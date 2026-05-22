from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Client
from .forms import ClientForm
from django.core.paginator import Paginator
from django.utils import timezone
from bookings.models import Booking

def client_list(request):
    clients = Client.objects.filter(is_active=True).order_by('name')

    search = request.GET.get('search')
    if search:
        clients = clients.filter(name__icontains=search) | clients.filter(phone__icontains=search)

    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search or '',
    }
    return render(request, 'clients/list.html', context)


def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente creado exitosamente.')
            return redirect('clients:list')
    else:
        form = ClientForm()

    return render(request, 'clients/form.html', {'form': form, 'title': 'Nuevo Cliente'})


def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado.')
            return redirect('clients:list')
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/form.html', {'form': form, 'title': 'Editar Cliente'})


def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        # Cancelar reservas futuras
        today = timezone.now().date()
        cancelled = Booking.objects.filter(
            client=client,
            date__gte=today,
            status='confirmed'
        ).update(status='cancelled')

        client.is_active = False
        client.save()
        messages.success(request, f'Cliente {client.name} desactivado y {cancelled} reservas futuras canceladas.')
    return redirect('clients:list')


def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    bookings = client.bookings.filter(
        status='confirmed'
    ).select_related('resource').order_by('-date', 'start_time')

    context = {
        'client': client,
        'bookings': bookings,
    }
    return render(request, 'clients/detail.html', context)