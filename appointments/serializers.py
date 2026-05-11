from rest_framework import serializers
from .models import Hospital, Availability, Appointment
from django.contrib.auth import get_user_model

User = get_user_model()

class HospitalSerializer(serializers.ModelSerializer):
    distance = serializers.DecimalField(
        max_digits=6, 
        decimal_places=2,
        read_only=True,
        help_text="Distance in kilometers"
    )
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'city', 'state', 
            'postal_code', 'country', 'latitude', 
            'longitude', 'distance'
        ]


class AvailabilitySerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = ['id', 'doctor', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time']
        read_only_fields = ['doctor']


class HospitalDoctorsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'speciality', 'profile_image']


class AppointmentSerializer(serializers.ModelSerializer):
    payment_deadline = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = '__all__'
        
    def get_amount(self, obj):
        if obj.doctor.speciality.lower() in ['family medicine', 'internal medicine']:
            return "₦20,000"
        return "₦50,000"
    


# class AppointmentSerializer(serializers.ModelSerializer):
#     status_display = serializers.CharField(source='get_status_display', read_only=True)
#     doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
#     patient_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'doctor', 'doctor_name', 'user', 'patient_name', 
#             'date', 'time', 'day_of_week', 'status', 'status_display',
#             'created_at', 'updated_at'
#         ]
#         extra_kwargs = {
#             'doctor': {'write_only': True},
#             'user': {'read_only': True},
#             'day_of_week': {'read_only': True}
#         }

#     def validate(self, data):
#         # Custom validation logic
#         if 'date' in data and 'time' in data:
#             # Check for existing appointment
#             if Appointment.objects.filter(
#                 doctor=data['doctor'],
#                 date=data['date'],
#                 time=data['time']
#             ).exists():
#                 raise serializers.ValidationError("This time slot is already booked")
#         return data
    