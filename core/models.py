from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class User(AbstractUser):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[('Male', 'Male'), ('Female', 'Female')]
    )
    address = models.TextField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)


class MedicalPracticioner(models.Model):
    license_number=models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    gender = models.CharField(max_length=20)
    license_expiry_date = models.DateField(null=False)