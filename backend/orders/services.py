# backend/orders/services.py
"""
业务逻辑层（Service Layer）
=========================
所有"怎么做"的逻辑都在这里，views.py 只负责"接什么请求、返回什么响应"

"""
import google.generativeai as genai
from django.conf import settings

from .models import Order, CarePlan, Patient, Provider
from .tasks import generate_care_plan_task


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


# ============================================================
# 创建订单
# ============================================================
def create_order(validated_data):
    patient_data = {
        'first_name': validated_data.pop('patient_first_name'),
        'last_name': validated_data.pop('patient_last_name'),
        'mrn': validated_data.pop('patient_mrn'),
        'dob': validated_data.pop('patient_dob'),
    }

    provider_data = {
        'name': validated_data.pop('provider_name'),
        'npi': validated_data.pop('provider_npi'),
    }

    patient, created = Patient.objects.get_or_create(
        mrn=patient_data['mrn'],
        defaults=patient_data
    )

    provider, created = Provider.objects.get_or_create(
        npi=provider_data['npi'],
        defaults=provider_data
    )

    order = Order.objects.create(
        patient=patient,
        provider=provider,
        **validated_data
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
