"""
Celery tasks for care plan generation.
"""

import time
from datetime import datetime

import structlog
from celery import shared_task
from django.conf import settings
from prometheus_client import Counter, Histogram

from apps.orders.models import Order

from .llm_service import get_llm_service
from .models import CarePlan
from .prompts import build_care_plan_prompt
from .skeleton_analyzer import get_dynamic_skeleton, build_dynamic_system_prompt

logger = structlog.get_logger(__name__)

# Prometheus metrics for care plan generation
CARE_PLAN_GENERATION_TOTAL = Counter(
    "care_plan_generation_total",
    "Total care plan generation attempts",
    ["status"],  # success, error, already_exists, order_not_found
)
CARE_PLAN_GENERATION_DURATION = Histogram(
    "care_plan_generation_duration_seconds",
    "Time spent generating care plans",
    buckets=[1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)
LLM_TOKENS_USED = Counter(
    "llm_tokens_used_total",
    "Total LLM tokens used",
    ["type"],  # prompt, completion
)
CARE_PLAN_RETRY_TOTAL = Counter(
    "care_plan_retry_total",
    "Care plan generation retries",
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    max_retries=3,
)
def generate_care_plan(self, order_id: str):
    """
    Generate care plan for an order.

    This task is automatically retried on failure with exponential backoff.
    """
    start_time = time.time()

    # Log retry info if this is a retry
    if self.request.retries > 0:
        CARE_PLAN_RETRY_TOTAL.inc()
        logger.warning(
            "care_plan_generation_retry",
            order_id=order_id,
            retry_count=self.request.retries,
            max_retries=self.max_retries,
        )

    logger.info(
        "care_plan_generation_started",
        order_id=order_id,
        retry_count=self.request.retries,
    )

    try:
        # Get order with related data
        order = Order.objects.select_related(
            "patient", "provider"
        ).prefetch_related(
            "patient__diagnoses",
            "patient__medication_history",
        ).get(id=order_id)

        # Check if care plan already exists
        if hasattr(order, "care_plan"):
            logger.info(
                "care_plan_already_exists",
                order_id=order_id,
            )
            CARE_PLAN_GENERATION_TOTAL.labels(status="already_exists").inc()
            return {"status": "already_exists", "order_id": order_id}

        # Update status to processing
        order.status = "processing"
        order.save(update_fields=["status", "updated_at"])

        logger.debug(
            "care_plan_building_prompt",
            order_id=order_id,
            medication=order.medication_name,
        )

        # Build prompt
        patient = order.patient

        additional_diagnoses = [d.icd10_code for d in patient.diagnoses.all() if not d.is_primary]

        medication_history = [
            f"{m.medication_name} {m.dosage or ''} {m.frequency or ''}".strip()
            for m in patient.medication_history.all()
        ]

        prompt = build_care_plan_prompt(
            first_name=patient.first_name,
            last_name=patient.last_name,
            mrn=patient.mrn,
            dob=str(patient.date_of_birth) if patient.date_of_birth else None,
            sex=patient.sex,
            weight_kg=float(patient.weight_kg) if patient.weight_kg else None,
            allergies=patient.allergies,
            primary_diagnosis_code=patient.primary_diagnosis_code,
            primary_diagnosis_description=patient.primary_diagnosis_description,
            additional_diagnoses=additional_diagnoses,
            medication_name=order.medication_name,
            medication_history=medication_history,
            patient_records=order.patient_records,
        )

        # Get LLM service
        llm_service = get_llm_service()

        # Get dynamic skeleton from recent care plans
        logger.debug("skeleton_analysis_starting", order_id=order_id)
        skeleton = get_dynamic_skeleton(use_llm=False)  # Use simple extraction (faster)
        system_prompt = build_dynamic_system_prompt(skeleton)

        # === DEBUG: Log prompts for testing ===
        # Using WARNING level to ensure visibility in logs
        logger.warning(
            "DEBUG_SKELETON",
            order_id=order_id,
            medication=order.medication_name,
            patient=f"{patient.first_name} {patient.last_name}",
            mrn=patient.mrn,
            skeleton=skeleton,
        )

        logger.warning(
            "DEBUG_SYSTEM_PROMPT",
            order_id=order_id,
            system_prompt=system_prompt,
        )

        logger.warning(
            "DEBUG_USER_PROMPT",
            order_id=order_id,
            user_prompt=prompt[:1500],  # First 1500 chars
            total_length=len(prompt),
        )

        logger.info(
            "llm_generation_started",
            order_id=order_id,
            llm_provider=settings.LLM_PROVIDER,
            skeleton_sections=skeleton.count("\n"),
            system_prompt_length=len(system_prompt),
            user_prompt_length=len(prompt),
        )

        # Generate with LLM using dynamic system prompt
        response = llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        # Record LLM token metrics
        LLM_TOKENS_USED.labels(type="prompt").inc(response.prompt_tokens)
        LLM_TOKENS_USED.labels(type="completion").inc(response.completion_tokens)

        logger.info(
            "llm_generation_completed",
            order_id=order_id,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            generation_time_ms=response.generation_time_ms,
        )

        # Create care plan record
        care_plan = CarePlan.objects.create(
            order=order,
            content=response.content,
            llm_model=response.model,
            llm_prompt_tokens=response.prompt_tokens,
            llm_completion_tokens=response.completion_tokens,
            generation_time_ms=response.generation_time_ms,
            generated_at=datetime.now(),
        )

        # Save file (if storage configured)
        try:
            file_path = save_care_plan_file(order, care_plan)
            care_plan.file_path = file_path
            care_plan.save(update_fields=["file_path"])
        except Exception as e:
            logger.warning(
                "care_plan_file_save_failed",
                order_id=order_id,
                error=str(e),
            )
            # Don't fail the task if file save fails

        # Update order status
        order.status = "completed"
        order.save(update_fields=["status", "updated_at"])

        # Record success metrics
        duration = time.time() - start_time
        CARE_PLAN_GENERATION_DURATION.observe(duration)
        CARE_PLAN_GENERATION_TOTAL.labels(status="success").inc()

        logger.info(
            "care_plan_generation_success",
            order_id=order_id,
            care_plan_id=str(care_plan.id),
            duration_seconds=round(duration, 2),
            total_tokens=response.total_tokens,
        )

        return {
            "status": "success",
            "order_id": order_id,
            "care_plan_id": str(care_plan.id),
            "tokens_used": response.total_tokens,
            "generation_time_ms": response.generation_time_ms,
        }

    except Order.DoesNotExist:
        logger.error(
            "care_plan_order_not_found",
            order_id=order_id,
        )
        CARE_PLAN_GENERATION_TOTAL.labels(status="order_not_found").inc()
        return {"status": "error", "message": "Order not found"}

    except Exception as e:
        duration = time.time() - start_time
        CARE_PLAN_GENERATION_DURATION.observe(duration)
        CARE_PLAN_GENERATION_TOTAL.labels(status="error").inc()

        logger.error(
            "care_plan_generation_failed",
            order_id=order_id,
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=round(duration, 2),
            retry_count=self.request.retries,
            will_retry=self.request.retries < self.max_retries,
        )

        # Update order status to failed
        try:
            order = Order.objects.get(id=order_id)
            order.status = "failed"
            order.error_message = str(e)[:1000]  # Truncate error message
            order.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass

        # Re-raise to trigger retry
        raise


def save_care_plan_file(order: Order, care_plan: CarePlan) -> str:
    """
    Save care plan to file storage.
    
    Returns the file path/key.
    """
    patient = order.patient
    provider = order.provider
    
    # Format content with header
    content = f"""================================================================================
PHARMACIST CARE PLAN
================================================================================

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

PATIENT INFORMATION
-------------------
Name: {patient.first_name} {patient.last_name}
MRN: {patient.mrn}
Primary Diagnosis: {patient.primary_diagnosis_code}
Medication: {order.medication_name}

REFERRING PROVIDER
------------------
Name: {provider.name}
NPI: {provider.npi}

================================================================================
CARE PLAN CONTENT
================================================================================

{care_plan.content}
"""
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"care_plan_{patient.mrn}_{timestamp}.txt"
    
    # For now, save locally
    # In production, this would upload to S3
    import os
    
    storage_dir = os.path.join(settings.BASE_DIR, "storage", "care_plans")
    os.makedirs(storage_dir, exist_ok=True)
    
    file_path = os.path.join(storage_dir, filename)
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return file_path
