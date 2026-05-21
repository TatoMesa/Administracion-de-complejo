from django.urls import path
from . import views

app_name = 'availability'

urlpatterns = [
    path('', views.availability_list, name='list'),
    path('<int:resource_pk>/regla/nueva/', views.rule_create, name='rule_create'),
    path('regla/<int:pk>/eliminar/', views.rule_delete, name='rule_delete'),
    path('<int:resource_pk>/excepcion/nueva/', views.exception_create, name='exception_create'),
    path('excepcion/<int:pk>/eliminar/', views.exception_delete, name='exception_delete'),
]