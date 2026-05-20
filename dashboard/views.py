from django.shortcuts import render
from django.utils import timezone
from bookings.models import Booking
from resources.models import Resource
from clients.models import Client


def index(request):
    today = timezone.now().date()

    # Reservas de hoy
    bookings_today = Booking.objects.filter(
        date=today,
        status='confirmed'
    ).select_related('resource', 'client').order_by('start_time')

    # Totales
    total_bookings_today = bookings_today.count()
    total_resources = Resource.objects.filter(is_active=True).count()
    total_clients = Client.objects.filter(is_active=True).count()

    # Ingresos estimados del día
    daily_revenue = sum(b.total_price for b in bookings_today)

    # Próximas reservas (hoy y mañana)
    upcoming_bookings = Booking.objects.filter(
        date__gte=today,
        status='confirmed'
    ).select_related('resource', 'client').order_by('date', 'start_time')[:10]

    context = {
        'total_bookings_today': total_bookings_today,
        'total_resources': total_resources,
        'total_clients': total_clients,
        'daily_revenue': daily_revenue,
        'bookings_today': bookings_today,
        'upcoming_bookings': upcoming_bookings,
        'today': today,
    }
    return render(request, 'dashboard/index.html', context)