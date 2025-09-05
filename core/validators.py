from django.core.exceptions import ValidationError
# from datetime import timezone
from django.utils import timezone
# import magic # python-magic to detect MIME type

HEALTH_RECORD_ALLOWED_FILE_TYPES = ['application/pdf','application/msword', 'image/jpeg']

PROFILE_IMAGE_ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/jpg']

import mimetypes



def file_validators(file):
    mime_type, _ = mimetypes.guess_type(file.name)
    print(f"Validating file: {file.name}, MIME type: {mime_type}")  # Debugging
    if mime_type not in HEALTH_RECORD_ALLOWED_FILE_TYPES:
        raise ValidationError(f"File type {mime_type} is not allowed. Allowed types: {', '.join(HEALTH_RECORD_ALLOWED_FILE_TYPES)}")
    if file.size > 500 * 1024:
        raise ValidationError("File must not be greater than 500KB!")

    

def validate_image(file):
    mime_type, _ = mimetypes.guess_type(file.name)
    print(f"Validating image: {file.name}, MIME type: {mime_type}")  # Debugging
    if mime_type not in PROFILE_IMAGE_ALLOWED_FILE_TYPES:
        raise ValidationError(f"Unsupported file type: {mime_type}")
    if file.size > 500 * 1024:
        raise ValidationError("Profile image file size must not exceed 500KB.")
    
def validate_future_date(value):
        if value and value < timezone.now().date():
            raise ValidationError("License expiry date must be in the future")
        
def validate_phone_number(value):
    if not value.isdigit():
        raise ValidationError(f'Your number should not include any character')
    if len(value) < 11:
        raise ValidationError(f'Phone number length should be 11')
    
def validate_age(value):
    today = timezone.now().date()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError("You must be at least 18 years old to register.")

def validate_future_dob(value):
    today = timezone.now().date()
    if value > today:
        raise ValidationError('Your age cannot be greater than today')