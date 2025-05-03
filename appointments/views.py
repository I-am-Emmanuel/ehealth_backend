from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Availability, Hospital
from .serializers import AvailabilitySerializer, HospitalSerializer
from rest_framework.viewsets import ModelViewSet

class DoctorAvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Availability.objects.filter(doctor=self.request.user)

    def perform_create(self, serializer):
        
        serializer.save(doctor=self.request.user)

class DoctorAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Availability.objects.filter(doctor=self.request.user)


class HospitalViewSet(ModelViewSet):
    serializer_class = HospitalSerializer
    queryset = Hospital.objects.all()
    permission_classes = [permissions.AllowAny]
