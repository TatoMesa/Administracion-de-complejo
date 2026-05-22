from django.contrib import admin
from .models import Tournament, Team, Player, Group, Match, Standing


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 1
    fields = ['name', 'dni', 'is_active', 'injury_replacement']


class TeamInline(admin.TabularInline):
    model = Team
    extra = 1
    fields = ['name', 'contact_name', 'contact_phone']


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'sport', 'format', 'gender', 'category', 'status', 'total_teams', 'start_date']
    list_filter = ['status', 'gender', 'category', 'format', 'sport']
    search_fields = ['name']
    inlines = [TeamInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'contact_name', 'contact_phone', 'total_players', 'is_complete']
    list_filter = ['tournament']
    search_fields = ['name', 'contact_name']
    inlines = [PlayerInline]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'dni', 'team', 'is_active', 'injury_replacement']
    list_filter = ['team__tournament', 'is_active', 'injury_replacement']
    search_fields = ['name', 'dni']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['home_team', 'away_team', 'tournament', 'stage', 'date', 'start_time', 'home_score', 'away_score', 'status']
    list_filter = ['tournament', 'stage', 'status']
    ordering = ['date', 'start_time']


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ['team', 'tournament', 'group', 'played', 'won', 'drawn', 'lost', 'goals_for', 'goals_against', 'points']
    list_filter = ['tournament', 'group']