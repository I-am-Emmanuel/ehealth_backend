from django.urls import path, include
from .views import *

# urlpatterns = [
#     path('availability', DoctorAvailabilityListCreateView.as_view()),
#     path('availability-update', DoctorAvailabilityDetailView.as_view()),
# ]

urlpatterns = [
    path('availability/', DoctorAvailabilityListCreateView.as_view(), name='availability-list-create'),
    path('availability/<int:pk>/', DoctorAvailabilityDetailView.as_view(), name='availability-detail'),
]