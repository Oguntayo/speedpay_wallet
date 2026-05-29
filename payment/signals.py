import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Account

from .tasks import send_registration_email_task

User = get_user_model()

def generate_unique_account_number():
    while True:
        account_number = str(random.randint(100000, 999999))
        if not Account.objects.filter(account_number=account_number).exists():
            return account_number

@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        account_number = generate_unique_account_number()
        Account.objects.create(user=instance, account_number=account_number)
        
        # Send registration email via Celery
        send_registration_email_task.delay(instance.email, instance.first_name, account_number)
