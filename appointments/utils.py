from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from django.conf import settings
from django.core.cache import cache
import time
from core.task import password_url_email, send_password_was_reset_email, send_email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# from django.core.mail.message import EmailMultiAlternatives
import os
from django.template.loader import render_to_string
import pytz
from django.utils import timezone

def geocode_address(address):
    if settings.FAKE_GEOCODING:
        return settings.DEFAULT_LATITUDE, settings.DEFAULT_LONGITUDE
    
    cache_key = f"geocode_{hash(address)}"
    if cached := cache.get(cache_key):
        return cached
    
    retries = 0
    while retries < settings.GEOCODING_MAX_RETRIES:
        try:
            geolocator = Nominatim(
                user_agent=settings.GEOCODING_USER_AGENT,
                timeout=settings.GEOCODING_TIMEOUT
            )
            location = geolocator.geocode(address)
            if location:
                result = (location.latitude, location.longitude)
                cache.set(cache_key, result, settings.GEOCODING_CACHE_TTL)
                return result
        except GeocoderUnavailable:
            retries += 1
            time.sleep(2 ** retries)  # Exponential backoff
    
    return None, None


# def geocode_address(address):
#     """
#     Convert address to latitude/longitude using OpenStreetMap
#     Returns (lat, lng) or (None, None) on failure
#     """
#     try:
#         geolocator = Nominatim(
#             user_agent=settings.GEOCODING_USER_AGENT,
#             timeout=10
#         )
#         location = geolocator.geocode(address)
#         if location:
#             return location.latitude, location.longitude
#     except GeocoderUnavailable:
#         pass
#     return None, None

def send_payment_reminder_email(appointment):
    subject = "Complete Payment for Your Appointment"
    body = f"""
    Hello {appointment.user.first_name},
    
    Your appointment with Dr. {appointment.doctor.last_name} on 
    {appointment.date} at {appointment.time} has been confirmed.
    
    Please complete your payment within 2 hours to secure your appointment:
    {settings.FRONTEND_URL}/payment/{appointment.id}/
    
    If payment is not received by {appointment.payment_deadline.astimezone(pytz.timezone('Africa/Lagos')).strftime('%H:%M %p')}, 
    your appointment will be automatically cancelled.
    
    Appointment Fee: {'₦5,000' if appointment.doctor.specialization.lower() in ['family medicine', 'internal medicine'] else '₦10,000'}
    """
    
    # Use your existing email function
    return send_password_was_reset_email(
        to_email=appointment.user.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.EMAIL_HOST,
        body=body,
        subject=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )

def send_payment_expired_email(appointment):
    subject = "Appointment Cancelled - Payment Not Received"
    body = f"""
    Hello {appointment.user.first_name},
    
    Your appointment with Dr. {appointment.doctor.last_name} on 
    {appointment.date} at {appointment.time} has been cancelled because 
    we didn't receive your payment within the required time frame.
    
    You can book a new appointment at:
    {settings.FRONTEND_URL}/book-appointment/
    """
    
    return send_password_was_reset_email(
        to_email=appointment.user.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.DEFAULT_FROM_EMAIL,
        body=body,
        subject=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )

def send_payment_success_email(appointment):
    subject = "Appointment Payment Successful"
    body = f"""
    Dear {appointment.user.first_name},
    
    Your payment for the appointment with Dr. {appointment.doctor.last_name} 
    on {appointment.date} at {appointment.time} has been successfully processed.
    
    Your appointment is now confirmed and scheduled.
    
    Appointment Details:
    - Doctor: Dr. {appointment.doctor.last_name}
    - Date: {appointment.date}
    - Time: {appointment.time}
    - Specialization: {appointment.doctor.specialization}
    
    Thank you for choosing MediConnect!
    """
    
    # Use your existing email function
    return send_password_was_reset_email(
        to_email=appointment.user.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.DEFAULT_FROM_EMAIL,
        body=body,
        subject=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )

def send_doctor_confirmation_email(appointment):
    subject = "Patient Payment Received - Appointment Confirmed"
    body = f"""
    Dr. {appointment.doctor.last_name},
    
    Your patient {appointment.user.first_name} has successfully completed payment 
    for their appointment scheduled on {appointment.date} at {appointment.time}.
    
    The appointment is now confirmed and scheduled.
    
    Patient Details:
    - Name: {appointment.user.first_name} {appointment.user.last_name}
    - Email: {appointment.user.email}
    - Appointment Date: {appointment.date}
    - Appointment Time: {appointment.time}
    
    Please prepare for this consultation.
    """
    
    # Use your existing email function
    return send_password_was_reset_email(
        to_email=appointment.doctor.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.EMAIL_HOST,
        body=body,
        subject=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )

def send_approval_email(appointment):
    subject = "Appointment Approved"
    body = f"""
    Hello {appointment.user.first_name},\n\n
    
    Your appointment with Dr. {appointment.doctor.last_name} on 
    {appointment.date} at {appointment.time} has been approved but not yet confirmed.\n
    
    Please ensure you make the payment on the doctor's details within 2hrs so that your consultation will \
        be finalised with Dr {appointment.doctor.first_name}.\n\n
    
    Payment Details:
    Log in to your account, under you appointment section, you will find the payment link for this appointment.\n\n
    
    Thank you for choosing MediConnect!
    """
    return send_email(
        to_email=appointment.user.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.EMAIL_HOST,
        body=body,
        title=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )

def send_doctor_cancellation_email(appointment):
    subject = "Appointment Cancelled by Doctor"
    body = f"""
    Hello {appointment.user.first_name},\n\n
    
    Your appointment with Dr. {appointment.doctor.last_name} on 
    {appointment.date} at {appointment.time} has been cancelled by the doctor.\n
    
    Reason: {appointment.cancellation_reason if appointment.cancellation_reason else 'No reason provided'}\n\n
    
    You can book a new appointment at:
    {settings.FRONTEND_URL}dashboard/\n\n
    
    Thank you for choosing MediConnect!
    """
    
    return send_email(
        to_email=appointment.user.email,
        email_port=settings.EMAIL_PORT,
        sender_email=settings.EMAIL_HOST,
        body=body,
        title=subject,
        sender_password=settings.EMAIL_HOST_PASSWORD
    )


# Convert Python's weekday (Monday=0) to model's weekday (Monday=1)
def model_weekday(py_weekday):
    """Convert Python weekday (Monday=0) to model weekday (Monday=1)"""
    return (py_weekday + 1) % 7  # Sunday wraps from 6 to 0

def _calculate_this_week_date_range(date):

    start_of_week = date - timezone.timedelta(days=date.weekday())  # Monday
    end_of_week = start_of_week + timezone.timedelta(days=6)  # Sunday
    return start_of_week, end_of_week

def _calculate_this_month_date_range(date):
    start_of_month = date.replace(day=1)
    if date.month == 12:
        end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timezone.timedelta(days=1)
    else:
        end_of_month = date.replace(month=date.month + 1, day=1) - timezone.timedelta(days=1)
    return start_of_month, end_of_month

# print(_calculate_this_week_date_range(timezone.now().date()))