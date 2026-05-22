from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Booking, RecurrenceRule
from resources.models import Resource
from clients.models import Client
from .forms import BookingForm
import datetime
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta

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

    # Paginacion
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
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
    

    current_date = original.date
    end_date = rule.end_date or (current_date + datetime.timedelta(weeks=12))

    delta = datetime.timedelta(weeks=1) if rule.frequency == 'weekly' else datetime.timedelta(weeks=2)


def get_available_slots(request):
    resource_id = request.GET.get('resource')
    date_str = request.GET.get('date')

    if not resource_id or not date_str:
        return JsonResponse({'slots': []})

    import datetime
    from availability.models import AvailabilityRule, AvailabilityException

    try:
        date = datetime.date.fromisoformat(date_str)
        resource = Resource.objects.get(pk=resource_id, is_active=True)
    except (ValueError, Resource.DoesNotExist):
        return JsonResponse({'slots': []})

    # Verificar si hay excepcion de cierre para esa fecha
    exception = AvailabilityException.objects.filter(
        resource=resource,
        date=date
    ).first()

    if exception and exception.is_closed:
        return JsonResponse({'slots': [], 'reason': 'La cancha esta cerrada ese dia.'})

    # Obtener horario del dia de la semana
    day_of_week = date.weekday()

    if exception and not exception.is_closed:
        open_time = exception.open_time
        close_time = exception.close_time
    else:
        rule = AvailabilityRule.objects.filter(
            resource=resource,
            day_of_week=day_of_week
        ).first()

        if not rule:
            return JsonResponse({'slots': [], 'reason': 'La cancha no tiene horario configurado para ese dia.'})

        open_time = rule.open_time
        close_time = rule.close_time

    # Generar slots de 30 minutos
    slots = []
    current = datetime.datetime.combine(date, open_time)
    end = datetime.datetime.combine(date, close_time)

    while current < end:
        slots.append(current.strftime('%H:%M'))
        current += datetime.timedelta(minutes=30)

    # Filtrar slots ocupados por reservas confirmadas
    confirmed_bookings = Booking.objects.filter(
        resource=resource,
        date=date,
        status='confirmed'
    )

    available_slots = []
    for slot in slots:
        slot_time = datetime.datetime.strptime(slot, '%H:%M').time()
        occupied = confirmed_bookings.filter(
            start_time__lte=slot_time,
            end_time__gt=slot_time
        ).exists()
        if not occupied:
            available_slots.append(slot)

    return JsonResponse({'slots': available_slots})

def booking_history(request):
    bookings = Booking.objects.filter(
        status__in=['completed', 'cancelled']
    ).select_related('resource', 'client').order_by('-date', '-start_time')

    # Filtros
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    resource_filter = request.GET.get('resource')
    status_filter = request.GET.get('status')

    if date_from:
        bookings = bookings.filter(date__gte=date_from)
    if date_to:
        bookings = bookings.filter(date__lte=date_to)
    if resource_filter:
        bookings = bookings.filter(resource_id=resource_filter)
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    context = {
        'bookings': bookings,
        'resources': Resource.objects.filter(is_active=True),
        'date_from': date_from or '',
        'date_to': date_to or '',
        'resource_filter': resource_filter or '',
        'status_filter': status_filter or '',
        'total_completed': bookings.filter(status='completed').count(),
        'total_cancelled': bookings.filter(status='cancelled').count(),
        'total_revenue': sum(b.total_price for b in bookings.filter(status='completed')),
    }
    return render(request, 'bookings/history.html', context)