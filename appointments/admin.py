from django.contrib import admin
from .models import Availability


# Register your models here.
@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    fields = ['full_name', 'start_time', 'end_time']
    # pass