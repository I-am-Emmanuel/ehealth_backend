from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator, ValidationError
from . models import MedicalPracticioner
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.conf import settings

User = get_user_model()
HEALTH_RECORD_ALLOWED_FILE_TYPES = ['application/pdf', 'application/msword']



class GeneralUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
    

PROFILE_IMAGE_ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/jpg']
class DoctorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[
        UniqueValidator(queryset=User.objects.all(), message="This email is already in use.")
    ])
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'gender', 'email','phone', 
                'speciality', 'hospital', 'license_expiry_date', 
                'username', 'password', 'is_med', 'profile_image')
        extra_kwargs = {
            'password': {'write_only': True},
            'is_med': {'read_only': True}
        }

    def get_profile_image(self, obj):
        if obj.profile_image:
            # Cloudinary URLs are already absolute
            return obj.profile_image.url
        return None

    def create(self, validated_data):
        password = validated_data.pop('password') 
        validated_data['is_med'] = True            
        user = User.objects.create(**validated_data)  
        user.set_password(password)
        user.save()
        return user
    
    def validate_profile_image(self, value):
        if value:
            if value.size > 500 * 1024:  # 500KB
                raise ValidationError("Profile image file size must not exceed 500KB.")
            if value.content_type not in PROFILE_IMAGE_ALLOWED_FILE_TYPES:
                raise ValidationError(f"Profile image file type must be one of {', '.join(PROFILE_IMAGE_ALLOWED_FILE_TYPES)}.") 
        return value

class PatientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all(), message="This email is already in use.")
    ])
    class Meta:
        model = User
        fields = ('id','first_name', 'last_name', 'gender', 'address','date_of_birth', 'email', 'phone', 'username','password', 'profile_image', 'health_record')
        extra_kwargs = {'password': {'write_only': True}}

    def get_profile_image(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None
    
    def get_health_record(self, obj):
        if obj.health_record:
            return obj.health_record.url
        return None
    
    def validate_health_record(self, value):
        if value:
            if value.size > 500 * 1024:  # 500KB
                raise ValidationError("Health record file size must not exceed 500KB.")
            if value.content_type not in HEALTH_RECORD_ALLOWED_FILE_TYPES:
                raise ValidationError(f"Health record file type must be one of {', '.join(HEALTH_RECORD_ALLOWED_FILE_TYPES)}.")
        return value
    
    def validate_profile_image(self, value):
        if value:
            if value.size > 500 * 1024:  # 500KB
                raise ValidationError("Profile image file size must not exceed 500KB.")
            if value.content_type not in PROFILE_IMAGE_ALLOWED_FILE_TYPES:
                raise ValidationError(f"Profile image file type must be one of {', '.join(PROFILE_IMAGE_ALLOWED_FILE_TYPES)}.") 
        return value
            
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class MedicalPractitionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalPracticioner
        fields = '__all__'

class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['profile_image']

class ProfileHealthRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['health_record']

class AuthTokenSerializer(serializers.Serializer):
    # email = serializers.EmailField()  # Use EmailField instead of CharField
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        username = attrs.get('username').lower().strip()
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            username=username,  # Important: use username kwarg for default backend
            password=password
        )
        
        if not user:
            raise serializers.ValidationError(
                _('Invalid email/password combination'),
                code='authorization'
            )
            
        if not user.is_active:
            raise serializers.ValidationError(
                _('User account is not active'),
                code='authorization'
            )
            
        attrs['user'] = user
        return attrs


class UpdatePasswordSerializer(serializers.Serializer):
    '''
    serializer for validating user's password before updating
    '''
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    confirm_password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        if len(password) < 8:
            raise ValidationError('Password must not be less than 8 characters!')
        if password != confirm_password:
            raise ValidationError("Password does not match!")
        '''
        Alert!! More validations to be done here!
        '''
        return super().validate(attrs)
    

# class AuthTokenSerializer(serializers.Serializer):
#     email = serializers.CharField(label=_("Email"))
    # password = serializers.CharField(
    #     label=_("Password"),
    #     style={'input_type': 'password'},
    #     trim_whitespace=False
    # )

#     def validate(self, attrs):
#         email = attrs.get('email')
#         password = attrs.get('password')

#         if email and password:
#             user = authenticate(request=self.context.get('request'),
#                                 email=email, password=password)
#             if not user:
#                 msg = _('Unable to log in with provided credentials.')
#                 raise serializers.ValidationError(msg, code='authorization')
#         else:
#             msg = _('Must include "email" and "password".')
#             raise serializers.ValidationError(msg, code='authorization')

#         attrs['user'] = user
#         return attrs

