from django.db import models
from core.models import User

class Hospital(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)  # e.g. 6.524379
    longitude = models.DecimalField(max_digits=9, decimal_places=6)  # e.g. 3.379206
    specialties = models.CharField(max_length=200)  # e.g. "Cardiology, Pediatrics"

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors')
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return f"Dr. {self.user.last_name} ({self.specialty})"

class Availability(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.PositiveSmallIntegerField(  # 0=Monday, 6=Sunday
        choices=[(0, 'Monday'), (1, 'Tuesday'),(2, 'Wednesday'), (3, 'Thursday'),(4, 'Friday'), ]
    )
    start_time = models.TimeField()  # e.g. 09:00
    end_time = models.TimeField()    # e.g. 17:00
    is_active = models.BooleanField(default=True)

class Appointment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
        default='Pending'
    )