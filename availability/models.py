from django.db import models
from django.core.exceptions import ValidationError
from resources.models import Resource


class AvailabilityRule(models.Model):
    """Horarios habituales de un recurso por día de semana."""
    DAYS = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='availability_rules',
        verbose_name='Recurso'
    )
    day_of_week = models.IntegerField(choices=DAYS, verbose_name='Día de la semana')
    open_time = models.TimeField(verbose_name='Hora de apertura')
    close_time = models.TimeField(verbose_name='Hora de cierre')

    class Meta:
        verbose_name = 'Regla de disponibilidad'
        verbose_name_plural = 'Reglas de disponibilidad'
        ordering = ['resource', 'day_of_week']
        unique_together = ['resource', 'day_of_week']

    def __str__(self):
        return f"{self.resource.name} — {self.get_day_of_week_display()} {self.open_time:%H:%M} a {self.close_time:%H:%M}"

    def clean(self):
        if self.open_time and self.close_time:
            if self.open_time >= self.close_time:
                raise ValidationError('La hora de apertura debe ser anterior a la de cierre.')


class AvailabilityException(models.Model):
    """Excepciones puntuales: feriados, mantenimiento, horario especial."""
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='availability_exceptions',
        verbose_name='Recurso'
    )
    date = models.DateField(verbose_name='Fecha')
    is_closed = models.BooleanField(default=True, verbose_name='Cerrado todo el día')
    open_time = models.TimeField(null=True, blank=True, verbose_name='Hora de apertura especial')
    close_time = models.TimeField(null=True, blank=True, verbose_name='Hora de cierre especial')
    reason = models.CharField(max_length=200, verbose_name='Motivo')

    class Meta:
        verbose_name = 'Excepción de disponibilidad'
        verbose_name_plural = 'Excepciones de disponibilidad'
        ordering = ['date']
        unique_together = ['resource', 'date']

    def __str__(self):
        estado = 'Cerrado' if self.is_closed else f"{self.open_time:%H:%M} a {self.close_time:%H:%M}"
        return f"{self.resource.name} — {self.date} ({estado})"

    def clean(self):
        if not self.is_closed:
            if not self.open_time or not self.close_time:
                raise ValidationError('Si no está cerrado, debe indicar horario de apertura y cierre.')
            if self.open_time >= self.close_time:
                raise ValidationError('La hora de apertura debe ser anterior a la de cierre.')