"""
Test settings - uses PostgreSQL for consistency with production.
"""

import os

from .base import *  # noqa

DEBUG = False

# Use PostgreSQL for tests (same as production)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "careplan_test"),
        "USER": os.environ.get("POSTGRES_USER", "careplan"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "careplan"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Celery - run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "DEBUG",
    },
}
