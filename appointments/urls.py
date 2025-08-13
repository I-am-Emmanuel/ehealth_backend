from django.urls import path
from .views import *
from rest_framework.routers import DefaultRouter


router = DefaultRouter()

router.register(r'doctors-appointment', DoctorAppointmentViewSet, basename='doctors-view')


urlpatterns = [
    path('availability/', DoctorAvailabilityListCreateView.as_view(), name='availability-list-create'),
    path('availability/<int:pk>/', DoctorAvailabilityDetailView.as_view(), name='availability-detail'),
    path('hospitals/', HospitalViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('hospitals/<int:pk>/', HospitalViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
    path('hospitals/nearby/', NearbyHospitalsView.as_view(), name='nearby-hospitals'),
    path('hospitals/<int:hospital_id>/doctors/', HospitalDoctorsListView.as_view(), name='hospital-doctors-list'),
    path('doctor-availability-booking/<int:pk>/', DoctorAppointmentBookingView.as_view(), name='doctor-availability-booking-detail'),
    path('doctor-availability/<int:doctor_id>/', DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('doctor-time-slots/<int:doctor_id>/', DoctorTimeSlotView.as_view(), name='doctor-time-slots'),
    path('book-appointment/', BookAppointmentView.as_view(), name='book-appointment'),
    path('patient-appointments/', 
     PatientAppointmentView.as_view({'get': 'list'})),
    path('patient-appointments/<int:pk>/cancel/', 
        PatientAppointmentView.as_view({'post': 'cancel'})),
    path('today-appointments/', 
        TodaysConfirmedAppointmentsView.as_view(), name='todays-confirmed-appointments'),
    # path('appointments/<int:appointment_id>/confirm/', DoctorConfirmAppointmentView.as_view()),
    # path('appointments/<int:appointment_id>/pay/', ProcessPaymentView.as_view()),
    # path('appointments/<int:appointment_id>/initialize-payment/', InitializePaymentView.as_view()),
    # path('appointments/<int:appointment_id>/verify-payment/', VerifyPaymentView.as_view()),
] + router.urls