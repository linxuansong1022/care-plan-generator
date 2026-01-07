"""
Order admin configuration.
"""

from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "patient",
        "provider",
        "medication_name",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "provider__npi",
        "provider__name",
        "medication_name",
    ]
    readonly_fields = ["id", "duplicate_check_hash", "created_at", "updated_at"]
    ordering = ["-created_at"]
    
    fieldsets = (
        (None, {
            "fields": ("id", "patient", "provider", "medication_name", "status")
        }),
        ("Clinical Data", {
            "fields": ("patient_records",),
            "classes": ("collapse",),
        }),
        ("Duplicate Detection", {
            "fields": ("duplicate_check_hash", "confirmed_not_duplicate"),
        }),
        ("Error Info", {
            "fields": ("error_message",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )
