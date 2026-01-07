"""
Care Plan URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CarePlanViewSet

router = DefaultRouter()
router.register("", CarePlanViewSet, basename="careplan")

urlpatterns = [
    path("", include(router.urls)),
]
