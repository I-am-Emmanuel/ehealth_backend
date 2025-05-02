from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from . models import MedicalPracticioner

User = get_user_model()

class DoctorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all(), message="This email is already in use.")
    ])
    class Meta:
        model = User
        fields = ('id','first_name', 'last_name', 'gender','email', 'speciality', 'license_expiry_date', 'phone', 'username','password','is_med' )
        extra_kwargs = {'password': {'write_only': True},
                        'is_med': {'read_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password') 
        validated_data['is_med'] = True            
        user = User.objects.create(**validated_data)  
        user.set_password(password)
        user.save()
        return user


class PatientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all(), message="This email is already in use.")
    ])
    class Meta:
        model = User
        fields = ('id','first_name', 'last_name', 'gender', 'address', 'email', 'phone', 'username','password', )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class MedicalPractitionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalPracticioner
        fields = '__all__'
