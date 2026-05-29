from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_password_reset_email_task(email, reset_link):
    send_mail(
        'Password Reset Request',
        f'Hi,\n\nYou requested a password reset. Click the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email.',
        'no-reply@speedpay.com',
        [email],
        fail_silently=True,
    )
