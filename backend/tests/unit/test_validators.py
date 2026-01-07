"""
Unit tests for validators.
"""

import pytest

from apps.core.validators import (
    ICD10Validator,
    MRNValidator,
    NPIValidator,
    validate_icd10,
    validate_mrn,
    validate_npi,
)
from django.core.exceptions import ValidationError


class TestNPIValidator:
    """Tests for NPI validation."""
    
    def test_valid_npi_passes(self):
        """Valid NPIs should pass validation."""
        # 1234567893 passes Luhn with 80840 prefix
        is_valid, error = NPIValidator.validate("1234567893")
        assert is_valid
        assert error is None
    
    def test_invalid_checksum_fails(self):
        """NPIs with invalid checksum should fail."""
        is_valid, error = NPIValidator.validate("1234567891")
        assert not is_valid
        assert "checksum" in error.lower()
    
    def test_wrong_length_fails(self):
        """NPIs with wrong length should fail."""
        # Too short
        is_valid, error = NPIValidator.validate("123456789")
        assert not is_valid
        assert "10 digits" in error
        
        # Too long
        is_valid, error = NPIValidator.validate("12345678901")
        assert not is_valid
        assert "10 digits" in error
    
    def test_non_numeric_fails(self):
        """NPIs with non-numeric characters should fail."""
        is_valid, error = NPIValidator.validate("123456789a")
        assert not is_valid
    
    def test_empty_fails(self):
        """Empty NPI should fail."""
        is_valid, error = NPIValidator.validate("")
        assert not is_valid
        assert "required" in error.lower()
    
    def test_none_fails(self):
        """None NPI should fail."""
        is_valid, error = NPIValidator.validate(None)
        assert not is_valid
    
    def test_django_validator_raises(self):
        """Django validator should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_npi("invalid")


class TestMRNValidator:
    """Tests for MRN validation."""
    
    def test_valid_mrn_passes(self):
        """Valid 6-digit MRNs should pass."""
        valid_mrns = ["123456", "000001", "999999"]
        
        for mrn in valid_mrns:
            is_valid, error = MRNValidator.validate(mrn)
            assert is_valid, f"Expected {mrn} to be valid"
    
    def test_wrong_length_fails(self):
        """MRNs with wrong length should fail."""
        is_valid, error = MRNValidator.validate("12345")
        assert not is_valid
        assert "6 digits" in error
        
        is_valid, error = MRNValidator.validate("1234567")
        assert not is_valid
    
    def test_non_numeric_fails(self):
        """MRNs with letters should fail."""
        is_valid, error = MRNValidator.validate("12345a")
        assert not is_valid
    
    def test_normalize_pads_zeros(self):
        """Normalize should pad with leading zeros."""
        assert MRNValidator.normalize("123") == "000123"
        assert MRNValidator.normalize("1") == "000001"
        assert MRNValidator.normalize("123456") == "123456"
    
    def test_django_validator_raises(self):
        """Django validator should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_mrn("12345")


class TestICD10Validator:
    """Tests for ICD-10 code validation."""
    
    @pytest.mark.parametrize("code", [
        "A00",        # Simple 3-char
        "A00.0",      # With decimal
        "A00.11",     # Longer decimal
        "G70.00",     # Myasthenia gravis
        "I10",        # Hypertension
        "E11.9",      # Type 2 diabetes
        "S72.001A",   # Fracture with 7th char
        "Z23",        # Immunization encounter
    ])
    def test_valid_codes_pass(self, code):
        """Valid ICD-10 codes should pass."""
        is_valid, error = ICD10Validator.validate(code)
        assert is_valid, f"Expected {code} to be valid, got: {error}"
    
    @pytest.mark.parametrize("code", [
        "U00",        # U is reserved
        "123",        # No letter
        "A0",         # Too short
        "A00.12345",  # Too long after decimal
        "AA0",        # Wrong format
        "",           # Empty
    ])
    def test_invalid_codes_fail(self, code):
        """Invalid ICD-10 codes should fail."""
        is_valid, error = ICD10Validator.validate(code)
        assert not is_valid, f"Expected {code} to be invalid"
    
    def test_case_insensitive(self):
        """Validation should be case-insensitive."""
        is_valid, _ = ICD10Validator.validate("g70.00")
        assert is_valid
    
    def test_normalize_uppercases(self):
        """Normalize should uppercase codes."""
        assert ICD10Validator.normalize("g70.00") == "G70.00"
    
    def test_django_validator_raises(self):
        """Django validator should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_icd10("invalid")
