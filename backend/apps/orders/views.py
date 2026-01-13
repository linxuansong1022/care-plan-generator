"""
Order views.
"""

import logging

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import DuplicateBlockedException, DuplicateWarningException
from apps.patients.models import MedicationHistory, Patient, PatientDiagnosis
from apps.providers.models import Provider

from .models import Order
from .serializers import (
    OrderCreateSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderWithWarningsSerializer,
)
from .services import DuplicateDetectionService, OrderDuplicateDetector

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order model.
    
    list: List all orders
    retrieve: Get a single order
    create: Create a new order with duplicate detection
    """
    
    queryset = Order.objects.select_related("patient", "provider").all()
    serializer_class = OrderSerializer
    
    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by provider NPI
        provider_npi = self.request.query_params.get("provider_npi")
        if provider_npi:
            queryset = queryset.filter(provider__npi=provider_npi)
        
        # Filter by patient MRN
        patient_mrn = self.request.query_params.get("patient_mrn")
        if patient_mrn:
            queryset = queryset.filter(patient__mrn=patient_mrn)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new order with duplicate detection.
        
        Flow:
        1. Validate input data
        2. Check for duplicates (provider, patient, order)
        3. If blocking duplicate → return 409 error
        4. If potential duplicate and not confirmed → return 409 with warnings
        5. Create/get provider and patient
        6. Create order
        7. Queue care plan generation
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Run duplicate detection
        dup_result = DuplicateDetectionService.check_all(
            provider_npi=data["provider_npi"],
            provider_name=data["provider_name"],
            patient_mrn=data["patient_mrn"],
            patient_first_name=data["patient_first_name"],
            patient_last_name=data["patient_last_name"],
            patient_dob=data.get("patient_date_of_birth"),
            medication_name=data["medication_name"],
            confirm_not_duplicate=data.get("confirm_not_duplicate", False),
        )
        
        # Check for blocking issues
        if dup_result.has_blocking_issues:
            raise DuplicateBlockedException(
                detail=[w.message for w in dup_result.all_warnings if w.action_required]
            )
        
        # Check if confirmation required
        if dup_result.requires_confirmation and not data.get("confirm_not_duplicate"):
            # Return warnings without creating order
            return Response(
                {
                    "order": None,
                    "warnings": [w.message for w in dup_result.all_warnings],
                    "patient_warnings": [
                        w.message for w in dup_result.patient_result.warnings if w.action_required
                    ],
                    "provider_warnings": [
                        w.message for w in dup_result.provider_result.warnings if w.action_required
                    ],
                    "is_potential_duplicate": True,
                    "requires_confirmation": True,
                    "duplicate_order_id": (
                        str(dup_result.order_result.existing_record.id)
                        if dup_result.order_result and dup_result.order_result.existing_record
                        else None
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        
        # Create order with all entities
        try:
            order = self._create_order(data, dup_result)
            
            # Queue care plan generation
            self._queue_care_plan_generation(order)
            
            # Prepare response
            response_serializer = OrderSerializer(order)
            
            # Collect all warnings for response
            patient_warnings = [
                w.message for w in dup_result.patient_result.warnings
            ] if dup_result.patient_result else []
            
            provider_warnings = [
                w.message for w in dup_result.provider_result.warnings
            ] if dup_result.provider_result else []
            
            return Response(
                {
                    "order": response_serializer.data,
                    "warnings": [w.message for w in dup_result.all_warnings],
                    "patient_warnings": patient_warnings,
                    "provider_warnings": provider_warnings,
                    "is_potential_duplicate": False,
                    "requires_confirmation": False,
                },
                status=status.HTTP_201_CREATED,
            )
        
        except Exception as e:
            logger.exception("Error creating order")
            raise
    
    @transaction.atomic
    def _create_order(self, data: dict, dup_result) -> Order:
        """Create order with provider and patient."""
        
        # Get or create provider
        if dup_result.existing_provider:
            provider = dup_result.existing_provider
        else:
            provider = Provider.objects.create(
                npi=data["provider_npi"],
                name=data["provider_name"],
            )
        
        # Get or create patient
        if dup_result.existing_patient:
            patient = dup_result.existing_patient
            # Optionally update patient info
            self._update_patient_if_needed(patient, data)
        else:
            patient = self._create_patient(data)
        
        # Generate duplicate hash
        duplicate_hash = OrderDuplicateDetector.generate_hash(
            str(patient.id),
            str(provider.id),
            data["medication_name"],
        )
        
        # Create order
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name=data["medication_name"],
            patient_records=data["patient_records"],
            duplicate_check_hash=duplicate_hash,
            confirmed_not_duplicate=data.get("confirm_not_duplicate", False),
            status="pending",
        )
        
        return order
    
    def _create_patient(self, data: dict) -> Patient:
        """Create new patient with diagnoses and medication history."""
        patient = Patient.objects.create(
            mrn=data["patient_mrn"],
            first_name=data["patient_first_name"],
            last_name=data["patient_last_name"],
            date_of_birth=data.get("patient_date_of_birth"),
            sex=data.get("patient_sex"),
            weight_kg=data.get("patient_weight_kg"),
            allergies=data.get("patient_allergies") or None,
            primary_diagnosis_code=data["primary_diagnosis_code"],
            primary_diagnosis_description=data.get("primary_diagnosis_description") or None,
        )
        
        # Create additional diagnoses
        for code in data.get("additional_diagnoses", []):
            PatientDiagnosis.objects.create(
                patient=patient,
                icd10_code=code,
                is_primary=False,
            )
        
        # Create medication history
        for med in data.get("medication_history", []):
            MedicationHistory.objects.create(
                patient=patient,
                medication_name=med,
            )
        
        return patient
    
    def _update_patient_if_needed(self, patient: Patient, data: dict):
        """Update patient info if new data is more complete."""
        updated = False
        
        # Update optional fields if they were empty and now have values
        if not patient.date_of_birth and data.get("patient_date_of_birth"):
            patient.date_of_birth = data["patient_date_of_birth"]
            updated = True
        
        if not patient.sex and data.get("patient_sex"):
            patient.sex = data["patient_sex"]
            updated = True
        
        if not patient.weight_kg and data.get("patient_weight_kg"):
            patient.weight_kg = data["patient_weight_kg"]
            updated = True
        
        if not patient.allergies and data.get("patient_allergies"):
            patient.allergies = data["patient_allergies"]
            updated = True
        
        if updated:
            patient.save()
    
    def _queue_care_plan_generation(self, order: Order):
        """Queue care plan generation task."""
        # Import here to avoid circular imports
        try:
            from apps.care_plans.tasks import generate_care_plan
            generate_care_plan.delay(str(order.id))
            logger.info(f"Queued care plan generation for order {order.id}")
        except Exception as e:
            logger.error(f"Failed to queue care plan generation for order {order.id}: {e}")
            # Don't fail the order creation if queuing fails
            # The task can be manually triggered later
    
    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Regenerate care plan for an order."""
        order = self.get_object()
        
        # Reset status
        order.status = "pending"
        order.error_message = None
        order.save()
        
        # Delete existing care plan if any
        if hasattr(order, "care_plan"):
            order.care_plan.delete()
        
        # Queue regeneration
        self._queue_care_plan_generation(order)
        
        return Response({"message": "Care plan regeneration queued"})