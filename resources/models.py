from django.db import models


class Sport(models.Model):
    """Tipo de deporte: Fútbol 5, Pádel, Básquet, etc."""
    name = models.CharField(max_length=100, verbose_name='Nombre')
    icon = models.CharField(max_length=10, verbose_name='Ícono', blank=True)
    color = models.CharField(max_length=7, verbose_name='Color', default='#3B82F6')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Deporte'
        verbose_name_plural = 'Deportes'
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}".strip()


class Resource(models.Model):
    """Cancha, sala o cualquier recurso reservable."""
    name = models.CharField(max_length=100, verbose_name='Nombre')
    sport = models.ForeignKey(
        Sport,
        on_delete=models.PROTECT,
        related_name='resources',
        verbose_name='Deporte'
    )
    capacity = models.PositiveIntegerField(verbose_name='Capacidad (jugadores)')
    description = models.TextField(blank=True, verbose_name='Descripción')
    price_per_hour = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Precio por hora'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    image = models.ImageField(
        upload_to='resources/',
        blank=True,
        null=True,
        verbose_name='Imagen'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recurso'
        verbose_name_plural = 'Recursos'
        ordering = ['sport', 'name']

    def __str__(self):
        return f"{self.name} ({self.sport.name})"