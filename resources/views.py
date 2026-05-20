from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Resource, Sport
from .forms import ResourceForm, SportForm


def resource_list(request):
    resources = Resource.objects.filter(
        is_active=True
    ).select_related('sport').order_by('sport', 'name')

    context = {
        'resources': resources,
        'sports': Sport.objects.filter(is_active=True),
    }
    return render(request, 'resources/list.html', context)


def resource_create(request):
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cancha creada exitosamente.')
            return redirect('resources:list')
    else:
        form = ResourceForm()

    return render(request, 'resources/form.html', {'form': form, 'title': 'Nueva Cancha'})


def resource_edit(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cancha actualizada.')
            return redirect('resources:list')
    else:
        form = ResourceForm(instance=resource)

    return render(request, 'resources/form.html', {'form': form, 'title': 'Editar Cancha'})


def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        resource.is_active = False
        resource.save()
        messages.success(request, f'Cancha {resource.name} desactivada.')
    return redirect('resources:list')