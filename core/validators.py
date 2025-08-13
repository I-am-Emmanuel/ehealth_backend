from django.core.exceptions import ValidationError
# from datetime import timezone
from django.utils import timezone

def file_validators(file):
    max_size = 500 
    if file.size > max_size * 1024:
        raise ValidationError(f"File must not be greater than {500}KB!")
    
def validate_future_date(value):
        if value and value < timezone.now().date():
            raise ValidationError("License expiry date must be in the future")
        
def validate_phone_number(value):
    if not value.isdigit():
        raise ValidationError(f'Your number should not include any character')
    if len(value) < 11:
        raise ValidationError(f'Phone number length should be 11')