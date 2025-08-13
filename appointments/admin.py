from django.contrib import admin
from .models import Availability, Hospital


# Register your models here.
@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    fields = ['full_name', 'start_time', 'end_time']
    # pass

@admin.register(Hospital)
class Hospiatal(admin.ModelAdmin):
    fields = ['name', 'license_number', 'city', 'state', 'address', 'postal_code', 'country']