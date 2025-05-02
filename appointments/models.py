from django.db import models
from core.models import User

class Hospital(models.Model):
    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')  # or make dynamic
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    registered_date = models.DateField(auto_now_add=True)



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


# class Appointment(models.Model):
#     patient = models.ForeignKey(User, on_delete=models.CASCADE)
#     doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
#     hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
#     date = models.DateField()
#     time = models.TimeField()
#     status = models.CharField(
#         max_length=20,
#         choices=[('Pending', 'Pending'), ('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
#         default='Pending'
#     )