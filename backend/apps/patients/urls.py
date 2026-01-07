"""
Patient URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PatientViewSet

router = DefaultRouter()
router.register("", PatientViewSet, basename="patient")

urlpatterns = [
    path("", include(router.urls)),
]
