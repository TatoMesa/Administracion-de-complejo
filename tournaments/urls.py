from django.urls import path
from . import views

app_name = 'tournaments'

urlpatterns = [
    path('', views.tournament_list, name='list'),
    path('nuevo/', views.tournament_create, name='create'),
    path('<int:pk>/', views.tournament_detail, name='detail'),
    path('<int:pk>/editar/', views.tournament_edit, name='edit'),
    path('<int:pk>/equipos/nuevo/', views.team_create, name='team_create'),
    path('equipos/<int:pk>/', views.team_detail, name='team_detail'),
    path('equipos/<int:pk>/jugador/nuevo/', views.player_create, name='player_create'),
    path('jugadores/<int:pk>/toggle/', views.player_toggle, name='player_toggle'),
    path('<int:pk>/generar-fixture/', views.generate_fixture, name='generate_fixture'),
    path('partidos/<int:pk>/resultado/', views.match_result, name='match_result'),
]