from rest_framework import serializers
from .models import Hospital, Availability

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['name', 'address', ]


class AvailabilitySerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = ['id', 'doctor', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time']
        read_only_fields = ['doctor']
