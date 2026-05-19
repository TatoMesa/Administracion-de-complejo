from django.contrib import admin
from .models import Booking, RecurrenceRule


@admin.register(RecurrenceRule)
class RecurrenceRuleAdmin(admin.ModelAdmin):
    list_display = ['frequency', 'start_date', 'end_date']
    list_filter = ['frequency']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['resource', 'client', 'date', 'start_time', 'end_time', 'status', 'total_price']
    list_filter = ['status', 'resource', 'date']
    search_fields = ['client__name', 'resource__name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['-date', 'start_time']
    date_hierarchy = 'date'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)