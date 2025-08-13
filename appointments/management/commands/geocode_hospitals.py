from django.core.management.base import BaseCommand
from appointments.models import Hospital
from django.db import models

class Command(BaseCommand):
    help = 'Geocode hospitals without coordinates'
    
    def handle(self, *args, **options):
        hospitals = Hospital.objects.filter(
            models.Q(latitude__isnull=True) | 
            models.Q(longitude__isnull=True)
        )
        
        for hospital in hospitals:
            hospital.save()  # Triggers geocoding in save method
            if hospital.latitude:
                self.stdout.write(f"Geocoded {hospital.name}")
            else:
                self.stdout.write(f"Failed to geocode {hospital.name}")