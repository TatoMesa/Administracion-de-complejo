from django.contrib import admin
from .models import Sport, Resource


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    list_editable = ['is_active']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'sport', 'capacity', 'price_per_hour', 'is_active']
    list_filter = ['sport', 'is_active']
    search_fields = ['name', 'sport__name']
    list_editable = ['is_active', 'price_per_hour']
    readonly_fields = ['created_at', 'updated_at']