from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from resources.models import Resource
from clients.models import Client


class RecurrenceRule(models.Model):
    """Define la regla de repetición de una reserva."""
    FREQUENCIES = [
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
    ]

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCIES,
        verbose_name='Frecuencia'
    )
    start_date = models.DateField(verbose_name='Fecha de inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha de fin')

    class Meta:
        verbose_name = 'Regla de recurrencia'
        verbose_name_plural = 'Reglas de recurrencia'

    def __str__(self):
        fin = self.end_date or 'sin fecha de fin'
        return f"{self.get_frequency_display()} desde {self.start_date} hasta {fin}"

    def clean(self):
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError('La fecha de fin debe ser posterior a la de inicio.')


class Booking(models.Model):
    """Reserva de un recurso por un cliente."""
    STATUS = [
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada'),
        ('completed', 'Completada'),
    ]

    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name='Recurso'
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name='Cliente'
    )
    date = models.DateField(verbose_name='Fecha')
    start_time = models.TimeField(verbose_name='Hora de inicio')
    end_time = models.TimeField(verbose_name='Hora de fin')
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='confirmed',
        verbose_name='Estado'
    )
    notes = models.TextField(blank=True, verbose_name='Notas')
    recurrence = models.ForeignKey(
        RecurrenceRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings',
        verbose_name='Recurrencia'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.resource.name} — {self.client.name} — {self.date} {self.start_time:%H:%M}"

    def clean(self):
        if self.start_time and self.end_time:
            # Validar que hora de fin sea posterior a la de inicio
            if self.start_time >= self.end_time:
                raise ValidationError('La hora de fin debe ser posterior a la de inicio.')

            # Validar solapamiento con otras reservas confirmadas
            overlapping = Booking.objects.filter(
                resource=self.resource,
                date=self.date,
                status='confirmed',
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            ).exclude(pk=self.pk)

            if overlapping.exists():
                conflicto = overlapping.first()
                raise ValidationError(
                    f'Ya existe una reserva en ese horario: '
                    f'{conflicto.client.name} de {conflicto.start_time:%H:%M} a {conflicto.end_time:%H:%M}.'
                )

    @property
    def duration_hours(self):
        from datetime import datetime, date
        from decimal import Decimal
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        seconds = (end - start).seconds
        return Decimal(seconds) / Decimal(3600)

    @property
    def total_price(self):
        return self.resource.price_per_hour * self.duration_hours