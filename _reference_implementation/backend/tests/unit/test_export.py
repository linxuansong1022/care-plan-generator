"""
Unit tests for export functionality.
"""

import csv
import io

import pytest
from django.urls import reverse

from apps.care_plans.models import CarePlan
from apps.orders.models import Order
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.reports.services import ReportService


@pytest.fixture
def setup_test_data(db):
    """Create test data for export tests."""
    # Create provider
    provider = Provider.objects.create(
        npi="1234567890",
        name="Dr. Test Provider",
    )

    # Create patients
    patient1 = Patient.objects.create(
        mrn="100001",
        first_name="John",
        last_name="Doe",
        date_of_birth="1979-06-08",
        primary_diagnosis_code="G70.00",
    )

    patient2 = Patient.objects.create(
        mrn="100002",
        first_name="Jane",
        last_name="Smith",
        date_of_birth="1985-03-15",
        primary_diagnosis_code="G70.01",
    )

    # Create orders
    order1 = Order.objects.create(
        patient=patient1,
        provider=provider,
        medication_name="IVIG",
        patient_records="Clinical notes for John",
        status="completed",
    )

    order2 = Order.objects.create(
        patient=patient2,
        provider=provider,
        medication_name="Rituximab",
        patient_records="Clinical notes for Jane",
        status="pending",
    )

    # Create care plan for first order
    care_plan = CarePlan.objects.create(
        order=order1,
        content="## Problem list / Drug therapy problems (DTPs)\n- Test DTP\n\n## Goals (SMART)\n- Test goal",
    )

    return {
        "provider": provider,
        "patient1": patient1,
        "patient2": patient2,
        "order1": order1,
        "order2": order2,
        "care_plan": care_plan,
    }


@pytest.mark.django_db
class TestExportAPI:
    """Tests for the export API endpoint."""

    def test_export_returns_csv(self, api_client, setup_test_data):
        """Test that GET /api/v1/export/ returns a CSV file."""
        response = api_client.get("/api/v1/export/")

        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "attachment" in response["Content-Disposition"]
        assert ".csv" in response["Content-Disposition"]

    def test_export_csv_has_correct_headers(self, api_client, setup_test_data):
        """Test that CSV has all required headers."""
        response = api_client.get("/api/v1/export/")

        content = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames

        expected_headers = [
            "order_id",
            "order_date",
            "patient_mrn",
            "patient_first_name",
            "patient_last_name",
            "patient_date_of_birth",
            "provider_npi",
            "provider_name",
            "medication_name",
            "primary_diagnosis_code",
            "care_plan_status",
            "care_plan_content",
        ]

        assert headers == expected_headers

    def test_export_csv_contains_order_data(self, api_client, setup_test_data):
        """Test that CSV contains the order data."""
        response = api_client.get("/api/v1/export/")

        content = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        # Should have 2 orders
        assert len(rows) == 2

        # Check first order (completed with care plan)
        order1_row = next(r for r in rows if r["patient_mrn"] == "100001")
        assert order1_row["patient_first_name"] == "John"
        assert order1_row["patient_last_name"] == "Doe"
        assert order1_row["patient_date_of_birth"] == "1979-06-08"
        assert order1_row["provider_npi"] == "1234567890"
        assert order1_row["provider_name"] == "Dr. Test Provider"
        assert order1_row["medication_name"] == "IVIG"
        assert order1_row["primary_diagnosis_code"] == "G70.00"
        assert order1_row["care_plan_status"] == "completed"
        assert "Problem list" in order1_row["care_plan_content"]

        # Check second order (pending, no care plan)
        order2_row = next(r for r in rows if r["patient_mrn"] == "100002")
        assert order2_row["patient_first_name"] == "Jane"
        assert order2_row["patient_last_name"] == "Smith"
        assert order2_row["medication_name"] == "Rituximab"
        assert order2_row["care_plan_status"] == "pending"
        assert order2_row["care_plan_content"] == ""

    def test_export_empty_database(self, api_client, db):
        """Test export with no orders returns empty CSV with headers."""
        response = api_client.get("/api/v1/export/")

        assert response.status_code == 200

        content = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) == 0
        assert reader.fieldnames is not None


@pytest.mark.django_db
class TestReportService:
    """Tests for the ReportService."""

    def test_export_all_orders_with_care_plans(self, setup_test_data):
        """Test the service method directly."""
        service = ReportService()
        file_bytes, filename, content_type = service.export_all_orders_with_care_plans()

        assert content_type == "text/csv"
        assert filename.startswith("orders_care_plans_export_")
        assert filename.endswith(".csv")

        # Parse CSV
        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) == 2

    def test_care_plan_status_mapping(self, setup_test_data):
        """Test that care plan status is correctly mapped."""
        data = setup_test_data

        # Set order2 to failed status
        data["order2"].status = "failed"
        data["order2"].save()

        service = ReportService()
        file_bytes, _, _ = service.export_all_orders_with_care_plans()

        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        # Find the failed order
        failed_row = next(r for r in rows if r["patient_mrn"] == "100002")
        assert failed_row["care_plan_status"] == "failed"

    def test_care_plan_status_processing(self, setup_test_data):
        """Test that processing status is correctly mapped."""
        data = setup_test_data

        data["order2"].status = "processing"
        data["order2"].save()

        service = ReportService()
        file_bytes, _, _ = service.export_all_orders_with_care_plans()

        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        processing_row = next(r for r in rows if r["patient_mrn"] == "100002")
        assert processing_row["care_plan_status"] == "processing"

    def test_patient_without_dob(self, db):
        """Test export handles patient without date of birth."""
        provider = Provider.objects.create(npi="9876543210", name="Dr. No DOB")
        patient = Patient.objects.create(
            mrn="999999",
            first_name="No",
            last_name="DOB",
            date_of_birth=None,
            primary_diagnosis_code="Z00.00",
        )
        Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name="Test Med",
            patient_records="Notes",
            status="pending",
        )

        service = ReportService()
        file_bytes, _, _ = service.export_all_orders_with_care_plans()

        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["patient_date_of_birth"] == ""
