from django.contrib.auth import get_user_model
from rest_framework import serializers
from . models import MedicalPracticioner

User = get_user_model()

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','first_name', 'last_name', 'gender','email', 'liscence_expiry_date', 'phone', 'username','password', )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','first_name', 'last_name', 'gender', 'address', 'email', 'phone', 'username','password', )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    

# class DoctorLicenseValidationSerializer(serializers.Serializer):
#     license_number = serializers.CharField(max_length=20)

class MedicalPractitionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalPracticioner
        fields = '__all__'
