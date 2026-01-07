"""
Settings module.
Default to development settings.
"""

import os

environment = os.environ.get("DJANGO_ENV", "development")

if environment == "production":
    from .production import *  # noqa
elif environment == "test":
    from .test import *  # noqa
else:
    from .development import *  # noqa
