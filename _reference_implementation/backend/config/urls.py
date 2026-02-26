"""
URL configuration for Care Plan Generator project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    # Prometheus metrics endpoint
    path("", include("django_prometheus.urls")),
]
