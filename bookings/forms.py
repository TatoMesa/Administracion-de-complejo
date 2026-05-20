from django import forms
from .models import Booking
from resources.models import Resource
from clients.models import Client
import datetime


def get_time_choices():
    """Genera opciones de 00:00 a 23:30 en intervalos de 30 minutos."""
    choices = []
    for hour in range(0, 24):
        for minute in (0, 30):
            time = datetime.time(hour, minute)
            label = time.strftime('%H:%M')
            choices.append((label, label))
    return choices


class BookingForm(forms.ModelForm):
    start_time = forms.ChoiceField(
        choices=get_time_choices,
        label='Hora inicio',
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    end_time = forms.ChoiceField(
        choices=get_time_choices,
        label='Hora fin',
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    class Meta:
        model = Booking
        fields = ['resource', 'client', 'date', 'start_time', 'end_time', 'notes']
        widgets = {
            'resource': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resource'].queryset = Resource.objects.filter(is_active=True)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['notes'].required = False

        # Si hay instancia, pre-seleccionar los valores actuales
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.fields['start_time'].initial = self.instance.start_time.strftime('%H:%M')
            if self.instance.end_time:
                self.fields['end_time'].initial = self.instance.end_time.strftime('%H:%M')

    def clean_start_time(self):
        value = self.cleaned_data.get('start_time')
        try:
            return datetime.datetime.strptime(value, '%H:%M').time()
        except (ValueError, TypeError):
            raise forms.ValidationError('Hora inválida.')

    def clean_end_time(self):
        value = self.cleaned_data.get('end_time')
        try:
            return datetime.datetime.strptime(value, '%H:%M').time()
        except (ValueError, TypeError):
            raise forms.ValidationError('Hora inválida.')

    def clean(self):
        cleaned_data = super().clean()
        resource = cleaned_data.get('resource')
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('La hora de fin debe ser posterior a la de inicio.')

        if resource and date and start_time and end_time:
            overlapping = Booking.objects.filter(
                resource=resource,
                date=date,
                status='confirmed',
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(pk=self.instance.pk if self.instance else None)

            if overlapping.exists():
                conflicto = overlapping.first()
                raise forms.ValidationError(
                    f'Ya existe una reserva en ese horario: '
                    f'{conflicto.client.name} de {conflicto.start_time:%H:%M} a {conflicto.end_time:%H:%M}.'
                )

        return cleaned_data