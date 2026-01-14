"""
Unit tests for duplicate detection service.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.services import (
    DuplicateCheckResult,
    OrderDuplicateDetector,
    PatientDuplicateDetector,
    ProviderDuplicateDetector,
)


class TestOrderDuplicateDetector:
    """Tests for Order duplicate detection."""

    def test_same_patient_same_medication_same_day_blocks(self):
        """Same patient + same medication + same day should BLOCK."""
        mock_order = MagicMock()
        mock_order.id = "existing-order-id"
        mock_order.created_at = datetime.now()  # Same day
        mock_order.status = "completed"

        with patch("apps.orders.services.Order.objects") as mock_objects:
            mock_objects.filter.return_value.order_by.return_value.first.return_value = mock_order

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="IVIG",
            )

            assert result.should_block is True
            assert result.is_duplicate is True
            assert result.warnings[0].code == "ORDER_DUPLICATE_SAME_DAY"

    def test_same_patient_same_medication_different_day_warns(self):
        """Same patient + same medication + different day should WARN."""
        mock_order = MagicMock()
        mock_order.id = "existing-order-id"
        mock_order.created_at = datetime.now() - timedelta(days=5)  # 5 days ago
        mock_order.status = "completed"

        with patch("apps.orders.services.Order.objects") as mock_objects:
            mock_objects.filter.return_value.order_by.return_value.first.return_value = mock_order

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="IVIG",
            )

            assert result.should_block is False
            assert result.is_potential_duplicate is True
            assert result.warnings[0].code == "ORDER_POSSIBLE_DUPLICATE"

    def test_same_patient_same_medication_different_day_with_confirmation_allows(self):
        """Same patient + same medication + different day with confirmation should ALLOW."""
        mock_order = MagicMock()
        mock_order.id = "existing-order-id"
        mock_order.created_at = datetime.now() - timedelta(days=5)
        mock_order.status = "completed"

        with patch("apps.orders.services.Order.objects") as mock_objects:
            mock_objects.filter.return_value.order_by.return_value.first.return_value = mock_order

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="IVIG",
                confirm_not_duplicate=True,
            )

            assert result.should_block is False
            assert result.is_potential_duplicate is True
            assert result.warnings[0].code == "ORDER_DUPLICATE_CONFIRMED"

    def test_no_duplicate_returns_empty_result(self):
        """No duplicate orders should return empty result."""
        with patch("apps.orders.services.Order.objects") as mock_objects:
            mock_objects.filter.return_value.order_by.return_value.first.return_value = None

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="IVIG",
            )

            assert result.should_block is False
            assert result.is_duplicate is False
            assert result.is_potential_duplicate is False
            assert len(result.warnings) == 0

    def test_new_patient_skips_check(self):
        """New patients (not yet in DB) should skip duplicate check."""
        result = OrderDuplicateDetector.check(
            patient_id="new:123456",  # New patient prefix
            provider_id="provider-123",
            medication_name="IVIG",
        )

        assert result.should_block is False
        assert result.is_duplicate is False


class TestProviderDuplicateDetector:
    """Tests for Provider duplicate detection."""

    def test_same_npi_same_name_reuses_existing(self):
        """Same NPI + same name should reuse existing provider."""
        mock_provider = MagicMock()
        mock_provider.npi = "1234567893"
        mock_provider.name = "Dr. Jane Smith"

        with patch("apps.orders.services.Provider.objects") as mock_objects:
            mock_objects.get.return_value = mock_provider

            result = ProviderDuplicateDetector.check(
                npi="1234567893",
                name="Dr. Jane Smith",
            )

            assert result.is_duplicate is True
            assert result.should_block is False
            assert result.existing_record == mock_provider
            assert result.warnings[0].code == "PROVIDER_EXISTS"

    def test_same_npi_different_name_blocks(self):
        """Same NPI + different name should BLOCK."""
        mock_provider = MagicMock()
        mock_provider.npi = "1234567893"
        mock_provider.name = "Dr. Jane Smith"

        with patch("apps.orders.services.Provider.objects") as mock_objects:
            mock_objects.get.return_value = mock_provider

            result = ProviderDuplicateDetector.check(
                npi="1234567893",
                name="Dr. John Doe",  # Different name
            )

            assert result.is_duplicate is True
            assert result.should_block is True
            assert result.warnings[0].code == "PROVIDER_NPI_CONFLICT"


class TestPatientDuplicateDetector:
    """Tests for Patient duplicate detection."""

    def test_same_mrn_same_name_reuses_existing(self):
        """Same MRN + same name should reuse existing patient."""
        mock_patient = MagicMock()
        mock_patient.mrn = "123456"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            mock_objects.get.return_value = mock_patient

            result = PatientDuplicateDetector.check(
                mrn="123456",
                first_name="John",
                last_name="Doe",
            )

            assert result.is_duplicate is True
            assert result.existing_record == mock_patient
            assert result.warnings[0].code == "PATIENT_EXISTS"

    def test_same_mrn_different_name_warns(self):
        """Same MRN + different name should warn."""
        mock_patient = MagicMock()
        mock_patient.mrn = "123456"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = None

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            mock_objects.get.return_value = mock_patient

            result = PatientDuplicateDetector.check(
                mrn="123456",
                first_name="Jane",  # Different name
                last_name="Doe",
            )

            assert result.is_duplicate is True
            assert result.warnings[0].code == "PATIENT_NAME_MISMATCH"
            assert result.warnings[0].action_required is True

    def test_same_mrn_different_dob_warns(self):
        """Same MRN + different DOB should warn."""
        from datetime import date

        mock_patient = MagicMock()
        mock_patient.mrn = "123456"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = date(1990, 1, 15)

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            mock_objects.get.return_value = mock_patient

            result = PatientDuplicateDetector.check(
                mrn="123456",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1985, 6, 20),  # Different DOB
            )

            assert result.is_duplicate is True
            assert result.warnings[0].code == "PATIENT_DOB_MISMATCH"
            assert result.warnings[0].action_required is True

    def test_same_mrn_different_name_and_dob_warns(self):
        """Same MRN + different name AND DOB should warn with combined code."""
        from datetime import date

        mock_patient = MagicMock()
        mock_patient.mrn = "123456"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = date(1990, 1, 15)

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            mock_objects.get.return_value = mock_patient

            result = PatientDuplicateDetector.check(
                mrn="123456",
                first_name="Jane",  # Different name
                last_name="Smith",  # Different name
                date_of_birth=date(1985, 6, 20),  # Different DOB
            )

            assert result.is_duplicate is True
            assert result.warnings[0].code == "PATIENT_DATA_MISMATCH"
            assert result.warnings[0].action_required is True

    def test_same_name_dob_different_mrn_warns(self):
        """Same fn+ln+dob but different MRN should warn (potential duplicate)."""
        from datetime import date
        from apps.patients.models import Patient

        mock_existing_patient = MagicMock()
        mock_existing_patient.mrn = "999999"
        mock_existing_patient.first_name = "John"
        mock_existing_patient.last_name = "Doe"
        mock_existing_patient.date_of_birth = date(1990, 1, 15)

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            # MRN not found
            mock_objects.get.side_effect = Patient.DoesNotExist
            # But same name+dob exists with different MRN
            mock_objects.filter.return_value.exclude.return_value.first.return_value = mock_existing_patient

            result = PatientDuplicateDetector.check(
                mrn="123456",  # Different MRN
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1990, 1, 15),  # Same DOB
            )

            assert result.is_potential_duplicate is True
            assert result.warnings[0].code == "PATIENT_POSSIBLE_DUPLICATE"
            assert result.warnings[0].action_required is True

    def test_no_match_creates_new_patient(self):
        """No matching MRN or name+dob should allow creating new patient."""
        from datetime import date
        from apps.patients.models import Patient

        with patch("apps.orders.services.Patient.objects") as mock_objects:
            # MRN not found
            mock_objects.get.side_effect = Patient.DoesNotExist

            # Mock for name+dob check (first filter call)
            mock_name_dob_filter = MagicMock()
            mock_name_dob_filter.exclude.return_value.first.return_value = None

            # Mock for similar name check (second filter call)
            mock_similar_name_filter = MagicMock()
            mock_similar_name_filter.exclude.return_value.__getitem__.return_value.exists.return_value = False

            # Return different mocks for each filter call
            mock_objects.filter.side_effect = [mock_name_dob_filter, mock_similar_name_filter]

            result = PatientDuplicateDetector.check(
                mrn="123456",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1990, 1, 15),
            )

            assert result.is_duplicate is False
            assert result.is_potential_duplicate is False
            assert result.should_block is False
            assert len(result.warnings) == 0


class TestCarePlanPerMedication:
    """Tests for care plan per medication design."""

    def test_same_medication_same_patient_same_day_blocks(self):
        """Same medication for same patient on same day should block."""
        mock_order = MagicMock()
        mock_order.id = "existing-order"
        mock_order.created_at = datetime.now()
        mock_order.status = "completed"

        with patch("apps.orders.services.Order.objects") as mock_objects:
            mock_objects.filter.return_value.order_by.return_value.first.return_value = mock_order

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="IVIG",
            )

            assert result.should_block is True

    def test_different_medication_same_patient_same_day_allows(self):
        """Different medication for same patient on same day should allow."""
        with patch("apps.orders.services.Order.objects") as mock_objects:
            # No existing order with this medication
            mock_objects.filter.return_value.order_by.return_value.first.return_value = None

            result = OrderDuplicateDetector.check(
                patient_id="patient-123",
                provider_id="provider-123",
                medication_name="Rituximab",
            )

            assert result.should_block is False
            assert result.is_duplicate is False
