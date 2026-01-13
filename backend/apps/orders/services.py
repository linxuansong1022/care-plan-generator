"""
Duplicate detection service.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from django.db.models import Q
from django.db.models.functions import Lower

from apps.patients.models import Patient
from apps.providers.models import Provider

from .models import Order


@dataclass
class Warning:
    """Warning message with metadata."""
    code: str
    message: str
    action_required: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class DuplicateCheckResult:
    """Result of a duplicate check."""
    is_duplicate: bool = False
    is_potential_duplicate: bool = False
    should_block: bool = False
    existing_record: Optional[any] = None
    warnings: List[Warning] = field(default_factory=list)


class ProviderDuplicateDetector:
    """Detects duplicate providers based on NPI and name similarity."""
    
    @staticmethod
    def check(npi: str, name: str) -> DuplicateCheckResult:
        """
        Check for provider duplicates.
        
        Rules:
        - Same NPI, same name → use existing (OK)
        - Same NPI, different name → BLOCK (data inconsistency)
        - Similar name, different NPI → WARN (potential duplicate)
        """
        warnings = []
        
        # Check exact NPI match
        try:
            existing = Provider.objects.get(npi=npi)
            
            # Same NPI exists - check name
            if existing.name.lower().strip() == name.lower().strip():
                # Same provider, OK to reuse
                warnings.append(Warning(
                    code="PROVIDER_EXISTS",
                    message=f"Provider with NPI {npi} already exists. Using existing record.",
                    action_required=False,
                ))
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_record=existing,
                    warnings=warnings,
                )
            else:
                # Same NPI, different name - BLOCK
                warnings.append(Warning(
                    code="PROVIDER_NPI_CONFLICT",
                    message=f"NPI {npi} is already registered to '{existing.name}'. "
                            f"Cannot register same NPI to '{name}'. Please verify the NPI.",
                    action_required=True,
                    data={"existing_name": existing.name},
                ))
                return DuplicateCheckResult(
                    is_duplicate=True,
                    should_block=True,
                    existing_record=existing,
                    warnings=warnings,
                )
        
        except Provider.DoesNotExist:
            pass
        
        # Check for similar names with different NPIs
        # Simple case-insensitive contains check
        similar = Provider.objects.annotate(
            lower_name=Lower("name")
        ).filter(
            lower_name__icontains=name.lower().split()[0]  # Match first name/word
        ).exclude(npi=npi)[:5]
        
        if similar.exists():
            warnings.append(Warning(
                code="PROVIDER_SIMILAR_NAME",
                message=f"Found {similar.count()} provider(s) with similar names. "
                        f"Please verify this is a new provider.",
                action_required=False,
                data={
                    "similar_providers": [
                        {"npi": p.npi, "name": p.name} for p in similar
                    ]
                },
            ))
            return DuplicateCheckResult(
                is_potential_duplicate=True,
                warnings=warnings,
            )
        
        return DuplicateCheckResult()


class PatientDuplicateDetector:
    """Detects duplicate patients based on MRN and demographics."""
    
    @staticmethod
    def check(mrn: str, first_name: str, last_name: str, date_of_birth=None) -> DuplicateCheckResult:
        """
        Check for patient duplicates.
        
        Rules:
        - Same MRN → use existing (may warn if name differs)
        - Same name + DOB, different MRN → WARN (potential duplicate)
        """
        warnings = []
        
        # Check exact MRN match
        try:
            existing = Patient.objects.get(mrn=mrn)
            
            # MRN found - check if names match
            names_match = (
                existing.first_name.lower().strip() == first_name.lower().strip() and
                existing.last_name.lower().strip() == last_name.lower().strip()
            )
            
            if names_match:
                warnings.append(Warning(
                    code="PATIENT_EXISTS",
                    message=f"Patient with MRN {mrn} already exists. Using existing record.",
                    action_required=False,
                ))
            else:
                warnings.append(Warning(
                    code="PATIENT_NAME_MISMATCH",
                    message=f"Patient MRN {mrn} exists with name "
                            f"'{existing.first_name} {existing.last_name}', "
                            f"but input name is '{first_name} {last_name}'. Please verify.",
                    action_required=True,
                    data={
                        "existing_name": f"{existing.first_name} {existing.last_name}"
                    },
                ))
            
            return DuplicateCheckResult(
                is_duplicate=True,
                existing_record=existing,
                warnings=warnings,
            )
        
        except Patient.DoesNotExist:
            pass
        
        # Check for same name + DOB with different MRN
        if date_of_birth:
            potential = Patient.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=date_of_birth,
            ).exclude(mrn=mrn).first()
            
            if potential:
                warnings.append(Warning(
                    code="PATIENT_POSSIBLE_DUPLICATE",
                    message=f"A patient with the same name and date of birth exists "
                            f"with MRN {potential.mrn}. Please verify this is a different patient.",
                    action_required=True,
                    data={
                        "existing_mrn": potential.mrn,
                        "existing_name": f"{potential.first_name} {potential.last_name}",
                    },
                ))
                return DuplicateCheckResult(
                    is_potential_duplicate=True,
                    warnings=warnings,
                )
        
        # Check for exact name match (without DOB)
        name_matches = Patient.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).exclude(mrn=mrn)[:5]
        
        if name_matches.exists():
            warnings.append(Warning(
                code="PATIENT_SIMILAR_NAME",
                message=f"Found {name_matches.count()} patient(s) with the same name. "
                        f"Please verify this is a new patient.",
                action_required=False,
                data={
                    "similar_patients": [
                        {"mrn": p.mrn, "dob": str(p.date_of_birth) if p.date_of_birth else None}
                        for p in name_matches
                    ]
                },
            ))
            return DuplicateCheckResult(
                is_potential_duplicate=True,
                warnings=warnings,
            )
        
        return DuplicateCheckResult()


class OrderDuplicateDetector:
    """Detects duplicate orders based on patient, medication, and date."""

    @classmethod
    def check(
        cls,
        patient_id: str,
        provider_id: str,
        medication_name: str,
        confirm_not_duplicate: bool = False,
    ) -> DuplicateCheckResult:
        """
        Check for order duplicates.

        Rules:
        - Same patient + same medication + same date → ERROR (block)
        - Same patient + same medication + different date → WARNING (can confirm)
        """
        # Skip check for new patients (not yet in DB)
        if patient_id.startswith("new:"):
            return DuplicateCheckResult()

        warnings = []
        today = datetime.now().date()

        # Check: Same patient + same medication (any date)
        existing_order = Order.objects.filter(
            patient_id=patient_id,
            medication_name__iexact=medication_name.strip(),
        ).order_by("-created_at").first()

        if not existing_order:
            return DuplicateCheckResult()

        # Check if same day
        order_date = existing_order.created_at.date()
        is_same_day = order_date == today

        if is_same_day:
            # Same day → BLOCK
            warnings.append(Warning(
                code="ORDER_DUPLICATE_SAME_DAY",
                message="An order for the same patient and medication was already created today. "
                        "Cannot create duplicate order on the same day.",
                action_required=True,
                data={
                    "existing_order_id": str(existing_order.id),
                    "existing_order_date": existing_order.created_at.isoformat(),
                    "existing_order_status": existing_order.status,
                },
            ))
            return DuplicateCheckResult(
                is_duplicate=True,
                should_block=True,
                existing_record=existing_order,
                warnings=warnings,
            )
        else:
            # Different day → WARNING (can confirm)
            if confirm_not_duplicate:
                warnings.append(Warning(
                    code="ORDER_DUPLICATE_CONFIRMED",
                    message="User confirmed this order is not a duplicate.",
                    action_required=False,
                ))
                return DuplicateCheckResult(
                    is_potential_duplicate=True,
                    warnings=warnings,
                )

            days_ago = (today - order_date).days
            warnings.append(Warning(
                code="ORDER_POSSIBLE_DUPLICATE",
                message=f"A similar order was created {days_ago} day(s) ago "
                        f"for the same patient and medication. "
                        f"Please confirm this is not a duplicate.",
                action_required=True,
                data={
                    "existing_order_id": str(existing_order.id),
                    "existing_order_date": existing_order.created_at.isoformat(),
                    "existing_order_status": existing_order.status,
                },
            ))
            return DuplicateCheckResult(
                is_potential_duplicate=True,
                existing_record=existing_order,
                warnings=warnings,
            )


@dataclass
class FullDuplicateCheckResult:
    """Combined result of all duplicate checks."""
    
    provider_result: DuplicateCheckResult
    patient_result: DuplicateCheckResult
    order_result: Optional[DuplicateCheckResult] = None
    
    @property
    def has_blocking_issues(self) -> bool:
        return self.provider_result.should_block or self.patient_result.should_block
    
    @property
    def requires_confirmation(self) -> bool:
        def needs_confirm(result: DuplicateCheckResult) -> bool:
            return (
                result.is_potential_duplicate and
                any(w.action_required for w in result.warnings)
            )
        
        return (
            needs_confirm(self.provider_result) or
            needs_confirm(self.patient_result) or
            (self.order_result and needs_confirm(self.order_result))
        )
    
    @property
    def all_warnings(self) -> List[Warning]:
        warnings = []
        warnings.extend(self.provider_result.warnings)
        warnings.extend(self.patient_result.warnings)
        if self.order_result:
            warnings.extend(self.order_result.warnings)
        return warnings
    
    @property
    def existing_provider(self) -> Optional[Provider]:
        if self.provider_result.is_duplicate and not self.provider_result.should_block:
            return self.provider_result.existing_record
        return None
    
    @property
    def existing_patient(self) -> Optional[Patient]:
        if self.patient_result.is_duplicate:
            return self.patient_result.existing_record
        return None


class DuplicateDetectionService:
    """Unified service for all duplicate detection."""
    
    @staticmethod
    def check_all(
        provider_npi: str,
        provider_name: str,
        patient_mrn: str,
        patient_first_name: str,
        patient_last_name: str,
        patient_dob=None,
        medication_name: str = None,
        confirm_not_duplicate: bool = False,
    ) -> FullDuplicateCheckResult:
        """
        Perform all duplicate checks for a new order.
        """
        # Check provider
        provider_result = ProviderDuplicateDetector.check(provider_npi, provider_name)
        
        # Check patient
        patient_result = PatientDuplicateDetector.check(
            patient_mrn, patient_first_name, patient_last_name, patient_dob
        )
        
        # Check order (if we have patient and provider)
        order_result = None
        if medication_name and not provider_result.should_block:
            # Get IDs
            patient_id = (
                str(patient_result.existing_record.id)
                if patient_result.existing_record
                else f"new:{patient_mrn}"
            )
            provider_id = (
                str(provider_result.existing_record.id)
                if provider_result.existing_record
                else f"new:{provider_npi}"
            )
            
            order_result = OrderDuplicateDetector.check(
                patient_id, provider_id, medication_name, confirm_not_duplicate
            )
        
        return FullDuplicateCheckResult(
            provider_result=provider_result,
            patient_result=patient_result,
            order_result=order_result,
        )
