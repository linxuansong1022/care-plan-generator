"""
Integration tests for Order API.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.orders.models import Order
from apps.patients.models import Patient
from apps.providers.models import Provider


@pytest.mark.django_db
class TestOrderAPI:
    """Integration tests for Order API."""
    
    def test_create_order_success(self, api_client, sample_order_data):
        """Test successful order creation."""
        url = reverse("order-list")
        response = api_client.post(url, sample_order_data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["order"] is not None
        assert data["order"]["status"] == "pending"
        
        # Verify database records
        assert Order.objects.count() == 1
        assert Patient.objects.count() == 1
        assert Provider.objects.count() == 1
    
    def test_create_order_invalid_npi_fails(self, api_client, sample_order_data):
        """Test that invalid NPI returns validation error."""
        sample_order_data["provider_npi"] = "1234567890"  # Invalid checksum
        
        url = reverse("order-list")
        response = api_client.post(url, sample_order_data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_order_invalid_mrn_fails(self, api_client, sample_order_data):
        """Test that invalid MRN returns validation error."""
        sample_order_data["patient_mrn"] = "12345"  # Only 5 digits
        
        url = reverse("order-list")
        response = api_client.post(url, sample_order_data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_order_invalid_icd10_fails(self, api_client, sample_order_data):
        """Test that invalid ICD-10 returns validation error."""
        sample_order_data["primary_diagnosis_code"] = "INVALID"
        
        url = reverse("order-list")
        response = api_client.post(url, sample_order_data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_duplicate_provider_npi_conflict(self, api_client, sample_order_data):
        """Test that same NPI with different name returns conflict."""
        url = reverse("order-list")
        
        # First order creates provider
        response = api_client.post(url, sample_order_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        # Second order with same NPI but different name
        sample_order_data["patient_mrn"] = "234567"  # Different patient
        sample_order_data["provider_name"] = "Dr. John Jones"  # Different name, same NPI
        
        response = api_client.post(url, sample_order_data, format="json")
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_reuse_existing_patient(self, api_client, sample_order_data):
        """Test that existing patient is reused."""
        url = reverse("order-list")
        
        # First order
        response = api_client.post(url, sample_order_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        # Second order for same patient
        sample_order_data["medication_name"] = "Different Medication"
        sample_order_data["confirm_not_duplicate"] = True
        
        response = api_client.post(url, sample_order_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        # Should still only have 1 patient
        assert Patient.objects.count() == 1
        assert Order.objects.count() == 2
    
    def test_get_order_list(self, api_client, sample_order_data):
        """Test listing orders."""
        url = reverse("order-list")
        
        # Create an order first
        api_client.post(url, sample_order_data, format="json")
        
        # List orders
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 1
    
    def test_get_order_detail(self, api_client, sample_order_data):
        """Test retrieving order by ID."""
        url = reverse("order-list")
        
        # Create order
        create_response = api_client.post(url, sample_order_data, format="json")
        order_id = create_response.json()["order"]["id"]
        
        # Get order detail
        detail_url = reverse("order-detail", kwargs={"pk": order_id})
        response = api_client.get(detail_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == order_id


@pytest.mark.django_db
class TestProviderAPI:
    """Integration tests for Provider API."""
    
    def test_create_provider(self, api_client, sample_provider_data):
        """Test creating a provider directly."""
        url = reverse("provider-list")
        response = api_client.post(url, sample_provider_data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Provider.objects.count() == 1
    
    def test_get_provider_by_npi(self, api_client, sample_provider_data):
        """Test getting provider by NPI."""
        # Create provider
        url = reverse("provider-list")
        api_client.post(url, sample_provider_data, format="json")
        
        # Get by NPI
        npi_url = f"/api/v1/providers/by-npi/{sample_provider_data['npi']}/"
        response = api_client.get(npi_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["npi"] == sample_provider_data["npi"]


@pytest.mark.django_db
class TestPatientAPI:
    """Integration tests for Patient API."""
    
    def test_create_patient(self, api_client, sample_patient_data):
        """Test creating a patient directly."""
        url = reverse("patient-list")
        response = api_client.post(url, sample_patient_data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Patient.objects.count() == 1
    
    def test_get_patient_by_mrn(self, api_client, sample_patient_data):
        """Test getting patient by MRN."""
        # Create patient
        url = reverse("patient-list")
        api_client.post(url, sample_patient_data, format="json")
        
        # Get by MRN
        mrn_url = f"/api/v1/patients/by-mrn/{sample_patient_data['mrn']}/"
        response = api_client.get(mrn_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["mrn"] == sample_patient_data["mrn"]
