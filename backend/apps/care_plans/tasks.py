"""
Celery tasks for care plan generation.
"""

import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings

from apps.orders.models import Order

from .llm_service import get_llm_service
from .models import CarePlan
from .prompts import CARE_PLAN_SYSTEM_PROMPT, build_care_plan_prompt

logger = logging.getLogger(__name__)


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
    logger.info(f"Starting care plan generation for order {order_id}")
    
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
            logger.info(f"Care plan already exists for order {order_id}")
            return {"status": "already_exists", "order_id": order_id}
        
        # Update status to processing
        order.status = "processing"
        order.save(update_fields=["status", "updated_at"])
        
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
        
        # Generate with LLM
        llm_service = get_llm_service()
        response = llm_service.generate(
            prompt=prompt,
            system_prompt=CARE_PLAN_SYSTEM_PROMPT,
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
            logger.warning(f"Failed to save care plan file for order {order_id}: {e}")
            # Don't fail the task if file save fails
        
        # Update order status
        order.status = "completed"
        order.save(update_fields=["status", "updated_at"])
        
        logger.info(f"Successfully generated care plan for order {order_id}")
        
        return {
            "status": "success",
            "order_id": order_id,
            "care_plan_id": str(care_plan.id),
            "tokens_used": response.total_tokens,
            "generation_time_ms": response.generation_time_ms,
        }
    
    except Order.DoesNotExist:
        logger.error(f"Order not found: {order_id}")
        return {"status": "error", "message": "Order not found"}
    
    except Exception as e:
        logger.exception(f"Error generating care plan for order {order_id}")
        
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
