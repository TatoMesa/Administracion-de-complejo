from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.resource_list, name='list'),
    path('nueva/', views.resource_create, name='create'),
    path('<int:pk>/editar/', views.resource_edit, name='edit'),
    path('<int:pk>/eliminar/', views.resource_delete, name='delete'),
]