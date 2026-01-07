"""
Care Plan admin configuration.
"""

from django.contrib import admin

from .models import CarePlan


@admin.register(CarePlan)
class CarePlanAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "llm_model",
        "total_tokens",
        "generation_time_ms",
        "generated_at",
    ]
    list_filter = ["llm_model", "generated_at"]
    search_fields = ["order__id", "order__patient__mrn"]
    readonly_fields = [
        "id",
        "order",
        "llm_model",
        "llm_prompt_tokens",
        "llm_completion_tokens",
        "generation_time_ms",
        "generated_at",
        "created_at",
    ]
    ordering = ["-generated_at"]
    
    fieldsets = (
        (None, {
            "fields": ("id", "order")
        }),
        ("Content", {
            "fields": ("content", "file_path", "file_format"),
        }),
        ("LLM Metadata", {
            "fields": (
                "llm_model",
                "llm_prompt_tokens",
                "llm_completion_tokens",
                "generation_time_ms",
            ),
        }),
        ("Timestamps", {
            "fields": ("generated_at", "created_at"),
        }),
    )
