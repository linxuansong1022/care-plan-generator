# backend/orders/services.py
"""
业务逻辑层（Service Layer）
=========================
所有"怎么做"的逻辑都在这里，views.py 只负责"接什么请求、返回什么响应"

"""
from .adapters.base import InternalOrder
import google.generativeai as genai
from django.conf import settings

from .models import Order, CarePlan, Patient, Provider
from .tasks import generate_care_plan_task
from django.utils import timezone
from .exceptions import BlockError, WarningException


# ============================================================
# LLM 调用
# ============================================================
def generate_care_plan(order):
    """调用 Google Gemini API 生成 Care Plan（同步）"""
    prompt = f"""You are a clinical pharmacist creating a care plan for a specialty pharmacy patient.

Patient Information:
- Name: {order.patient.first_name} {order.patient.last_name}
- Date of Birth: {order.patient.dob}
- MRN: {order.patient.mrn}

Provider: {order.provider.name} (NPI: {order.provider.npi})

Medication: {order.medication_name}
Primary Diagnosis (ICD-10): {order.primary_diagnosis}
Additional Diagnoses: {', '.join(order.additional_diagnoses) if order.additional_diagnoses else 'None'}
Medication History: {', '.join(order.medication_history) if order.medication_history else 'None'}
Patient Records/Notes: {order.patient_records if order.patient_records else 'None provided'}

Please generate a comprehensive pharmaceutical care plan with EXACTLY these four sections:

1. **Problem List / Drug Therapy Problems (DTPs)**
   - Identify potential drug therapy problems related to the prescribed medication and diagnoses

2. **Goals (SMART format)**
   - Specific, Measurable, Achievable, Relevant, Time-bound goals for this patient

3. **Pharmacist Interventions / Plan**
   - Specific actions the pharmacist should take
   - Patient education points
   - Coordination with the prescribing provider

4. **Monitoring Plan & Lab Schedule**
   - Labs to monitor and frequency
   - Clinical parameters to track
   - Follow-up schedule

Be specific and clinically relevant to the medication and diagnoses provided."""

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_provider(provider_data):
    """Provider 重复检测"""
    npi = provider_data['npi']
    name = provider_data['name']
    
    try:
        existing = Provider.objects.get(npi=npi)
    except Provider.DoesNotExist:
        return None  # 全新 NPI，没问题
    
    if existing.name == name:
        return existing  # NPI + 名字都一样，完美复用
    raise BlockError(                               # ← 改：raise 替代 return
        message="Provider NPI conflict",
        detail=f"NPI {npi} is already registered to '{existing.name}', "
               f"but you submitted '{name}'.",
        code="PROVIDER_NPI_CONFLICT"
    )

def check_patient(patient_data, confirm=False):
    """Patient 重复检测"""
    mrn = patient_data['mrn']
    first_name = patient_data['first_name']
    last_name = patient_data['last_name']
    dob = patient_data['dob']
    
    warnings = []
    
    # 检查 1: MRN 已存在
    try:
        existing = Patient.objects.get(mrn=mrn)
        if (existing.first_name == first_name 
            and existing.last_name == last_name 
            and str(existing.dob) == str(dob)):
            return existing
        else:
            warnings.append(
                f"MRN {mrn} exists for '{existing.first_name} {existing.last_name}' "
                f"(DOB: {existing.dob}), but you submitted "
                f"'{first_name} {last_name}' (DOB: {dob})."
            )
    except Patient.DoesNotExist:
        pass
    
    # 检查 2: 名字+DOB 相同但 MRN 不同
    same_name_dob = Patient.objects.filter(
        first_name=first_name,
        last_name=last_name,
        dob=dob
    ).exclude(mrn=mrn)
    
    if same_name_dob.exists():
        match = same_name_dob.first()
        warnings.append(
            f"Patient '{first_name} {last_name}' (DOB: {dob}) already exists "
            f"with MRN {match.mrn}, but you submitted MRN {mrn}."
        )
    
    if warnings and not confirm:
        raise WarningException(                     # ← 改：raise 替代 return
            message="Possible duplicate patient",
            detail=warnings,
            code="PATIENT_DUPLICATE_WARNING"
        )
    
    return None


def check_order_duplicate(patient, medication_name, confirm=False):
    """Order 重复检测"""
    today = timezone.now().date()
    
    existing = Order.objects.filter(
        patient=patient,
        medication_name__iexact=medication_name
    )
    
    if not existing.exists():
        return None
    
    # 同患者 + 同药 + 同一天 → ERROR（不可跳过）
    if existing.filter(created_at__date=today).exists():
        raise BlockError(                           # ← 改：raise
            message="Duplicate order",
            detail=f"Patient {patient.first_name} {patient.last_name} "
                   f"(MRN: {patient.mrn}) already has an order for "
                   f"'{medication_name}' today.",
            code="ORDER_SAME_DAY_DUPLICATE"
        )
    
    # 同患者 + 同药 + 不同天 → WARNING
    latest = existing.order_by('-created_at').first()
    if not confirm:
        raise WarningException(                     # ← 改：raise
            message="Previous order exists",
            detail=f"Patient {patient.first_name} {patient.last_name} "
                   f"(MRN: {patient.mrn}) had a previous order for "
                   f"'{medication_name}' on {latest.created_at.date()}.",
            code="ORDER_PREVIOUS_EXISTS"
        )
    
    return None
# ============================================================
# 创建订单
# ============================================================
def create_order(internal_order: InternalOrder):
    patient_data = {
        'first_name': internal_order.patient.first_name,
        'last_name': internal_order.patient.last_name,
        'mrn': internal_order.patient.mrn,
        'dob': internal_order.patient.dob,
    }

    provider_data = {
        'name': internal_order.provider.name,
        'npi': internal_order.provider.npi,
    }

    # === 重复检测 ===
    provider = check_provider(provider_data)        # ← 有问题直接 raise 了，不会走到下一行
    patient = check_patient(patient_data, confirm=internal_order.confirm)
    if provider is None:
        provider = Provider.objects.create(**provider_data)
    if patient is None:
        patient, _ = Patient.objects.get_or_create(
            mrn=patient_data['mrn'], defaults=patient_data
        )
    check_order_duplicate(patient, internal_order.medication_name, confirm=internal_order.confirm)
    
    order = Order.objects.create(
        patient=patient, 
        provider=provider,
        medication_name=internal_order.medication_name,
        primary_diagnosis=internal_order.primary_diagnosis,
        additional_diagnoses=internal_order.additional_diagnoses,
        medication_history=internal_order.medication_history,
        patient_records=internal_order.patient_records
    )
    return order 
  
def submit_care_plan_task(order_id):
    """触发 Celery 异步任务生成 care plan"""
    generate_care_plan_task.delay(order_id)


# ============================================================
# 查询订单状态
# ============================================================
def get_order_status(order_id):
    """
    查询订单状态，返回 dict 或 None（订单不存在时）
    """
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return None

    data = {
        'order_id': order.id,
        'status': order.status,
        'patient_first_name': order.patient.first_name,
        'patient_last_name': order.patient.last_name,
        'medication_name': order.medication_name,
    }

    if order.status == 'completed' and hasattr(order, 'care_plan'):
        data['care_plan_content'] = order.care_plan.content

    return data


# ============================================================
# 获取 Care Plan 详情
# ============================================================
def get_care_plan_detail(order_id):
    """
    返回 care plan 详情 dict
    如果出错，返回带 'error' key 的 dict
    """
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return {'error': 'Order does not exist'}

    if order.status != 'completed' or not hasattr(order, 'care_plan'):
        return {'error': 'Care plan not available'}

    return {
        'order_id': order.id,
        'status': order.status,
        'patient_name': f"{order.patient.first_name} {order.patient.last_name}",
        'medication': order.medication_name,
        'care_plan_content': order.care_plan.content,
    }


# ============================================================
# 组装 Care Plan 下载文件
# ============================================================
def build_care_plan_file(order_id):
    """
    组装文件内容和文件名
    成功：返回 (file_content_string, filename_string)
    失败：返回 (None, error_message_string)
    """
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return (None, 'Order not found')

    if order.status != 'completed' or not hasattr(order, 'care_plan'):
        return (None, 'Care plan not available')

    file_content = f"""PHARMACEUTICAL CARE PLAN
{'='*50}
Patient: {order.patient.first_name} {order.patient.last_name}
MRN: {order.patient.mrn}
DOB: {order.patient.dob}
Provider: {order.provider.name} (NPI: {order.provider.npi})
Medication: {order.medication_name}
Primary Diagnosis: {order.primary_diagnosis}
Generated: {order.created_at.strftime('%Y-%m-%d %H:%M')}
{'='*50}

{order.care_plan.content}
"""

    filename = f"careplan_{order.patient.mrn}_{order.medication_name}_{order.order_date}.txt"
    filename = filename.replace(' ', '_').replace('/', '_')

    return (file_content, filename)
