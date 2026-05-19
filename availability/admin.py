from django.contrib import admin
from .models import AvailabilityRule, AvailabilityException


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ['resource', 'day_of_week', 'open_time', 'close_time']
    list_filter = ['resource', 'day_of_week']
    ordering = ['resource', 'day_of_week']


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ['resource', 'date', 'is_closed', 'open_time', 'close_time', 'reason']
    list_filter = ['resource', 'is_closed']
    search_fields = ['reason']
    ordering = ['date']