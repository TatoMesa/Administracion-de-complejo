from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Tournament, Team, Player, Group, Match, Standing
from .forms import TournamentForm, TeamForm, PlayerForm, MatchResultForm
import itertools
import random
from django.db.models import Count
from .models import Tournament, Team, Player, Group, Match, Standing, MatchEvent
from .forms import TournamentForm, TeamForm, PlayerForm, MatchResultForm, MatchEventForm
from django.db.models import Case, When, IntegerField


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
    
    STAGE_ORDER = Case(
        When(stage='group', then=1),
        When(stage='round_of_16', then=2),
        When(stage='quarterfinal', then=3),
        When(stage='semifinal', then=4),
        When(stage='third_place', then=5),
        When(stage='final', then=6),
        default=0,
        output_field=IntegerField()
    )

    matches = tournament.matches.select_related(
        'home_team', 'away_team', 'resource', 'group'
    ).annotate(stage_order=STAGE_ORDER).order_by('stage_order', 'date', 'start_time')

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

    teams = list(tournament.teams.all())
    if len(teams) < 2:
        messages.error(request, 'Se necesitan al menos 2 equipos.')
        return redirect('tournaments:detail', pk=pk)

    # Si ya existe fixture, borrar todo y regenerar
    
    tournament.matches.all().delete()
    tournament.groups.all().delete()
    tournament.standings.all().delete()
    tournament.champion = None
    tournament.runner_up = None
    tournament.save()

    if tournament.format == 'round_robin':
        _generate_round_robin(tournament, teams)
    elif tournament.format == 'groups_elimination':
        _generate_groups(tournament, teams)

    tournament.status = 'in_progress'
    tournament.save()
    messages.success(request, f'Fixture generado para {len(teams)} equipos.')
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
        if not group.teams.filter(pk=team.pk).exists():
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

def _generate_elimination_stage(tournament):
    """Genera los partidos de eliminación cuando terminan los grupos."""
    groups = list(tournament.groups.prefetch_related('teams', 'standings').all())

    if not groups:
        return

    # Obtener el primero y segundo de cada grupo ordenado por puntos
    classified = []
    for group in groups:
        group_standings = sorted(
            group.standings.all(),
            key=lambda s: (-s.points, -s.goal_difference, -s.goals_for)
        )
        if len(group_standings) >= 1:
            classified.append(('first', group, group_standings[0].team))
        if len(group_standings) >= 2:
            classified.append(('second', group, group_standings[1].team))

    # Primeros de cada grupo
    first_place = [t for pos, g, t in classified if pos == 'first']
    # Segundos de cada grupo
    second_place = [t for pos, g, t in classified if pos == 'second']

    num_groups = len(groups)

    if num_groups == 2:
        # 2 grupos: semifinales cruzadas (1A vs 2B y 1B vs 2A)
        if len(first_place) >= 2 and len(second_place) >= 2:
            Match.objects.create(
                tournament=tournament,
                home_team=first_place[0],
                away_team=second_place[1],
                stage='semifinal',
                resource=tournament.resource,
            )
            Match.objects.create(
                tournament=tournament,
                home_team=first_place[1],
                away_team=second_place[0],
                stage='semifinal',
                resource=tournament.resource,
            )
    elif num_groups >= 4:
        # 4 grupos: cuartos de final cruzados
        matchups = [
            (first_place[0], second_place[1]),
            (first_place[1], second_place[0]),
            (first_place[2], second_place[3]),
            (first_place[3], second_place[2]),
        ]
        for home, away in matchups:
            Match.objects.create(
                tournament=tournament,
                home_team=home,
                away_team=away,
                stage='quarterfinal',
                resource=tournament.resource,
            )
    else:
        # Para otros casos generar cruces simples
        for i in range(len(first_place)):
            if i < len(second_place):
                Match.objects.create(
                    tournament=tournament,
                    home_team=first_place[i],
                    away_team=second_place[(i + 1) % len(second_place)],
                    stage='semifinal',
                    resource=tournament.resource,
                )

    

def _generate_final_stage(tournament):
    """Genera final y tercer puesto cuando terminan las semifinales."""
    semis = tournament.matches.filter(
        stage='semifinal',
        status='finished'
    )

    if semis.count() < 2:
        return

    # Ganadores van a la final, perdedores al tercer puesto
    finalists = []
    third_place = []

    for semi in semis:
        if semi.result == 'home':
            finalists.append(semi.home_team)
            third_place.append(semi.away_team)
        elif semi.result == 'away':
            finalists.append(semi.away_team)
            third_place.append(semi.home_team)

    if len(finalists) == 2:
        # Crear final
        if not tournament.matches.filter(stage='final').exists():
            Match.objects.create(
                tournament=tournament,
                home_team=finalists[0],
                away_team=finalists[1],
                stage='final',
                resource=tournament.resource,
            )

        # Crear tercer puesto
        if len(third_place) == 2 and not tournament.matches.filter(stage='third_place').exists():
            Match.objects.create(
                tournament=tournament,
                home_team=third_place[0],
                away_team=third_place[1],
                stage='third_place',
                resource=tournament.resource,
            )

def _generate_semifinal_stage(tournament):
    """Genera semifinales cuando terminan los cuartos."""
    quarters = tournament.matches.filter(
        stage='quarterfinal',
        status='finished'
    )

    total_quarters = tournament.matches.filter(stage='quarterfinal').count()
    if quarters.count() < total_quarters or total_quarters == 0:
        return

    winners = []
    for q in quarters:
        if q.result == 'home':
            winners.append(q.home_team)
        elif q.result == 'away':
            winners.append(q.away_team)

    if len(winners) >= 2 and not tournament.matches.filter(stage='semifinal').exists():
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                Match.objects.create(
                    tournament=tournament,
                    home_team=winners[i],
                    away_team=winners[i + 1],
                    stage='semifinal',
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
                _check_and_proclame_champion(match.tournament)

                # Verificar si hay que generar siguiente fase
                if match.tournament.format == 'groups_elimination':
                    stage_generated = _check_next_stage(match.tournament)
                    if stage_generated:
                        messages.info(request, 'Fase completada. Se generaron los partidos de la siguiente ronda.')

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

def _check_and_proclame_champion(tournament):
    """Verifica si todos los partidos terminaron y proclama campeón."""
    total_matches = tournament.matches.count()
    finished_matches = tournament.matches.filter(status='finished').count()

    if total_matches == 0 or total_matches != finished_matches:
        return

    champion = None
    runner_up = None

    if tournament.format == 'round_robin':
        # Ordenar por puntos, diferencia de goles, goles a favor
        standings = sorted(
            tournament.standings.all(),
            key=lambda s: (-s.points, -s.goal_difference, -s.goals_for)
        )
        if len(standings) >= 1:
            champion = standings[0].team
        if len(standings) >= 2:
            runner_up = standings[1].team

    elif tournament.format == 'groups_elimination':
        # Buscar el partido de la final
        final = tournament.matches.filter(stage='final', status='finished').first()
        if final:
            if final.result == 'home':
                champion = final.home_team
                runner_up = final.away_team
            elif final.result == 'away':
                champion = final.away_team
                runner_up = final.home_team

    if champion:
        tournament.champion = champion
        tournament.runner_up = runner_up
        tournament.status = 'finished'
        tournament.save()

def _check_next_stage(tournament):
    """Verifica si hay que generar la siguiente fase de eliminación."""
    group_matches = tournament.matches.filter(stage='group')
    if group_matches.exists():
        finished_groups = group_matches.filter(status='finished').count()
        total_groups = group_matches.count()
        if finished_groups == total_groups:
            if not tournament.matches.filter(
                stage__in=['quarterfinal', 'semifinal', 'final']
            ).exists():
                _generate_elimination_stage(tournament)
                return True

    quarter_matches = tournament.matches.filter(stage='quarterfinal')
    if quarter_matches.exists():
        if quarter_matches.filter(status='finished').count() == quarter_matches.count():
            if not tournament.matches.filter(stage='semifinal').exists():
                _generate_semifinal_stage(tournament)
                return True

    semi_matches = tournament.matches.filter(stage='semifinal')
    if semi_matches.exists():
        if semi_matches.filter(status='finished').count() == semi_matches.count():
            if not tournament.matches.filter(stage='final').exists():
                _generate_final_stage(tournament)
                return True

    return False       

def tournament_history(request):
    tournaments = Tournament.objects.filter(
        status='finished'
    ).select_related(
        'sport', 'champion', 'runner_up'
    ).order_by('-start_date')

    return render(request, 'tournaments/history.html', {'tournaments': tournaments})