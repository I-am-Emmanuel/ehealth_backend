from django.urls import path, include
from .views import *
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('register', RegisterPatientAPI.as_view()),
    path('doctor', RegisterDoctorAPI.as_view()),
    path('license_check', ValidateDoctorLicense.as_view()),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('profile-image/', ProfileImageView.as_view(), name='profile-image'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
] 



