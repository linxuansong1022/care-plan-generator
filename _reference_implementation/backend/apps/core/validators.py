"""
Validators for healthcare identifiers.
- NPI: National Provider Identifier (10 digits with Luhn checksum)
- MRN: Medical Record Number (6 digits)
- ICD-10: International Classification of Diseases codes
"""

import re
from typing import Tuple, Optional

from django.core.exceptions import ValidationError


class NPIValidator:
    """
    NPI (National Provider Identifier) Validator.
    
    NPIs are 10-digit numbers.
    """
    
    NPI_PATTERN = re.compile(r"^\d{10}$")
    
    @classmethod
    def validate(cls, npi: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an NPI number.
        
        Args:
            npi: The NPI string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not npi:
            return False, "NPI is required"
        
        npi = str(npi).strip()
        
        if not cls.NPI_PATTERN.match(npi):
            return False, "NPI must be exactly 10 digits"
        
        return True, None


def validate_npi(value: str) -> str:
    """Django validator function for NPI."""
    is_valid, error = NPIValidator.validate(value)
    if not is_valid:
        raise ValidationError(error)
    return value


class MRNValidator:
    """
    MRN (Medical Record Number) Validator.
    For this system, MRNs are exactly 6 digits.
    """
    
    MRN_PATTERN = re.compile(r"^\d{6}$")
    
    @classmethod
    def validate(cls, mrn: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an MRN.
        
        Args:
            mrn: The MRN string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not mrn:
            return False, "MRN is required"
        
        mrn = str(mrn).strip()
        
        if not cls.MRN_PATTERN.match(mrn):
            return False, "MRN must be exactly 6 digits"
        
        return True, None
    
    @classmethod
    def normalize(cls, mrn: str) -> str:
        """Normalize MRN (pad with leading zeros if needed)."""
        if mrn and mrn.isdigit():
            return mrn.zfill(6)
        return mrn


def validate_mrn(value: str) -> str:
    """Django validator function for MRN."""
    is_valid, error = MRNValidator.validate(value)
    if not is_valid:
        raise ValidationError(error)
    return value


class ICD10Validator:
    """
    ICD-10-CM Code Validator.
    
    ICD-10-CM codes follow the pattern:
    - First character: Letter (A-Z, excluding U)
    - Characters 2-3: Digits
    - Character 4 (optional): Decimal point
    - Characters 5-7 (optional): Alphanumeric
    
    Examples: A00, A00.0, A00.11, S72.001A, Z23
    """
    
    ICD10_PATTERN = re.compile(
        r"^[A-TV-Z]"      # First letter (A-T, V-Z; U is reserved)
        r"\d{2}"          # Two digits
        r"(\.\w{1,4})?$"  # Optional: decimal + 1-4 alphanumeric
    , re.IGNORECASE)
    
    VALID_CATEGORIES = {
        "A", "B",  # Infectious diseases
        "C", "D",  # Neoplasms, blood diseases
        "E",       # Endocrine, nutritional
        "F",       # Mental disorders
        "G",       # Nervous system
        "H",       # Eye, ear
        "I",       # Circulatory
        "J",       # Respiratory
        "K",       # Digestive
        "L",       # Skin
        "M",       # Musculoskeletal
        "N",       # Genitourinary
        "O",       # Pregnancy
        "P",       # Perinatal
        "Q",       # Congenital
        "R",       # Symptoms, signs
        "S", "T",  # Injury, poisoning
        "V", "W", "X", "Y",  # External causes
        "Z",       # Health status factors
    }
    
    @classmethod
    def validate(cls, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an ICD-10-CM code format.
        
        Note: This validates FORMAT only, not whether the code exists.
        
        Args:
            code: The ICD-10 code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code:
            return False, "ICD-10 code is required"
        
        code = code.strip().upper()
        
        if not cls.ICD10_PATTERN.match(code):
            return False, f"Invalid ICD-10 code format: {code}. Expected format like 'A00' or 'A00.0'"
        
        if code[0] not in cls.VALID_CATEGORIES:
            return False, f"Invalid ICD-10 category: {code[0]}"
        
        return True, None
    
    @classmethod
    def normalize(cls, code: str) -> str:
        """Normalize ICD-10 code to standard format."""
        if not code:
            return code
        return code.strip().upper()


def validate_icd10(value: str) -> str:
    """Django validator function for ICD-10 code."""
    is_valid, error = ICD10Validator.validate(value)
    if not is_valid:
        raise ValidationError(error)
    return ICD10Validator.normalize(value)