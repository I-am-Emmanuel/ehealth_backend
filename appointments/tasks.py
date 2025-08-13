# tasks.py (Celery tasks)
from celery import shared_task
from django.utils import timezone
from .models import Appointment
from .utils import send_payment_expired_email

@shared_task
def check_payment_expiry(appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        if appointment.status == 'confirmed' and timezone.now() > appointment.payment_deadline:
            appointment.status = 'cancelled'
            appointment.save()
            send_payment_expired_email(appointment)
            return f"Appointment {appointment_id} cancelled due to non-payment"
        return f"Appointment {appointment_id} not expired or already paid"
    except Appointment.DoesNotExist:
        return f"Appointment {appointment_id} not found"