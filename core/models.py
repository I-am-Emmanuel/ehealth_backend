from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(AbstractUser):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Undefine', 'Prefer not to say')
    ]
    
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True, null=True)
    
    def validate_future_date(value):
        if value and value < timezone.now().date():
            raise ValidationError("License expiry date must be in the future")
    
    license_expiry_date = models.DateField(
        null=True,
        blank=True,
        validators=[validate_future_date]
    )
    
    speciality = models.CharField(max_length=50, null=True, blank=True)
    is_med = models.BooleanField(default=False)
    hospital = models.ForeignKey(
        'appointments.Hospital',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='staff'
    )

    class Meta:
        verbose_name = 'Medical Professional'
        verbose_name_plural = 'Medical Professionals'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        if self.specialty:
            return f"{self.get_full_name()} ({self.specialty})"
        return self.get_full_name()


class MedicalPracticioner(models.Model):
    license_number=models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    gender = models.CharField(max_length=20)
    license_expiry_date = models.DateField(null=False)
    speciality = models.CharField(max_length=50, null=False)