import os
from datetime import timedelta

"""Production configuration for Speedpay.

This file imports all base settings from `settings.py` and then overrides
values that should differ in a production environment.
"""

from .settings import *  # noqa: F403,F401

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Allowed hosts must be explicitly set in .env (comma‑separated)
# Example: ALLOWED_HOSTS=example.com,www.example.com
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Email backend – replace with real SMTP credentials in .env
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# CORS origins also come from .env
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')

# JWT token lifetimes
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_EXPIRATION_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_EXPIRATION_DAYS', '1')),
    # keep the rest of the defaults from base settings
}
