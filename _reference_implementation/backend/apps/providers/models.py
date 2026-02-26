"""
Provider model.
"""

import uuid

from django.db import models

from apps.core.validators import validate_npi


class Provider(models.Model):
    """
    Healthcare provider (e.g., physician, nurse practitioner).
    
    Identified by NPI (National Provider Identifier).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    npi = models.CharField(
        max_length=10,
        unique=True,
        validators=[validate_npi],
        help_text="National Provider Identifier (10 digits)",
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Provider full name",
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number",
    )
    
    fax = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Fax number",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "providers"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["npi"]),
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"
