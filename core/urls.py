from django.urls import path, include
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'patients', PatientViewSet, basename='patient')


urlpatterns = [
    path('register', RegisterPatientAPI.as_view()),
    path('doctor', RegisterDoctorAPI.as_view()),
    # path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    # path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    # path('doctor/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('license_check', ValidateDoctorLicense.as_view()),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('profile-image/', ProfileImageView.as_view(), name='profile-image'),
    path('profile-health-record/', ProfileHealthRecordView.as_view(), name='health-record'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('password-reset/',
         PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-token-confirm/', ConfirmPasswordResetTokenView.as_view(), name='confirm-password-reset'),
    path('password-reset-token-activate/', ConfirmPasswordResetActivationToken.as_view(), name='reset-activation'),
    path('set-new-password/', SetNewPasswordView.as_view(), name='reset-password'),
    # path('', testing, name='doctors'),
    # path('', view_doctors, name='doctors'),
]  + router.urls



