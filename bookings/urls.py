from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='list'),
    path('nueva/', views.booking_create, name='create'),
    path('<int:pk>/cancelar/', views.booking_cancel, name='cancel'),
    path('slots/', views.get_available_slots, name='slots'),
]