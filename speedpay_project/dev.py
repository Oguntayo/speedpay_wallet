# dev.py
"""Development settings for Speedpay project.
These extend the base settings and enable DEBUG mode.
"""

from .settings import *  # noqa: F403,F401

# Override base settings for development
DEBUG = True
ALLOWED_HOSTS = ['*']
