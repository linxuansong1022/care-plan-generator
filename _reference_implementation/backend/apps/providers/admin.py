"""
Provider admin configuration.
"""

from django.contrib import admin

from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "npi", "phone", "created_at"]
    search_fields = ["name", "npi"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["name"]
