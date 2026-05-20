from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='list'),
    path('nuevo/', views.client_create, name='create'),
    path('<int:pk>/', views.client_detail, name='detail'),
    path('<int:pk>/editar/', views.client_edit, name='edit'),
    path('<int:pk>/eliminar/', views.client_delete, name='delete'),
]