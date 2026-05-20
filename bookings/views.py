from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Booking, RecurrenceRule
from resources.models import Resource
from clients.models import Client
from .forms import BookingForm
import datetime


def booking_list(request):
    bookings = Booking.objects.filter(
        status='confirmed'
    ).select_related('resource', 'client').order_by('date', 'start_time')

    # Filtros
    date_filter = request.GET.get('date')
    resource_filter = request.GET.get('resource')

    if date_filter:
        bookings = bookings.filter(date=date_filter)
    if resource_filter:
        bookings = bookings.filter(resource_id=resource_filter)

    context = {
        'bookings': bookings,
        'resources': Resource.objects.filter(is_active=True),
        'date_filter': date_filter or '',
        'resource_filter': resource_filter or '',
        'today': timezone.now().date(),
    }
    return render(request, 'bookings/list.html', context)


def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.created_by = request.user

            # Manejo de recurrencia
            recurrence_type = request.POST.get('recurrence_type')
            if recurrence_type and recurrence_type != 'none':
                end_date = request.POST.get('recurrence_end_date')
                rule = RecurrenceRule.objects.create(
                    frequency=recurrence_type,
                    start_date=booking.date,
                    end_date=end_date or None,
                )
                booking.recurrence = rule
                booking.save()

                # Generar reservas recurrentes
                _generate_recurring_bookings(booking, rule, request.user)
                messages.success(request, 'Reserva recurrente creada exitosamente.')
            else:
                booking.save()
                messages.success(request, 'Reserva creada exitosamente.')

            return redirect('bookings:list')
    else:
        # Pre-cargar fecha si viene por parámetro
        initial = {}
        date = request.GET.get('date')
        if date:
            initial['date'] = date
        form = BookingForm(initial=initial)

    context = {
        'form': form,
        'title': 'Nueva Reserva',
    }
    return render(request, 'bookings/form.html', context)


def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, f'Reserva de {booking.client.name} cancelada.')
    return redirect('bookings:list')


def _generate_recurring_bookings(original, rule, user):
    """Genera todas las reservas futuras según la regla de recurrencia."""
    from dateutil.relativedelta import relativedelta

    current_date = original.date
    end_date = rule.end_date or (current_date + datetime.timedelta(weeks=12))

    delta = datetime.timedelta(weeks=1) if rule.frequency == 'weekly' else datetime.timedelta(weeks=2)