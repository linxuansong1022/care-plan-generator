"""
Provider serializers.
"""

from rest_framework import serializers

from apps.core.validators import NPIValidator

from .models import Provider


class ProviderSerializer(serializers.ModelSerializer):
    """Serializer for Provider model."""
    
    class Meta:
        model = Provider
        fields = ["id", "npi", "name", "phone", "fax", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def validate_npi(self, value):
        """Validate NPI with Luhn checksum."""
        is_valid, error = NPIValidator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
    
    def validate_name(self, value):
        """Clean and validate provider name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Provider name is required")
        return " ".join(value.split())  # Normalize whitespace


class ProviderCreateSerializer(ProviderSerializer):
    """Serializer for creating providers (used in order creation)."""
    
    class Meta(ProviderSerializer.Meta):
        fields = ["npi", "name", "phone", "fax"]


class ProviderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing providers."""
    
    class Meta:
        model = Provider
        fields = ["id", "npi", "name"]
