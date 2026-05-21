from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from resources.models import Resource
from .models import AvailabilityRule, AvailabilityException
from .forms import AvailabilityRuleForm, AvailabilityExceptionForm


def availability_list(request):
    resources = Resource.objects.filter(
        is_active=True
    ).prefetch_related('availability_rules', 'availability_exceptions').select_related('sport')

    context = {
        'resources': resources,
        'days': [
            (0, 'Lunes'), (1, 'Martes'), (2, 'Miercoles'),
            (3, 'Jueves'), (4, 'Viernes'), (5, 'Sabado'), (6, 'Domingo')
        ],
    }
    return render(request, 'availability/list.html', context)


def rule_create(request, resource_pk):
    resource = get_object_or_404(Resource, pk=resource_pk)
    if request.method == 'POST':
        form = AvailabilityRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.resource = resource
            rule.save()
            messages.success(request, 'Horario agregado.')
            return redirect('availability:list')
    else:
        form = AvailabilityRuleForm()

    return render(request, 'availability/rule_form.html', {
        'form': form,
        'resource': resource,
        'title': f'Agregar horario - {resource.name}'
    })


def rule_delete(request, pk):
    rule = get_object_or_404(AvailabilityRule, pk=pk)
    if request.method == 'POST':
        rule.delete()
        messages.success(request, 'Horario eliminado.')
    return redirect('availability:list')


def exception_create(request, resource_pk):
    resource = get_object_or_404(Resource, pk=resource_pk)
    if request.method == 'POST':
        form = AvailabilityExceptionForm(request.POST)
        if form.is_valid():
            exception = form.save(commit=False)
            exception.resource = resource
            exception.save()
            messages.success(request, 'Excepcion agregada.')
            return redirect('availability:list')
    else:
        form = AvailabilityExceptionForm()

    return render(request, 'availability/exception_form.html', {
        'form': form,
        'resource': resource,
        'title': f'Agregar excepcion - {resource.name}'
    })


def exception_delete(request, pk):
    exception = get_object_or_404(AvailabilityException, pk=pk)
    if request.method == 'POST':
        exception.delete()
        messages.success(request, 'Excepcion eliminada.')
    return redirect('availability:list')