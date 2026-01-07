"""
Patient serializers.
"""

from datetime import date

from rest_framework import serializers

from apps.core.validators import ICD10Validator, MRNValidator

from .models import MedicationHistory, Patient, PatientDiagnosis


class PatientDiagnosisSerializer(serializers.ModelSerializer):
    """Serializer for patient diagnoses."""
    
    class Meta:
        model = PatientDiagnosis
        fields = ["id", "icd10_code", "description", "is_primary", "created_at"]
        read_only_fields = ["id", "created_at"]
    
    def validate_icd10_code(self, value):
        is_valid, error = ICD10Validator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return ICD10Validator.normalize(value)


class MedicationHistorySerializer(serializers.ModelSerializer):
    """Serializer for medication history."""
    
    class Meta:
        model = MedicationHistory
        fields = ["id", "medication_name", "dosage", "frequency", "is_current", "created_at"]
        read_only_fields = ["id", "created_at"]


class PatientSerializer(serializers.ModelSerializer):
    """Full serializer for Patient model."""
    
    diagnoses = PatientDiagnosisSerializer(many=True, read_only=True)
    medication_history = MedicationHistorySerializer(many=True, read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            "id",
            "mrn",
            "first_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "sex",
            "weight_kg",
            "allergies",
            "primary_diagnosis_code",
            "primary_diagnosis_description",
            "diagnoses",
            "medication_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def validate_mrn(self, value):
        """Validate MRN format."""
        is_valid, error = MRNValidator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return MRNValidator.normalize(value)
    
    def validate_primary_diagnosis_code(self, value):
        """Validate ICD-10 code."""
        is_valid, error = ICD10Validator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return ICD10Validator.normalize(value)
    
    def validate_date_of_birth(self, value):
        """Ensure DOB is not in the future."""
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        return value
    
    def validate_weight_kg(self, value):
        """Ensure weight is reasonable."""
        if value is not None and (value <= 0 or value > 500):
            raise serializers.ValidationError("Weight must be between 0 and 500 kg")
        return value
    
    def validate_first_name(self, value):
        """Clean name."""
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required")
        return " ".join(value.split())
    
    def validate_last_name(self, value):
        """Clean name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Last name is required")
        return " ".join(value.split())


class PatientCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating patients (used in order creation).
    Includes nested additional diagnoses and medication history.
    """
    
    additional_diagnoses = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of additional ICD-10 codes",
    )
    
    medication_history = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of medications",
    )
    
    class Meta:
        model = Patient
        fields = [
            "mrn",
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "weight_kg",
            "allergies",
            "primary_diagnosis_code",
            "primary_diagnosis_description",
            "additional_diagnoses",
            "medication_history",
        ]
    
    def validate_mrn(self, value):
        is_valid, error = MRNValidator.validate(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return MRNValidator.normalize(value)
    
    def validate_primary_diagnosis_code(self, value):
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
                raise serializers.ValidationError(f"Invalid diagnosis code '{code}': {error}")
            validated.append(ICD10Validator.normalize(code))
        return validated
    
    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        return value


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing patients."""
    
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = ["id", "mrn", "first_name", "last_name", "full_name", "primary_diagnosis_code"]
