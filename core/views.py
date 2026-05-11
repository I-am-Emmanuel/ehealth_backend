from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, ListModelMixin
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status
from .serializer import DoctorSerializer, PatientSerializer,MedicalPractitionerSerializer, AuthTokenSerializer, ProfileImageSerializer, GeneralUserSerializer, UpdatePasswordSerializer
from .models import MedicalPracticioner, PasswordResetKey
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
from .utils import make_password_token_and_key
from .task import send_password_token, send_password_was_reset_email
from django.utils import timezone
import cloudinary.uploader
from .validators import validate_image, file_validators
# from .utils import password_url_email, password_token

User = get_user_model()


class LoginAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        try:
            serializer = AuthTokenSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_doctor': user.is_med
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            return Response(
                {"detail": "Authentication failed. Please check your credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )
class RegisterDoctorAPI(generics.GenericAPIView):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  # Creates the user
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": DoctorSerializer(user).data,  
            "access": str(refresh.access_token),  
            "refresh": str(refresh),              
        }, status=status.HTTP_201_CREATED)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_med=False)
    serializer_class = PatientSerializer
    permission_classes = [permissions.AllowAny]  # Adjust permissions as needed

    @action(detail=False, methods=['get'])
    def multiple(self, request):
        ids = request.query_params.get('ids', '')
        if not ids:
            return Response(
                {"error": "No doctor IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            patient_ids = [int(id) for id in ids.split(',')]
            patients = self.queryset.filter(id__in=patient_ids)
            serializer = self.get_serializer(patients, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "Invalid patient IDs format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    def retrieve(self, request, pk=None):
        patient = get_object_or_404(self.queryset, pk=pk)
        serializer = self.get_serializer(patient)
        return Response(serializer.data)
    


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_med=True)
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]  # Adjust permissions as needed
    # permission_classes = [permissions.AllowAny]  # Adjust permissions as needed
    
    # Custom action to get multiple doctors by IDs
    @action(detail=False, methods=['get'])
    def multiple(self, request):
        ids = request.query_params.get('ids', '')
        if not ids:
            return Response(
                {"error": "No doctor IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            doctor_ids = [int(id) for id in ids.split(',')]
            doctors = self.queryset.filter(id__in=doctor_ids)
            serializer = self.get_serializer(doctors, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "Invalid doctor IDs format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Override default list to add filtering capabilities
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add any additional filtering you need here
        specialization = request.query_params.get('speciality')
        if specialization:
            queryset = queryset.filter(speciality=specialization)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # Override retrieve to add custom response if needed
    def retrieve(self, request, pk=None):
        doctor = get_object_or_404(self.queryset, pk=pk)
        serializer = self.get_serializer(doctor)
        return Response(serializer.data)
    
    # Example of custom action for doctor availability
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        doctor = self.get_object()
        return Response({
            "doctor": doctor.id,
            "availability": "Add your availability data here"
        })


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_med:
            serializer = DoctorSerializer(user, context={'request': request})
            return Response(serializer.data)
        elif not user.is_med:
            serializer = PatientSerializer(user, context={'request': request})
            return Response(serializer.data)
        return Response({'error': 'Invalid user type.'}, status=status.HTTP_403_FORBIDDEN)

    def put(self, request):
        user = request.user
        if user.is_med:
            serializer = DoctorSerializer(user, data=request.data, partial=True, context={'request': request})
        elif not user.is_med:
            serializer = PatientSerializer(user, data=request.data, partial=True, context={'request': request})
        else:
            return Response({'error': 'Invalid user type.'}, status=status.HTTP_403_FORBIDDEN)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

    def delete(self, request):
        user = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class ProfileImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        if 'profile_image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=400)
        
        try:
            validate_image(request.FILES['profile_image'])
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        
        user = request.user
        try:
            # Generate a consistent public_id based on user ID
            public_id = f"Mediconnect/UserProfileImage/user_{user.id}"
            
            result = cloudinary.uploader.upload(
                request.FILES['profile_image'],
                public_id=public_id,  # Use consistent public_id for overwriting
                resource_type="image",
                overwrite=True,
                invalidate=True,
                transformation=[
                    {'width': 500, 'height': 500, 'crop': 'limit'},
                    {'quality': 'auto:best'}
                ]
            )
            
            user.profile_image = result['secure_url']
            user.save()
            
            return Response({
                'message': 'Profile image updated successfully',
                'profile_image': user.profile_image
            }, status=200)
            
        except Exception as e:
            print(f"Error in profile image upload: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)


class ProfileHealthRecordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        user = request.user
        if user.is_med:
            return Response({'error': 'Doctors cannot upload health records.'}, status=status.HTTP_403_FORBIDDEN)
        if 'health_record' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        try:
            file_validators(request.FILES['health_record'])
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        try:
            result = cloudinary.uploader.upload(
                request.FILES['health_record'],
                folder="Mediconnect/UsersHealthRecord/",
                resource_type="raw",
                overwrite=True,
                invalidate=True
            )
            if user.health_record:
                public_id = user.health_record.public_id
                cloudinary.uploader.destroy(public_id)
            user.health_record = result['secure_url']
            user.save()
            serializer = PatientSerializer(user, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
class RegisterPatientAPI(generics.GenericAPIView):
    serializer_class = PatientSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": PatientSerializer(user).data,  
            "access": str(refresh.access_token), 
            "refresh": str(refresh),              
        }, status=status.HTTP_201_CREATED)
    
class ValidateDoctorLicense(generics.GenericAPIView):
    serializer_class = MedicalPractitionerSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        
        license_number = request.query_params.get("license_number")

        if not license_number:
            return Response({'error': 'license number query parameter is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        license = MedicalPracticioner.objects.filter(license_number=license_number).first()

        if license:
            if license.license_expiry_date < datetime.today().date():
                return Response({'error': 'Your License has expired. You need to renew it to complete your registration!'}, status=status.HTTP_403_FORBIDDEN)
            serializer = MedicalPractitionerSerializer(license, context={'request': request})
            return Response({'data': serializer.data})
        else:
            return Response({'error': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

class PasswordResetView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, email=email)
        token = make_password_token_and_key(6, 'token')
        reset_activation_token = make_password_token_and_key(24, 'reset_activation')
        expiry_date = timezone.now() + timezone.timedelta(minutes=15)
        
        # Create or update existing key
        PasswordResetKey.objects.update_or_create(
            user=user,
            defaults={
                'key': token,
                'expiry_date': expiry_date,
                'token_activation_code': reset_activation_token
            }
        )

        # Send email
        email_sent = send_password_token(
            user.email, 
            token, 
            reset_activation_token, 
            email_port=settings.EMAIL_PORT, 
            sender_email=settings.EMAIL_HOST,  
            sender_password=settings.EMAIL_HOST_PASSWORD
        )

        if not email_sent:
            return Response({'message': 'Failed to send email'}, 
                          status=status.HTTP_501_NOT_IMPLEMENTED)

        return Response({'message': 'Password reset instructions sent to your email'}, 
                      status=status.HTTP_200_OK)

class ConfirmPasswordResetActivationToken(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        code = request.data.get('code', None)
        activation_code_qs = PasswordResetKey.objects.filter(
            token_activation_code=code, matched=False)
        # print('hi')
        if activation_code_qs.exists():
            activation_code = activation_code_qs.first()
            if activation_code.expiry_date <= timezone.now() + timezone.timedelta(minutes=15):
                return Response({'valid': True}, status=status.HTTP_200_OK)
            else:
                return Response({'valid': False,
                                 'message': 'The reset link has already expired.'},
                                status=status.HTTP_200_OK)
        return Response({'valid': False}, status=status.HTTP_200_OK)


class ConfirmPasswordResetTokenView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        code = request.data.get('code', None)
        if code is not None:
            key_qs = PasswordResetKey.objects.filter(key=code, matched=False)
            if key_qs.exists():
                key = key_qs[0]
                if key.expiry_date <= timezone.now() + timezone.timedelta(minutes=15):
                    pass
                else:
                    key.matched = True
                    key.save()
                    return Response(
                        {'message': 'This password token has expired!'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'message': 'Successful!'}, status=status.HTTP_200_OK)
                # else:
            else:
                return Response(
                    {'message': 'This token does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'Error'}, status=status.HTTP_400_BAD_REQUEST)

class SetNewPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        # data = cipher.decrypt_nested(request.data)
        data = request.data
        if not data:
            return Response({'error': 'Invalid data'},
                            status=status.HTTP_400_BAD_REQUEST)
        p1 = data.get('p1', None)
        p2 = data.get('p2', None)
        resetkey = data.get('resetkey', None)
        if(p1 == p2 and not any(x is None for x in [p1, p2, resetkey])):
            password = p1
            if not any(letter.isdigit() for letter in password):
                return Response(
                    {'error': 'Password must contain at least one digit !'}, status=status.HTTP_400_BAD_REQUEST)
            key_qs = PasswordResetKey.objects.filter(
                key=resetkey, matched=False)
            print(key_qs)
            if key_qs.exists():
                key = key_qs[0]
                if key.expiry_date < timezone.now() - timezone.timedelta(minutes=15):
                    return Response(
                        {'error': 'Token for this password reset has expired !'}, status=status.HTTP_400_BAD_REQUEST)
                key.user.set_password(password)
                key.user.save()
                key.delete()
                send_password_was_reset_email(key.user.email, email_port=settings.EMAIL_PORT, sender_email=settings.EMAIL_HOST, sender_password=settings.EMAIL_HOST_PASSWORD)
                return Response(
                    {'message': 'Password Reset successful!'}, status=status.HTTP_200_OK)
        return Response({'error': 'Request failed!. Invalid Data'},
                        status=status.HTTP_400_BAD_REQUEST)




# practise task

# def testing(request):
#     return render(request, 'docs.html', {'name': 'User'})
def view_doctors(request):
    # queryset = MedicalPracticioner.objects.all()
    # queryset = MedicalPracticioner.objects.filter(first_name__istartswith='S')
    # queryset = MedicalPracticioner.objects.filter(license_expiry_date__year__range=('2025','2026'))
    # queryset = MedicalPracticioner.objects.filter(license_expiry_date__year=('2025'))
    # queryset = MedicalPracticioner.objects.filter(license_expiry_date__isnull=(False))
    # queryset = MedicalPracticioner.objects.all()[:5]
    doctor = MedicalPracticioner.objects.get(pk='0054-3026')
    # serializer = MedicalPractitionerSerializer(queryset)
    # return Response(serializer.data, status=status.HTTP_200_OK)

    # return render(request, "docs.html", {'doctors': list(queryset)})
    return render(request, "docs.html", {'doctors': doctor})

#     Mommy - 0013-2646
# Joscelin - 0046-2575
# Sabina - 0049-4900
# Isidoro - 0054-3026
# Cal - 0064-3600