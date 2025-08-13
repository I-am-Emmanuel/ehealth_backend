from django.db import models
from django.db.models import F, Func, FloatField, ExpressionWrapper
from django.db.models.functions import Radians, Power, Sin, Cos, ATan2, Sqrt
import pytz
from datetime import datetime, timedelta   
from django.utils import timezone
from core.models import User

from .utils import geocode_address

    

class Hospital(models.Model):
    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Nigeria')  # or make dynamic
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    registered_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'
        ordering = ['name']

    def name_with_location(self):
        return f"{self.name} ({self.city}, {self.state})"
    
    def __str__(self):
        return self.name_with_location()
    
    @classmethod
    def nearby_hospitals(cls, latitude, longitude, radius_km=10):
        """
        Find hospitals within given radius (km) of specified coordinates
        using Haversine formula
        """
        # Convert degrees to radians
        lat_rad = Radians(latitude)
        lon_rad = Radians(longitude)
        lat_rad_field = Radians(F('latitude'))
        lon_rad_field = Radians(F('longitude'))
        
        # Haversine formula components
        dlat = lat_rad_field - lat_rad
        dlon = lon_rad_field - lon_rad
        
        a = (
            Power(Sin(dlat / 2), 2) + 
            Cos(lat_rad) * 
            Cos(lat_rad_field) * 
            Power(Sin(dlon / 2), 2)
        )
        
        c = 2 * ATan2(Sqrt(a), Sqrt(1 - a))
        distance_km = 6371 * c  # Earth's radius in km
        
        return cls.objects.annotate(
            distance=ExpressionWrapper(distance_km, output_field=FloatField())
        ).filter(
            distance__lt=radius_km
        ).order_by('distance')
    
    def save(self, *args, **kwargs):
        """Auto-populate coordinates if address changes"""
        if not self.latitude or not self.longitude:
            full_address = f"{self.address}, {self.city}, {self.state}, {self.country}"
            self.latitude, self.longitude = geocode_address(full_address)
        super().save(*args, **kwargs)


class Availability(models.Model):
    
    DAYS_OF_WEEK = [
        (0, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ]

    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField(default='09:00')
    end_time = models.TimeField(default='17:00')

    class Meta:
        unique_together = ('doctor', 'day_of_week', 'start_time', 'end_time')  # Prevent duplicates
        ordering = ['day_of_week', 'start_time']

    def full_name(self):
        return f"Dr. {self.doctor.first_name} {self.doctor.last_name}"

    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='patient_appointments')
    doctor = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='doctor_appointments'
    )
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    day_of_week = models.PositiveSmallIntegerField(
        choices=Availability.DAYS_OF_WEEK, 
        default=0, 
        help_text="Day of the week for the appointment (0=Sunday, 6=Saturday)"
    )
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_deadline = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(
        max_length=10,
        choices=[('doctor', 'Doctor'), ('patient', 'Patient')],
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('doctor', 'date', 'time', 'is_active')  # Modified constraint
        ordering = ['-date', 'time']
        indexes = [
            models.Index(fields=['doctor', 'date', 'time', 'is_active']),
            models.Index(fields=['user', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.date} {self.time} - {self.user.get_full_name()} with Dr. {self.doctor.get_full_name()}"

    def save(self, *args, **kwargs):
        # Set payment deadline when status changes to approved
        if self.status == 'approved' and not self.approval_date:
            self.approval_date = timezone.now()
            tz = pytz.timezone('Africa/Lagos')
            self.payment_deadline = timezone.now() + timedelta(hours=48)
            
        # Set confirmation date when status changes to confirmed
        if self.status == 'confirmed' and not self.confirmation_date:
            self.confirmation_date = timezone.now()
            
        # Set completion date when status changes to completed
        if self.status == 'completed' and not self.completion_date:
            self.completion_date = timezone.now()
            
        super().save(*args, **kwargs)

    def get_status_color(self):
        status_colors = {
            'pending': 'warning',
            'approved': 'info',
            'paid': 'success',
            'confirmed': 'success',
            'rejected': 'danger',
            'cancelled': 'danger',
            'completed': 'primary'
        }
        return status_colors.get(self.status, 'secondary')

    def is_past_due(self):
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        appointment_datetime = datetime.combine(
            self.date,
            self.time
        ).replace(tzinfo=tz)
        return now > appointment_datetime