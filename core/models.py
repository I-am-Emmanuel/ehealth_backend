from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from .validators import file_validators, validate_future_date, validate_phone_number

class User(AbstractUser):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ("Non-binary", "Non-binary"),
        ('Undefine', 'Prefer not to say')
    ]
    
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    phone = models.CharField(max_length=11, blank=True, null=True, validators=[validate_phone_number], unique=True)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(validators=[file_validators],upload_to='profile_images/', null=True, blank=True)
    health_record = models.FileField(validators=[file_validators, FileExtensionValidator("pdf")], null=True, blank=True, upload_to='health_records/')
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
        if self.speciality:
            return f"{self.get_full_name()} ({self.speciality})"
        return self.get_full_name()


class MedicalPracticioner(models.Model):
    license_number=models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    gender = models.CharField(max_length=20)
    license_expiry_date = models.DateField(null=False)
    speciality = models.CharField(max_length=50, null=False)

class PasswordResetKey(models.Model):
    key = models.CharField(max_length=10, blank=True, null=True)
    expiry_date = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        related_name='reset_keys',
        on_delete=models.CASCADE)
    matched = models.BooleanField(default=False)
    token_activation_code = models.CharField(
        max_length=50, null=True, blank=True)

    def __str__(self):
        return self.user.username if self.user else self.matched