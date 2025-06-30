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