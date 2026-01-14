"""
Development settings.
"""

from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Add browsable API renderer in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"