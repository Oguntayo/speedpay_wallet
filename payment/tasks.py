from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_registration_email_task(email, first_name, account_number):
    send_mail(
        'Welcome to Speedpay!',
        f'Hi {first_name or "User"},\n\nYour registration was successful. Your account number is {account_number}.',
        'no-reply@speedpay.com',
        [email],
        fail_silently=True,
    )
