"""
Patient models.
"""

import uuid

from django.db import models

from apps.core.validators import validate_icd10, validate_mrn


class Patient(models.Model):
    """
    Patient model.
    
    Identified by MRN (Medical Record Number).
    """
    
    SEX_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    mrn = models.CharField(
        max_length=6,
        unique=True,
        validators=[validate_mrn],
        help_text="Medical Record Number (6 digits)",
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Patient date of birth",
    )
    
    sex = models.CharField(
        max_length=10,
        choices=SEX_CHOICES,
        blank=True,
        null=True,
    )
    
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Weight in kilograms",
    )
    
    allergies = models.TextField(
        blank=True,
        null=True,
        help_text="Known allergies",
    )
    
    primary_diagnosis_code = models.CharField(
        max_length=10,
        validators=[validate_icd10],
        help_text="Primary ICD-10 diagnosis code",
    )
    
    primary_diagnosis_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Human-readable diagnosis description",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "patients"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["mrn"]),
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["primary_diagnosis_code"]),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN: {self.mrn})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class PatientDiagnosis(models.Model):
    """
    Additional diagnoses for a patient.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="diagnoses",
    )
    
    icd10_code = models.CharField(
        max_length=10,
        validators=[validate_icd10],
    )
    
    description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "patient_diagnoses"
        verbose_name_plural = "Patient diagnoses"
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["icd10_code"]),
        ]
    
    def __str__(self):
        return f"{self.patient.mrn} - {self.icd10_code}"


class MedicationHistory(models.Model):
    """
    Patient medication history.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medication_history",
    )
    
    medication_name = models.CharField(max_length=200)
    
    dosage = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g., '60 mg'",
    )
    
    frequency = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g., 'PO q6h PRN'",
    )
    
    is_current = models.BooleanField(
        default=True,
        help_text="Is the patient currently taking this medication?",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "medication_history"
        verbose_name_plural = "Medication histories"
        indexes = [
            models.Index(fields=["patient"]),
        ]
    
    def __str__(self):
        return f"{self.patient.mrn} - {self.medication_name}"
