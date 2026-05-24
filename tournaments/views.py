from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Tournament, Team, Player, Group, Match, Standing
from .forms import TournamentForm, TeamForm, PlayerForm, MatchResultForm
import itertools
import random
from django.db.models import Count
from .models import Tournament, Team, Player, Group, Match, Standing, MatchEvent
from .forms import TournamentForm, TeamForm, PlayerForm, MatchResultForm, MatchEventForm


def tournament_list(request):
    tournaments = Tournament.objects.select_related('sport').order_by('-created_at')
    return render(request, 'tournaments/list.html', {'tournaments': tournaments})


def tournament_create(request):
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save()
            messages.success(request, 'Torneo creado exitosamente.')
            return redirect('tournaments:detail', pk=tournament.pk)
    else:
        form = TournamentForm()
    return render(request, 'tournaments/form.html', {'form': form, 'title': 'Nuevo Torneo'})


def tournament_edit(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            form.save()
            messages.success(request, 'Torneo actualizado.')
            return redirect('tournaments:detail', pk=tournament.pk)
    else:
        form = TournamentForm(instance=tournament)
    return render(request, 'tournaments/form.html', {'form': form, 'title': 'Editar Torneo'})


def tournament_detail(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    teams = tournament.teams.prefetch_related('players')
    matches = tournament.matches.select_related(
        'home_team', 'away_team', 'resource', 'group'
    ).order_by('date', 'start_time')

    # Tabla de posiciones ordenada por puntos
    standings = sorted(
        tournament.standings.select_related('team', 'group'),
        key=lambda s: (-s.points, -s.goal_difference, -s.goals_for)
    )

    # Goleadores
    scorers = MatchEvent.objects.filter(
        match__tournament=tournament,
        event_type='goal'
    ).values('player__name', 'player__team__name').annotate(
        total=Count('id')
    ).order_by('-total')[:10]

    # Tarjetas amarillas
    yellow_cards = MatchEvent.objects.filter(
        match__tournament=tournament,
        event_type='yellow'
    ).values('player__name', 'player__team__name').annotate(
        total=Count('id')
    ).order_by('-total')[:10]

    # Tarjetas rojas
    red_cards = MatchEvent.objects.filter(
        match__tournament=tournament,
        event_type='red'
    ).values('player__name', 'player__team__name').annotate(
        total=Count('id')
    ).order_by('-total')[:10]

    groups = tournament.groups.prefetch_related('teams', 'standings')

    context = {
        'tournament': tournament,
        'teams': teams,
        'matches': matches,
        'scorers': scorers,
        'yellow_cards': yellow_cards,
        'red_cards': red_cards,
        'standings': standings,
        'groups': groups,
        'can_generate': tournament.teams.count() >= 2 and not tournament.matches.exists(),
        
    }
    return render(request, 'tournaments/detail.html', context)


def team_create(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.tournament = tournament
            team.save()
            messages.success(request, f'Equipo {team.name} agregado.')
            return redirect('tournaments:detail', pk=tournament.pk)
    else:
        form = TeamForm()
    return render(request, 'tournaments/team_form.html', {
        'form': form,
        'tournament': tournament,
        'title': 'Nuevo Equipo'
    })


def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    players = team.players.all().order_by('name')
    return render(request, 'tournaments/team_detail.html', {
        'team': team,
        'players': players,
    })


def player_create(request, pk):
    team = get_object_or_404(Team, pk=pk)
    tournament = team.tournament

    if request.method == 'POST':
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            player.team = team
            try:
                player.full_clean()
                player.save()
                messages.success(request, f'Jugador {player.name} agregado.')
                return redirect('tournaments:team_detail', pk=team.pk)
            except Exception as e:
                from django.core.exceptions import ValidationError
                if isinstance(e, ValidationError):
                    for msg in e.messages:
                        messages.error(request, msg)
                else:
                    messages.error(request, str(e))
    else:
        form = PlayerForm()

    return render(request, 'tournaments/player_form.html', {
        'form': form,
        'team': team,
        'tournament': tournament,
        'title': f'Agregar jugador — {team.name}'
    })


def player_toggle(request, pk):
    player = get_object_or_404(Player, pk=pk)
    if request.method == 'POST':
        player.is_active = not player.is_active
        player.save()
        estado = 'habilitado' if player.is_active else 'suspendido'
        messages.success(request, f'{player.name} {estado}.')
    return redirect('tournaments:team_detail', pk=player.team.pk)


def generate_fixture(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)

    if tournament.matches.exists():
        messages.error(request, 'El fixture ya fue generado.')
        return redirect('tournaments:detail', pk=pk)

    teams = list(tournament.teams.all())
    if len(teams) < 2:
        messages.error(request, 'Se necesitan al menos 2 equipos.')
        return redirect('tournaments:detail', pk=pk)

    if tournament.format == 'round_robin':
        _generate_round_robin(tournament, teams)
    elif tournament.format == 'groups_elimination':
        _generate_groups(tournament, teams)

    tournament.status = 'in_progress'
    tournament.save()
    messages.success(request, 'Fixture generado exitosamente.')
    return redirect('tournaments:detail', pk=pk)


def _generate_round_robin(tournament, teams):
    """Genera todos contra todos."""
    random.shuffle(teams)
    for home, away in itertools.combinations(teams, 2):
        Match.objects.create(
            tournament=tournament,
            home_team=home,
            away_team=away,
            stage='group',
            resource=tournament.resource,
        )
        # Crear standing para cada equipo
        Standing.objects.get_or_create(
            tournament=tournament,
            team=home,
            group=None
        )
        Standing.objects.get_or_create(
            tournament=tournament,
            team=away,
            group=None
        )


def _generate_groups(tournament, teams):
    """Divide en grupos y genera fixture por grupo."""
    random.shuffle(teams)
    num_groups = max(2, len(teams) // 4)
    group_names = 'ABCDEFGH'

    groups = []
    for i in range(num_groups):
        group = Group.objects.create(
            tournament=tournament,
            name=group_names[i]
        )
        groups.append(group)

    # Distribuir equipos en grupos
    for i, team in enumerate(teams):
        group = groups[i % num_groups]
        group.teams.add(team)
        Standing.objects.get_or_create(
            tournament=tournament,
            team=team,
            group=group
        )

    # Generar partidos por grupo
    for group in groups:
        group_teams = list(group.teams.all())
        for home, away in itertools.combinations(group_teams, 2):
            Match.objects.create(
                tournament=tournament,
                group=group,
                home_team=home,
                away_team=away,
                stage='group',
                resource=tournament.resource,
            )


def match_result(request, pk):
    match = get_object_or_404(Match, pk=pk)
    events = match.events.select_related('player', 'player__team').order_by('minute')

    if request.method == 'POST':
        form = MatchResultForm(request.POST, instance=match)
        if form.is_valid():
            old = Match.objects.get(pk=pk)
            old_status = old.status
            old_home_score = old.home_score
            old_away_score = old.away_score

            match = form.save()

            if match.status == 'finished':
                if old_status == 'finished' and old_home_score is not None:
                    _revert_standings(match, old_home_score, old_away_score)
                _update_standings(match)
                messages.success(request, 'Resultado guardado y tabla actualizada.')
            else:
                if old_status == 'finished' and old_home_score is not None:
                    _revert_standings(match, old_home_score, old_away_score)
                messages.success(request, 'Resultado guardado.')

            return redirect('tournaments:detail', pk=match.tournament.pk)
    else:
        match_fresh = Match.objects.get(pk=pk)
        form = MatchResultForm(instance=match)

    # Siempre inicializar event_form con match
    event_form = MatchEventForm(match=match)

    return render(request, 'tournaments/match_result.html', {
        'form': form,
        'match': match,
        'events': events,
        'event_form': event_form,
    })

def _revert_standings(match, home_score, away_score):
    """Revierte el resultado anterior de la tabla antes de actualizar."""
    try:
        home_standing = Standing.objects.get(
            tournament=match.tournament,
            team=match.home_team,
            group=match.group
        )
        away_standing = Standing.objects.get(
            tournament=match.tournament,
            team=match.away_team,
            group=match.group
        )
    except Standing.DoesNotExist:
        return

    home_standing.played = max(0, home_standing.played - 1)
    away_standing.played = max(0, away_standing.played - 1)
    home_standing.goals_for = max(0, home_standing.goals_for - home_score)
    home_standing.goals_against = max(0, home_standing.goals_against - away_score)
    away_standing.goals_for = max(0, away_standing.goals_for - away_score)
    away_standing.goals_against = max(0, away_standing.goals_against - home_score)

    # Revertir resultado anterior
    if home_score > away_score:
        home_standing.won = max(0, home_standing.won - 1)
        away_standing.lost = max(0, away_standing.lost - 1)
    elif away_score > home_score:
        away_standing.won = max(0, away_standing.won - 1)
        home_standing.lost = max(0, home_standing.lost - 1)
    else:
        home_standing.drawn = max(0, home_standing.drawn - 1)
        away_standing.drawn = max(0, away_standing.drawn - 1)

    home_standing.save()
    away_standing.save()

def _update_standings(match):
    """Actualiza la tabla de posiciones tras cargar un resultado."""
    home_standing, _ = Standing.objects.get_or_create(
        tournament=match.tournament,
        team=match.home_team,
        group=match.group
    )
    away_standing, _ = Standing.objects.get_or_create(
        tournament=match.tournament,
        team=match.away_team,
        group=match.group
    )

    home_standing.played += 1
    away_standing.played += 1
    home_standing.goals_for += match.home_score
    home_standing.goals_against += match.away_score
    away_standing.goals_for += match.away_score
    away_standing.goals_against += match.home_score

    if match.result == 'home':
        home_standing.won += 1
        away_standing.lost += 1
    elif match.result == 'away':
        away_standing.won += 1
        home_standing.lost += 1
    else:
        home_standing.drawn += 1
        away_standing.drawn += 1

    home_standing.save()
    away_standing.save()

def match_event_create(request, pk):
    match = get_object_or_404(Match, pk=pk)
    if request.method == 'POST':
        form = MatchEventForm(match=match, data=request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.match = match
            event.save()

            # Verificar suspension por amarillas acumuladas
            if event.event_type == 'yellow':
                _check_yellow_suspension(event.player, match.tournament)

            # Suspension inmediata por roja
            if event.event_type == 'red':
                event.player.is_active = False
                event.player.save()
                messages.warning(
                    request,
                    f'{event.player.name} suspendido por tarjeta roja.'
                )
            else:
                messages.success(request, 'Evento registrado.')

            return redirect('tournaments:match_result', pk=match.pk)
    else:
        form = MatchEventForm(match=match)

    return render(request, 'tournaments/match_event_form.html', {
        'form': form,
        'match': match,
    })


def match_event_delete(request, pk):
    event = get_object_or_404(MatchEvent, pk=pk)
    match_pk = event.match.pk
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Evento eliminado.')
    return redirect('tournaments:match_result', pk=match_pk)


def _check_yellow_suspension(player, tournament):
    yellow_count = MatchEvent.objects.filter(
        player=player,
        event_type='yellow',
        match__tournament=tournament
    ).count()

    if yellow_count >= tournament.yellow_cards_suspension:
        player.is_active = False
        player.save()
        return True
    return False