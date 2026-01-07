"""
Order model.
"""

import uuid

from django.db import models

from apps.patients.models import Patient
from apps.providers.models import Provider


class Order(models.Model):
    """
    Order for care plan generation.
    
    Links a patient, provider, and medication with clinical records.
    """
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    
    medication_name = models.CharField(
        max_length=200,
        help_text="Name of the medication being ordered",
    )
    
    patient_records = models.TextField(
        help_text="Clinical notes / patient records for care plan generation",
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    
    # For duplicate detection
    duplicate_check_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash for duplicate detection",
    )
    
    confirmed_not_duplicate = models.BooleanField(
        default=False,
        help_text="User confirmed this is not a duplicate",
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error details if status is 'failed'",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["status"]),
            models.Index(fields=["duplicate_check_hash"]),
            models.Index(fields=["-created_at"]),
        ]
    
    def __str__(self):
        return f"Order {self.id} - {self.patient.mrn} - {self.medication_name}"
    
    @property
    def has_care_plan(self):
        """Check if care plan exists."""
        return hasattr(self, "care_plan") and self.care_plan is not None
