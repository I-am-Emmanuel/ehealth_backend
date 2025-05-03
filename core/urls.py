from django.urls import path, include
from .views import *



urlpatterns = [
    path('register', RegisterPatientAPI.as_view()),
    path('doctor', RegisterDoctorAPI.as_view()),
    path('license_check', ValidateDoctorLicense.as_view()),
    path('login/', LoginAPIView.as_view(), name='login'),
]