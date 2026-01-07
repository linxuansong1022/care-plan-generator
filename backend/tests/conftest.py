"""
Pytest configuration and fixtures.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def sample_provider_data():
    """Sample provider data for testing."""
    return {
        "npi": "1234567893",
        "name": "Dr. Jane Smith",
    }


@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing."""
    return {
        "mrn": "123456",
        "first_name": "John",
        "last_name": "Doe",
        "primary_diagnosis_code": "G70.00",
        "primary_diagnosis_description": "Myasthenia gravis",
    }


@pytest.fixture
def sample_order_data():
    """Sample order creation data for testing."""
    return {
        "patient_mrn": "123456",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "primary_diagnosis_code": "G70.00",
        "primary_diagnosis_description": "Myasthenia gravis",
        "additional_diagnoses": [],
        "medication_history": [],
        "provider_npi": "1234567893",
        "provider_name": "Dr. Jane Smith",
        "medication_name": "IVIG",
        "patient_records": "Test clinical notes for care plan generation.",
    }
