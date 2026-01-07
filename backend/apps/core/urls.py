"""
API URL configuration.
Includes all app routes.
"""

from django.urls import include, path

urlpatterns = [
    path("providers/", include("apps.providers.urls")),
    path("patients/", include("apps.patients.urls")),
    path("orders/", include("apps.orders.urls")),
    path("care-plans/", include("apps.care_plans.urls")),
    path("reports/", include("apps.reports.urls")),
]
