"""
Order serializers.
"""

from rest_framework import serializers

from apps.core.validators import ICD10Validator, MRNValidator, NPIValidator
from apps.patients.models import MedicationHistory, Patient, PatientDiagnosis
from apps.patients.serializers import PatientListSerializer
from apps.providers.models import Provider
from apps.providers.serializers import ProviderListSerializer

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    """Full serializer for Order model."""
    
    patient = PatientListSerializer(read_only=True)
    provider = ProviderListSerializer(read_only=True)
    has_care_plan = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            "id",
            "patient",
            "provider",
            "medication_name",
            "patient_records",
            "status",
            "has_care_plan",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "error_message", "created_at", "updated_at"]


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing orders."""
    
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    provider_npi = serializers.CharField(source="provider.npi", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    has_care_plan = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            "id",
            "patient_mrn",
            "patient_name",
            "provider_npi",
            "provider_name",
            "medication_name",
            "status",
            "has_care_plan",
            "created_at",
        ]


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders.
    
    Accepts flat patient/provider data and creates or retrieves entities.
    """
    
    # Patient fields
    patient_mrn = serializers.CharField(max_length=6)
    patient_first_name = serializers.CharField(max_length=100)
    patient_last_name = serializers.CharField(max_length=100)
    patient_date_of_birth = serializers.DateField(required=False, allow_null=True)
    patient_sex = serializers.ChoiceField(
        choices=["Male", "Female", "Other"],
        required=False,
        allow_null=True,
    )
    patient_weight_kg = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    patient_allergies = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Diagnosis fields
    primary_diagnosis_code = serializers.CharField(max_length=10)
    primary_diagnosis_description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )
    additional_diagnoses = serializers.ListField(
        child=serializers.CharField(max_length=10),
        required=False,
        default=list,
    )
    
    # Medication history
    medication_history = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
    )
    
    # Provider fields
    provider_npi = serializers.CharField(max_length=10)
    provider_name = serializers.CharField(max_length=200)
    
    # Order fields
    medication_name = serializers.CharField(max_length=200)
    patient_records = serializers.CharField()
    
    # Duplicate confirmation
    confirm_not_duplicate = serializers.BooleanField(default=False)
    
    def validate_patient_mrn(self, value):
        """Validate MRN format."""
        is_valid, error = MRNValidator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return MRNValidator.normalize(value)
    
    def validate_provider_npi(self, value):
        """Validate NPI with Luhn checksum."""
        is_valid, error = NPIValidator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
    
    def validate_primary_diagnosis_code(self, value):
        """Validate ICD-10 code."""
        is_valid, error = ICD10Validator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return ICD10Validator.normalize(value)
    
    def validate_additional_diagnoses(self, value):
        """Validate list of ICD-10 codes."""
        validated = []
        for code in value:
            is_valid, error = ICD10Validator.validate(code)
            if not is_valid:
                raise serializers.ValidationError(f"Invalid diagnosis '{code}': {error}")
            validated.append(ICD10Validator.normalize(code))
        return validated
    
    def validate_patient_first_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required")
        return " ".join(value.split())
    
    def validate_patient_last_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Last name is required")
        return " ".join(value.split())
    
    def validate_provider_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Provider name is required")
        return " ".join(value.split())
    
    def validate_medication_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Medication name is required")
        return value.strip()
    
    def validate_patient_records(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Patient records are required")
        return value.strip()


class OrderWithWarningsSerializer(serializers.Serializer):
    """Response serializer that includes warnings."""
    
    order = OrderSerializer(allow_null=True)
    warnings = serializers.ListField(child=serializers.CharField())
    patient_warnings = serializers.ListField(child=serializers.CharField(), default=list)
    provider_warnings = serializers.ListField(child=serializers.CharField(), default=list)
    is_potential_duplicate = serializers.BooleanField(default=False)
    requires_confirmation = serializers.BooleanField(default=False)
    duplicate_order_id = serializers.UUIDField(allow_null=True, required=False)
