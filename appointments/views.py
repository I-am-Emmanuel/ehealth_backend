from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Availability
from .serializers import AvailabilitySerializer

class DoctorAvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return only the logged-in doctor's availabilities
        return Availability.objects.filter(doctor=self.request.user)

    def perform_create(self, serializer):
        # Set the doctor field automatically
        
        serializer.save(doctor=self.request.user)

class DoctorAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Availability.objects.filter(doctor=self.request.user)

