from django.core.exceptions import ValidationError

def file_validators(file_size):
    max_size = 500 
    if file_size > max_size * 1024:
        raise ValidationError(f"File must not be greater than {500}KB!")