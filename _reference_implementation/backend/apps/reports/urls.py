"""
Report export URL configuration.
"""

from django.urls import path

from .views import (
    export_medication_summary,
    export_orders,
    export_patient_history,
    export_provider_report,
)

urlpatterns = [
    path("orders/export/", export_orders, name="export-orders"),
    path("providers/export/", export_provider_report, name="export-providers"),
    path("patients/<str:mrn>/export/", export_patient_history, name="export-patient"),
    path("medications/export/", export_medication_summary, name="export-medications"),
]
