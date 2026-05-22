from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Tournament, Team, Player, Group, Match, Standing
from .forms import TournamentForm, TeamForm, PlayerForm, MatchResultForm
import itertools
import random


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

    groups = tournament.groups.prefetch_related('teams', 'standings')

    context = {
        'tournament': tournament,
        'teams': teams,
        'matches': matches,
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
    if request.method == 'POST':
        form = MatchResultForm(request.POST, instance=match)
        if form.is_valid():
            old_status = match.status
            match = form.save()

            # Actualizar tabla si el partido fue finalizado
            if match.status == 'finished' and old_status != 'finished':
                _update_standings(match)
                messages.success(request, 'Resultado guardado y tabla actualizada.')
            else:
                messages.success(request, 'Resultado guardado.')

            return redirect('tournaments:detail', pk=match.tournament.pk)
    else:
        form = MatchResultForm(instance=match)

    return render(request, 'tournaments/match_result.html', {
        'form': form,
        'match': match,
    })


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