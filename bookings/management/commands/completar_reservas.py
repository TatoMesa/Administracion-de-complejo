from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking
import datetime


class Command(BaseCommand):
    help = 'Marca como completadas las reservas cuya fecha y hora de fin ya pasaron'

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        today = now.date()
        current_time = now.time()

        # Reservas de dias anteriores
        past_bookings = Booking.objects.filter(
            status='confirmed',
            date__lt=today
        )

        # Reservas de hoy cuya hora de fin ya paso
        today_bookings = Booking.objects.filter(
            status='confirmed',
            date=today,
            end_time__lte=current_time
        )

        past_count = past_bookings.update(status='completed')
        today_count = today_bookings.update(status='completed')
        total = past_count + today_count

        self.stdout.write(
            self.style.SUCCESS(
                f'Completadas {total} reservas ({past_count} de dias anteriores, {today_count} de hoy)'
            )
        )