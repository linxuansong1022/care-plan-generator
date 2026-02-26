"""
Patient admin configuration.
"""

from django.contrib import admin

from .models import MedicationHistory, Patient, PatientDiagnosis


class PatientDiagnosisInline(admin.TabularInline):
    model = PatientDiagnosis
    extra = 0


class MedicationHistoryInline(admin.TabularInline):
    model = MedicationHistory
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["mrn", "first_name", "last_name", "primary_diagnosis_code", "created_at"]
    search_fields = ["mrn", "first_name", "last_name"]
    list_filter = ["sex", "primary_diagnosis_code"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["last_name", "first_name"]
    inlines = [PatientDiagnosisInline, MedicationHistoryInline]


@admin.register(PatientDiagnosis)
class PatientDiagnosisAdmin(admin.ModelAdmin):
    list_display = ["patient", "icd10_code", "is_primary", "created_at"]
    search_fields = ["patient__mrn", "icd10_code"]


@admin.register(MedicationHistory)
class MedicationHistoryAdmin(admin.ModelAdmin):
    list_display = ["patient", "medication_name", "dosage", "is_current", "created_at"]
    search_fields = ["patient__mrn", "medication_name"]
    list_filter = ["is_current"]
