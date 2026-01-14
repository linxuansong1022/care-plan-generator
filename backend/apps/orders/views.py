"""
Order views.
"""

import time

import structlog
from django.db import transaction
from prometheus_client import Counter, Histogram
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

# Structured logger
logger = structlog.get_logger(__name__)

# Prometheus metrics
ORDER_CREATED_TOTAL = Counter(
    "order_created_total",
    "Total number of orders created",
    ["status"],  # success, error, duplicate_blocked, duplicate_warning
)
ORDER_CREATE_DURATION = Histogram(
    "order_create_duration_seconds",
    "Time spent creating an order",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
DUPLICATE_DETECTION_TOTAL = Counter(
    "duplicate_detection_total",
    "Duplicate detection results",
    ["type", "result"],  # type: patient/provider/order, result: exact_match/conflict/warning/none
)
CARE_PLAN_QUEUED_TOTAL = Counter(
    "care_plan_queued_total",
    "Care plan generation tasks queued",
    ["status"],  # success, error
)


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
        3. If blocking duplicate → return 409 Conflict (cannot proceed)
        4. If potential duplicate and not confirmed → return 200 with requires_confirmation=true
        5. If confirmed or no duplicates → create order and return 201
        """
        start_time = time.time()

        # Log incoming request (no PHI - only metadata)
        logger.info(
            "order_create_started",
            medication=request.data.get("medication_name"),
            has_patient_records=bool(request.data.get("patient_records")),
        )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "order_validation_failed",
                errors=serializer.errors,
            )
            ORDER_CREATED_TOTAL.labels(status="validation_error").inc()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Run duplicate detection
        logger.debug("duplicate_detection_started")
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

        # Log duplicate detection results
        self._log_duplicate_results(dup_result)

        # Check for blocking issues
        if dup_result.has_blocking_issues:
            logger.warning(
                "order_blocked_duplicate",
                medication=data["medication_name"],
                blocking_reasons=[w.code for w in dup_result.all_warnings if w.action_required],
            )
            ORDER_CREATED_TOTAL.labels(status="duplicate_blocked").inc()
            raise DuplicateBlockedException(
                detail=[w.message for w in dup_result.all_warnings if w.action_required]
            )

        # Check if confirmation required
        if dup_result.requires_confirmation and not data.get("confirm_not_duplicate"):
            logger.info(
                "order_requires_confirmation",
                medication=data["medication_name"],
                warning_codes=[w.code for w in dup_result.all_warnings],
            )
            ORDER_CREATED_TOTAL.labels(status="duplicate_warning").inc()

            # Helper to serialize warning objects
            def serialize_warning(w):
                return {
                    "code": w.code,
                    "message": w.message,
                    "action_required": w.action_required,
                    "data": w.data,
                }

            # Return 200 with warnings - user can confirm and resubmit
            return Response(
                {
                    "order": None,
                    "warnings": [serialize_warning(w) for w in dup_result.all_warnings],
                    "patient_warnings": [
                        serialize_warning(w) for w in dup_result.patient_result.warnings if w.action_required
                    ],
                    "provider_warnings": [
                        serialize_warning(w) for w in dup_result.provider_result.warnings if w.action_required
                    ],
                    "is_potential_duplicate": True,
                    "requires_confirmation": True,
                    "is_blocked": False,
                    "duplicate_order_id": (
                        str(dup_result.order_result.existing_record.id)
                        if dup_result.order_result and dup_result.order_result.existing_record
                        else None
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # Create order with all entities
        try:
            order = self._create_order(data, dup_result)

            # Queue care plan generation
            self._queue_care_plan_generation(order)

            # Record metrics
            duration = time.time() - start_time
            ORDER_CREATE_DURATION.observe(duration)
            ORDER_CREATED_TOTAL.labels(status="success").inc()

            # Log success
            logger.info(
                "order_created_success",
                order_id=str(order.id),
                medication=order.medication_name,
                duration_ms=round(duration * 1000, 2),
                reused_patient=bool(dup_result.existing_patient),
                reused_provider=bool(dup_result.existing_provider),
            )

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
            duration = time.time() - start_time
            ORDER_CREATE_DURATION.observe(duration)
            ORDER_CREATED_TOTAL.labels(status="error").inc()

            logger.error(
                "order_create_failed",
                error=str(e),
                error_type=type(e).__name__,
                medication=data["medication_name"],
                duration_ms=round(duration * 1000, 2),
            )
            raise

    def _log_duplicate_results(self, dup_result):
        """Log duplicate detection results for metrics."""
        # Patient duplicate detection
        if dup_result.patient_result:
            if dup_result.existing_patient:
                DUPLICATE_DETECTION_TOTAL.labels(type="patient", result="exact_match").inc()
            elif dup_result.patient_result.warnings:
                DUPLICATE_DETECTION_TOTAL.labels(type="patient", result="warning").inc()
            else:
                DUPLICATE_DETECTION_TOTAL.labels(type="patient", result="none").inc()

        # Provider duplicate detection
        if dup_result.provider_result:
            if dup_result.existing_provider:
                DUPLICATE_DETECTION_TOTAL.labels(type="provider", result="exact_match").inc()
            elif dup_result.provider_result.warnings:
                DUPLICATE_DETECTION_TOTAL.labels(type="provider", result="warning").inc()
            else:
                DUPLICATE_DETECTION_TOTAL.labels(type="provider", result="none").inc()

        # Order duplicate detection
        if dup_result.order_result:
            if dup_result.order_result.existing_record:
                DUPLICATE_DETECTION_TOTAL.labels(type="order", result="conflict").inc()
            elif dup_result.order_result.warnings:
                DUPLICATE_DETECTION_TOTAL.labels(type="order", result="warning").inc()
            else:
                DUPLICATE_DETECTION_TOTAL.labels(type="order", result="none").inc()
    
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
        
        # Create order
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name=data["medication_name"],
            patient_records=data["patient_records"],
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
            CARE_PLAN_QUEUED_TOTAL.labels(status="success").inc()
            logger.info(
                "care_plan_queued",
                order_id=str(order.id),
                medication=order.medication_name,
            )
        except Exception as e:
            CARE_PLAN_QUEUED_TOTAL.labels(status="error").inc()
            logger.error(
                "care_plan_queue_failed",
                order_id=str(order.id),
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't fail the order creation if queuing fails
            # The task can be manually triggered later
    
    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Regenerate care plan for an order."""
        order = self.get_object()

        logger.info(
            "care_plan_regenerate_started",
            order_id=str(order.id),
            previous_status=order.status,
        )

        # Reset status
        order.status = "pending"
        order.error_message = None
        order.save()

        # Delete existing care plan if any
        if hasattr(order, "care_plan"):
            order.care_plan.delete()
            logger.info(
                "care_plan_deleted_for_regeneration",
                order_id=str(order.id),
            )

        # Queue regeneration
        self._queue_care_plan_generation(order)

        return Response({"message": "Care plan regeneration queued"})