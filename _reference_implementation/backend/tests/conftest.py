"""
Pytest configuration and fixtures.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def mock_llm_service():
    """Mock LLM service to skip actual API calls during tests."""
    mock_response = MagicMock()
    mock_response.content = "Mock care plan content for testing."
    mock_response.model = "mock-model"
    mock_response.prompt_tokens = 100
    mock_response.completion_tokens = 50
    mock_response.total_tokens = 150
    mock_response.generation_time_ms = 100

    with patch("apps.care_plans.tasks.get_llm_service") as mock_get_llm:
        mock_service = MagicMock()
        mock_service.generate.return_value = mock_response
        mock_get_llm.return_value = mock_service
        yield mock_service


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
