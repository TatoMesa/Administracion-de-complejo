from django import forms
from .models import Booking
from resources.models import Resource
from clients.models import Client


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['resource', 'client', 'date', 'start_time', 'end_time', 'notes']
        widgets = {
            'resource': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resource'].queryset = Resource.objects.filter(is_active=True)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['notes'].required = False

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