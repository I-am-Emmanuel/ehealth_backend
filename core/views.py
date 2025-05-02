from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .serializer import DoctorSerializer, PatientSerializer,MedicalPractitionerSerializer
from .models import MedicalPracticioner
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterDoctorAPI(generics.GenericAPIView):
    serializer_class = DoctorSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  # Creates the user
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": DoctorSerializer(user).data,  # Optional: User details
            "access": str(refresh.access_token),  # JWT access token
            "refresh": str(refresh),              # JWT refresh token
        }, status=status.HTTP_201_CREATED)
    
class RegisterPatientAPI(generics.GenericAPIView):
    serializer_class = PatientSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": PatientSerializer(user).data})
    
class ValidateDoctorLicense(generics.GenericAPIView):
    serializer_class = MedicalPractitionerSerializer

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
        


