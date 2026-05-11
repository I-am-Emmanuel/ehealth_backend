from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Availability, Hospital, Appointment
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework import viewsets
from .serializers import HospitalSerializer,AvailabilitySerializer, HospitalDoctorsListSerializer, AppointmentSerializer
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, date
from django.db.models import Q, F
import calendar
import pytz
from django.utils import timezone
from datetime import time, datetime
from rest_framework.decorators import action
from .tasks import check_payment_expiry
from .utils import send_payment_reminder_email, send_doctor_confirmation_email, \
    send_payment_expired_email, send_payment_success_email, \
          model_weekday, send_confirm_email, send_doctor_cancellation_email, ai_match
from .tasks import check_payment_expiry
import requests
from django.conf import settings
from datetime import datetime
from django.db.models.aggregates import Count 

today = datetime.now().date()
print(today)
Users = get_user_model()




class DoctorAvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Availability.objects.filter(doctor=self.request.user)

    def perform_create(self, serializer): 
        serializer.save(doctor=self.request.user)

class DoctorAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Availability.objects.filter(doctor=self.request.user)
    
    def perform_destroy(self, instance):
        if instance.day_of_week == datetime.now().weekday():
            # If deleting today's availability, check for future appointments today
            tz = pytz.timezone('Africa/Lagos')
            now = timezone.now().astimezone(tz)
            future_appointments = Appointment.objects.filter(
                doctor=self.request.user,
                date=now.date(),
                time__gt=now.time(),
                status__in=['pending', 'approved', 'confirmed'],
                is_active=True
            )
            if future_appointments.exists():
                raise PermissionDenied("Cannot delete today's availability with future appointments scheduled.")
        instance.delete()
    
        
            
# from rest_framework.decorators import api_view, permission_classes

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def test_availability_view(request):
#     availabilities = Availability.objects.filter(doctor=request.user)
#     serializer = AvailabilitySerializer(availabilities, many=True)
#     return Response(serializer.data)

class HospitalViewSet(ModelViewSet):
    serializer_class = HospitalSerializer
    queryset = Hospital.objects.all()
    permission_classes = [permissions.AllowAny]


class NearbyHospitalsView(APIView):
    permission_classes = [permissions.AllowAny]
    """
    API to find hospitals near specified coordinates
    """
    
    def get(self, request):
        # Get query parameters
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 50)  # Default 50km radius (increased from 10km)
        
        # Validate parameters
        if not lat or not lng:
            return Response(
                {"error": "Missing latitude (lat) or longitude (lng) parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(radius)
            
            # Cap maximum radius at 500km to prevent excessive database queries
            if radius > 500:
                radius = 500
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid coordinate format. Must be numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get nearby hospitals
        hospitals = Hospital.nearby_hospitals(lat, lng, radius)
        serializer = HospitalSerializer(hospitals, many=True)

        
        return Response({
            "count": len(serializer.data),
            "user_location": {"latitude": lat, "longitude": lng},
            "radius_km": radius,
            "results": serializer.data
        })

class HospitalBySpeciality(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        speciality = request.query_params.get('speciality')
        if not speciality:
            return Response({"error": "speciality is required"}, status=400)
        print("SEARCH SPECIALITY:", speciality)
        print("MATCHED DOCTORS:", list(
            Users.objects.filter(
                is_med=True,
                speciality__icontains=speciality,
                license_expiry_date__gte=timezone.now().date()
            ).values("id", "speciality", "hospital_id")
        ))

        doctors = Users.objects.filter(
            is_med=True,
            speciality__icontains=speciality,
            license_expiry_date__gte=timezone.now().date()
        ).values_list('hospital', flat=True)

        hospitals = Hospital.objects.filter(id__in=doctors)
        return Response(HospitalSerializer(hospitals, many=True).data)


class HospitalBySymptoms(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        symptoms = request.query_params.get('symptoms')
        if not symptoms:
            return Response({"error": "symptoms is required"}, status=400)

        dict_result = ai_match(symptoms)

        print("AI RESULT:", dict_result)

        matched_doctors = Users.objects.filter(
            is_med=True,
            speciality__icontains=dict_result['speciality'],
            license_expiry_date__gte=timezone.now().date()
        )

        print("MATCHED DOCTORS:", list(
            matched_doctors.values("id", "first_name", "last_name", "speciality", "hospital_id")
        ))

        doctors = matched_doctors.values_list('hospital', flat=True)
        hospitals = Hospital.objects.filter(id__in=doctors)

        print("MATCHED HOSPITALS:", list(
            hospitals.values("id", "name", "city", "state")
        ))

        return Response({
            "ai_recommendation": dict_result['speciality'],
            "results": HospitalSerializer(hospitals, many=True).data
        })



class HospitalDoctorsListView(APIView):
    """
    API to list doctors in a specific hospital.
    Supports optional filtering by speciality.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, hospital_id):
        speciality = request.query_params.get("speciality", "").strip()
        today = timezone.now().date()

        try:
            if request.user.is_authenticated and request.user.is_med:
                return Response(
                    {
                        "error": "Medical professionals cannot access this endpoint with their medical accounts."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            hospital = Hospital.objects.get(id=hospital_id)

            doctors = Users.objects.filter(
                is_med=True,
                hospital=hospital,
                license_expiry_date__gte=today
            )

            # Apply speciality filter if provided
            if speciality:
                doctors = doctors.filter(speciality__icontains=speciality)

            serializer = HospitalDoctorsListSerializer(doctors, many=True)

            return Response(
                {
                    "hospital": hospital.name,
                    "speciality_filter": speciality if speciality else None,
                    "doctors": serializer.data
                },
                status=status.HTTP_200_OK,
            )

        except Hospital.DoesNotExist:
            return Response(
                {"error": "Hospital not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
    
class DoctorAppointmentBookingView(APIView):

    permission_classes = [permissions.AllowAny]
    
    def get(self, request, pk):
        """
        Get available appointment slots for a specific doctor
        """
        doctor = Users.objects.filter(id=pk, is_med=True).first()
        if not doctor:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Assuming Availability model has a foreign key to User (doctor)
        availability = Availability.objects.filter(doctor=doctor)
        serializer = AvailabilitySerializer(availability, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class DoctorAvailabilityView(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        # Get all availability records for the doctor
        availabilities = Availability.objects.filter(doctor_id=doctor_id)
        
        if not availabilities.exists():
            return Response({"error": "This doctor has no scheduled availability"}, status=status.HTTP_404_NOT_FOUND)
        
        # Structure response by day of week
        availability_by_day = {}
        for availability in availabilities:
            day_name = availability.get_day_of_week_display()
            if day_name not in availability_by_day:
                availability_by_day[day_name] = []
            
            availability_by_day[day_name].append({
                "id": availability.id,
                "start_time": availability.start_time.strftime('%H:%M'),
                "end_time": availability.end_time.strftime('%H:%M')
            })
        
        return Response(availability_by_day)



class DoctorTimeSlotView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        day_name = request.query_params.get('day')
        if not day_name:
            return Response({"error": "Day parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create mapping based on your Availability model's DAYS_OF_WEEK
        day_map = {
            'sunday': 0,
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6
        }
        
        day_number = day_map.get(day_name.lower())
        
        if day_number is None:
            return Response({"error": "Invalid day name"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            availability = Availability.objects.get(
                doctor_id=doctor_id,
                day_of_week=day_number
            )
        except Availability.DoesNotExist:
            return Response({"error": "Doctor not available on this day"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get current time in Nigeria timezone
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        today = now.date()

        
        # Calculate target date
        if model_weekday(today.weekday()) == day_number:
            # Today is the requested day in model's numbering
            next_date = today
        else:
            # Find next occurrence of this day
            # Adjust for the difference between Python's and model's weekday numbering
            days_ahead = (day_number - model_weekday(today.weekday())) % 7
            next_date = today + timedelta(days=days_ahead)
        
        # Combine with start_time to get datetime
        start_dt = datetime.combine(next_date, availability.start_time).replace(tzinfo=tz)
        
        # If the time is already in the past, shift to next week
        if start_dt < now:
            next_date += timedelta(days=7)
            start_dt += timedelta(days=7)
        
        # Get existing appointments
        # existing_appointments = Appointment.objects.filter(
        #     doctor_id=doctor_id,
        #     date=next_date,
        #     status__in=['pending', 'approved', 'confirmed', 'completed']
        # ).values_list('time', flat=True)

        existing_appointments = Appointment.objects.filter(
        doctor_id=doctor_id,
        date=next_date,
        is_active=True
        ).values_list('time', flat=True)
        
        booked_times = {t.strftime('%H:%M') for t in existing_appointments}
        
        # Generate time slots
        if availability.end_time <= availability.start_time:
            # Handle overnight shifts (e.g., 20:00-04:00)
            end_dt = datetime.combine(next_date + timedelta(days=1), availability.end_time).replace(tzinfo=tz)
        else:
            # Normal same-day shifts
            end_dt = datetime.combine(next_date, availability.end_time).replace(tzinfo=tz)
        
        current = start_dt
        available_slots = []
        
        while current + timedelta(hours=1) <= end_dt:
            if current > now:
                slot_start_str = current.time().strftime('%H:%M')
                slot_end = (current + timedelta(hours=1)).time().strftime('%H:%M')
                
                if slot_start_str not in booked_times:
                    available_slots.append({
                        'start': slot_start_str,
                        'end': slot_end
                    })
            
            current += timedelta(hours=1)
        
        return Response({
            "date": next_date.strftime('%Y-%m-%d'),
            "day": day_name,
            "day_number": day_number,
            "doctor_id": doctor_id,
            "available_slots": available_slots
        })


class BookAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        required_fields = ['doctor', 'date', 'time']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get Nigeria timezone
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        today = now.date()
        
        try:
            # Parse and validate appointment date/time
            app_date = date.fromisoformat(data['date'])
            app_time = time.fromisoformat(data['time'])
            app_datetime = datetime.combine(app_date, app_time, tzinfo=tz)
            
            # Check if appointment is in the past
            if app_datetime <= now:
                return Response({"error": "Cannot book appointment in the past"}, 
                              status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError:
            return Response({"error": "Invalid date or time format"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.is_med:
            return Response({"error": "Medical professionals cannot book appointments, with their medical accounts"}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Check for existing active appointments with same doctor FOR THIS USER
        existing_user_appointments = Appointment.objects.filter(
            user=request.user,
            doctor_id=data['doctor'],
            is_active=True,
            status__in=['pending', 'approved'],
        ).filter(
            Q(date__gt=today) | 
            Q(date=today, time__gt=now.time())
        )
        
        if existing_user_appointments.exists():
            return Response({
                "error": "You already have an active appointment with this doctor. "
                       "Please complete or cancel it before booking a new one."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for existing ACTIVE appointments at this time slot FOR ANY USER
        existing_slot_appointments = Appointment.objects.filter(
            doctor_id=data['doctor'],
            date=app_date,
            time=app_time,
            is_active=True  # Only check active appointments
        )
        
        if existing_slot_appointments.exists():
            return Response({
                "error": "This time slot is no longer available. Please choose another time."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if doctor exists and is available
        try:
            doctor = Users.objects.get(id=data['doctor'], is_med=True)
            
            # Convert Python weekday (Monday=0) to model's weekday (Monday=1)
            day_of_week_model = model_weekday(app_date.weekday())
            
            # Verify doctor availability
            same_day_availabilities = Availability.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week_model,
            )
            
            # Check previous day for night shifts
            prev_day_model = (day_of_week_model - 1) % 7
            prev_day_availabilities = Availability.objects.filter(
                doctor=doctor,
                day_of_week=prev_day_model,
            )
            
            available = False
            
            # Check same day availability
            for avail in same_day_availabilities:
                # Normal shift (same day)
                if avail.start_time <= avail.end_time:
                    if avail.start_time <= app_time <= avail.end_time:
                        available = True
                        break
                # Night shift (spans midnight)
                else:
                    if app_time >= avail.start_time:
                        available = True
                        break
            
            # Check previous day for continuing night shifts
            if not available:
                for avail in prev_day_availabilities:
                    if avail.start_time > avail.end_time:  # Night shift
                        if app_time <= avail.end_time:
                            available = True
                            break
            
            if not available:
                # Add debug information to response
                debug_info = {
                    "requested_time": app_time.strftime('%H:%M'),
                    "requested_day_model": day_of_week_model,
                    "same_day_availabilities": [
                        f"{avail.start_time}-{avail.end_time}" 
                        for avail in same_day_availabilities
                    ],
                    "prev_day_availabilities": [
                        f"{avail.start_time}-{avail.end_time}" 
                        for avail in prev_day_availabilities
                    ]
                }
                return Response({
                    "error": "Doctor not available at this time",
                    "debug": debug_info
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Users.DoesNotExist:
            return Response({"error": "Medical professional not found"}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Create the appointment
        appointment = Appointment.objects.create(
            user=request.user,
            doctor=doctor,
            date=app_date,
            time=app_time,
            day_of_week=app_date.weekday(),
            status='pending',
            is_active=True
        )
        
        return Response({
            "message": "Appointment booked successfully!",
            "appointment_id": appointment.id
        }, status=status.HTTP_201_CREATED)
class DoctorAppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Appointment.objects.all()

    def get_queryset(self):
        """Return filtered appointments for the authenticated doctor"""
        queryset = super().get_queryset().filter(doctor=self.request.user)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter and status_filter.lower() != 'all':
            queryset = queryset.filter(status=status_filter.lower())
        
        # print(f"Doctor's appointments: {queryset}")
        return queryset.order_by('-date', 'time')

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Approve an appointment"""
        appointment = self.get_object()
        
        if appointment.status != 'pending':
            return Response(
                {
                    "detail": "Appointment cannot be approved",
                    "reason": f"Current status is '{appointment.status}' but must be 'pending'",
                    "current_status": appointment.status,
                    "required_status": "pending"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
                
        appointment.status = 'confirmed'
        appointment.save()
        
        # Send approval email with payment link
        send_confirm_email(appointment)
        
        return Response(
            {"detail": "Patient appointment has been confirmed. Patient has been notified to make payment."},
            status=status.HTTP_200_OK
        )
    
    # @action(detail=True, methods=['post'])
    # def approve(self, request, pk=None):
    #     """Approve an appointment"""
    #     appointment = self.get_object()
        
    #     if appointment.status != 'pending':
    #         return Response(
    #             {
    #                 "detail": "Appointment cannot be approved",
    #                 "reason": f"Current status is '{appointment.status}' but must be 'pending'",
    #                 "current_status": appointment.status,
    #                 "required_status": "pending"
    #             },
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
                
    #     appointment.status = 'approved'
    #     appointment.save()
        
    #     # Send approval email with payment link
    #     send_approval_email(appointment)
        
    #     return Response(
    #         {"detail": "Appointment approved successfully. Patient has been notified to make payment."},
    #         status=status.HTTP_200_OK
    #     )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed"""
        appointment = self.get_object()
        
        if appointment.status != 'approved':
            return Response(
                {"detail": "Only confirmed appointments can be marked as completed."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if appointment.is_past_due():
            return Response(
                {"detail": "Cannot complete appointment before its scheduled time."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        appointment.status = 'completed'
        appointment.completion_date = datetime.now(pytz.timezone('Africa/Lagos'))
        appointment.save()
        
        return Response(
            {"detail": "Appointment marked as completed successfully."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Doctor-initiated cancellation - permanently blocks the slot"""
        appointment = self.get_object()
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        
        # Check if appointment is in the past
        appointment_datetime = datetime.combine(
            appointment.date,
            appointment.time
        ).replace(tzinfo=tz)
        
        if appointment_datetime < now:
            return Response(
                {"detail": "Cannot cancel past appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if appointment.status == 'cancelled':
            return Response(
                {"detail": "Appointment already cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if appointment.status not in ['pending', 'approved']:
            return Response(
                {"detail": "Only pending, approved or confirmed appointments can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark as cancelled by doctor
        appointment.status = 'cancelled'
        appointment.cancelled_by = 'doctor'
        appointment.cancellation_reason = request.data.get('reason', 'No reason provided')
        appointment.save()

        send_doctor_cancellation_email(appointment)
        
        return Response(
            {"detail": "Appointment cancelled and time slot permanently blocked."},
            status=status.HTTP_200_OK
        )

class PatientAppointmentView(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.AllowAny]  # Adjust permissions as needed

    def get_queryset(self):
        """Return only current user's appointments with automatic cancellation check"""
        queryset = Appointment.objects.filter(user=self.request.user)
        
        # Get current time in Africa/Lagos timezone
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        
        # Automatically cancel past appointments that are still pending/confirmed
        past_appointments = queryset.filter(
            status__in=['pending', 'approved'],
            date__lt=now.date()
        ) | queryset.filter(
            status__in=['pending', 'approved'],
            date=now.date(),
            time__lt=now.time()
        )
        
        for appointment in past_appointments:
            appointment.status = 'cancelled'
            appointment.cancellation_reason = "Automatically cancelled due to being past the scheduled time."
            appointment.save()
        
        # print(f'My appointments: {queryset}')
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Patient-initiated cancellation - marks as inactive but keeps record"""
        appointment = self.get_object()
        tz = pytz.timezone('Africa/Lagos')
        now = timezone.now().astimezone(tz)
        
        # Check if appointment is in the past
        appointment_datetime = datetime.combine(
            appointment.date,
            appointment.time
        ).replace(tzinfo=tz)
        
        if appointment_datetime < now:
            return Response(
                {"detail": "Cannot cancel past appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not appointment.is_active:
            return Response(
                {"detail": "Appointment already cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if appointment.status not in ['pending', 'approved']:
            return Response(
                {"detail": "Only pending or approved appointments can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Mark as inactive instead of changing status
        appointment.is_active = False
        appointment.status = 'cancelled'
        appointment.cancellation_reason = request.data.get('reason', 'No reason provided')
        appointment.save()
        
        return Response(
            {"detail": "Appointment cancelled successfully. Time slot is now available."},
            status=status.HTTP_200_OK
        )
    
    def list(self, request, *args, **kwargs):
        """Override list to ensure automatic cancellation happens before response"""
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TodaysConfirmedAppointmentsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """API to get today's appointments for the authenticated doctor
    """
    def get(self, request):
        tz = pytz.timezone('Africa/Lagos')
        today = timezone.now().astimezone(tz).date()
        
        # Get today's appointments for the authenticated doctor
        appointment_count = Appointment.objects.filter(
            doctor=request.user,
            date=today,
            status = 'confirmed'
        ).count()
        
        print(f"Today's confirmed appointments count: {appointment_count}")
        if not appointment_count:
            return Response({"message": "No confirmed appointments for today"}, status=status.HTTP_200_OK)
        # print(f"Today's confirmed appointments count: {appointment_count}")
        return Response({'count': appointment_count}, status=status.HTTP_200_OK)

class EachWeeklyAppointmentsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """API to get this week's appointments for the authenticated doctor
    """
    def get(self, request):
        try:
            tz = pytz.timezone('Africa/Lagos')
            today = timezone.now().astimezone(tz).date()
            from .utils import _calculate_this_week_date_range
            start_of_week, end_of_week = _calculate_this_week_date_range(today)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            # Get this week's appointments for the authenticated doctor
            appointment = Appointment.objects.filter(
                doctor=request.user,
                date__range=(start_of_week, end_of_week),)

        except Appointment.DoesNotExist:
            return Response({"message": "No appointments for this week"}, status=status.HTTP_404_NOT_FOUND)
            
        confirmed_count = appointment.filter(status='confirmed').count()
        completed_count = appointment.filter(status='completed').count()
        pending_count = appointment.filter(status='pending').count()
        approved_count = appointment.filter(status='approved').count()
        cancelled_count = appointment.filter(status='cancelled').count()
        return Response({
            'total_count' : appointment.count(),
            'confirmed_appointments': confirmed_count,
            'completed_appointments': completed_count,
            'pending_appointments': pending_count,
            'approved_appointments': approved_count,
            'cancelled_appointments': cancelled_count,
        }, status=status.HTTP_200_OK)  


class EachMonthlyAppointmentsView(APIView):
    '''
    API to get this month's appointments for the authenticated doctor
    '''
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            tz = pytz.timezone('Africa/Lagos')
            today = timezone.now().astimezone(tz).date()
            from .utils import _calculate_this_month_date_range
            start_of_month, end_of_month = _calculate_this_month_date_range(today)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            # Get this month's appointments for the authenticated doctor
            appointment = Appointment.objects.filter(
                doctor=request.user,
                date__range=(start_of_month, end_of_month),)

        except Appointment.DoesNotExist:
            return Response({"message": "No appointments for this month"}, status=status.HTTP_404_NOT_FOUND)
            
        confirmed_count = appointment.filter(status='confirmed').count()
        completed_count = appointment.filter(status='completed').count()
        pending_count = appointment.filter(status='pending').count()
        approved_count = appointment.filter(status='approved').count()
        cancelled_count = appointment.filter(status='cancelled').count()
        return Response({
            'total_count' : appointment.count(),
            'confirmed_appointments': confirmed_count,
            'completed_appointments': completed_count,
            'pending_appointments': pending_count,
            'approved_appointments': approved_count,
            'cancelled_appointments': cancelled_count,
        }, status=status.HTTP_200_OK)

class DoctorsCompletedAppointmentsView(APIView):
    """API to get all completed appointments for a specific doctor with search and date range filtering"""
    # permission_classes = [permissions.AllowAny]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, doctor_id):
        try:
            doctor = Users.objects.get(id=doctor_id, is_med=True)
        except Users.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get query parameters
        search_query = request.query_params.get('search', '')
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        
        appointments = Appointment.objects.filter(
            doctor=doctor,
            status='completed'
        ).select_related('user').order_by('-date', 'time')
        
        # Apply search filter if provided
        if search_query:
            appointments = appointments.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        # Apply date range filter if provided
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                appointments = appointments.filter(date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                appointments = appointments.filter(date__lte=end_date)
            except ValueError:
                pass
        
        if not appointments.exists():
            return Response({"message": "No completed appointments found."}, 
                          status=status.HTTP_200_OK)
        
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


