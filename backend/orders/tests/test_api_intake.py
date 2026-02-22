# orders/tests/test_api_intake.py
"""
External Intake API Integration Tests
======================================
测试 POST /api/intake/?source=xxx 的完整流程：
  HTTP 请求 → adapter 转换 → serializer 验证 → service 创建 → 数据库

这些测试需要数据库（@pytest.mark.django_db）和 HTTP 客户端（APIClient）
Celery task 被 mock 掉，不真的发异步任务
"""

import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from orders.models import Order, Patient, Provider


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def clinic_b_payload():
    """Clinic B 的标准测试数据"""
    return {
        "pt_fname": "Maria",
        "pt_lname": "Garcia",
        "pt_id_num": "654321",
        "birth_date": "1990-03-15",
        "doc_name": "Dr. Lee",
        "doc_npi": "9876543210",
        "drug": "Humira",
        "main_icd10": "L40.0",
        "past_meds": "Methotrexate 15mg, Prednisone 5mg",
        "is_confirmed": False,
    }


# ============================================================
# 正常流程测试
# ============================================================

@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_clinic_b_creates_order_successfully(mock_task, api_client, clinic_b_payload):
    """Clinic B 正常数据 → 201 + 订单创建成功"""
    response = api_client.post(
        '/api/intake/?source=clinic_b',
        data=clinic_b_payload,
        format='json'
    )
    assert response.status_code == 201 or response.status_code == 202
    assert 'order_id' in response.data

    # 验证数据库里确实创建了记录
    order = Order.objects.get(id=response.data['order_id'])
    assert order.medication_name == "Humira"
    assert order.patient.first_name == "Maria"
    assert order.patient.mrn == "654321"
    assert order.provider.npi == "9876543210"


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_clinic_b_triggers_async_task(mock_task, api_client, clinic_b_payload):
    """外部数据源也应该触发 care plan 异步生成"""
    response = api_client.post(
        '/api/intake/?source=clinic_b',
        data=clinic_b_payload,
        format='json'
    )
    # submit_care_plan_task 应该被调用了一次
    assert mock_task.called
    order_id = response.data['order_id']
    mock_task.assert_called_once_with(order_id)


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_cvs_web_source_works(mock_task, api_client):
    """CVS web form 数据通过 intake API 也能成功"""
    payload = {
        "patient": {
            "first_name": "Jane",
            "last_name": "Doe",
            "mrn": "123456",
            "dob": "1979-06-08",
        },
        "provider": {
            "name": "Dr. Smith",
            "npi": "1234567890",
        },
        "medication_name": "IVIG",
        "primary_diagnosis": "G70.01",
    }
    response = api_client.post(
        '/api/intake/?source=cvs_web',
        data=payload,
        format='json'
    )
    assert response.status_code in (201, 202)
    assert 'order_id' in response.data


# ============================================================
# 参数错误测试
# ============================================================

@pytest.mark.django_db
def test_missing_source_returns_400(api_client, clinic_b_payload):
    """缺少 source 参数 → 400"""
    response = api_client.post(
        '/api/intake/',  # 没有 ?source=xxx
        data=clinic_b_payload,
        format='json'
    )
    assert response.status_code == 400
    assert 'source' in str(response.data).lower() or 'error' in response.data


@pytest.mark.django_db
def test_unknown_source_returns_400(api_client, clinic_b_payload):
    """不存在的 source → 400"""
    response = api_client.post(
        '/api/intake/?source=unknown_hospital',
        data=clinic_b_payload,
        format='json'
    )
    assert response.status_code == 400


# ============================================================
# Adapter 转换失败测试
# ============================================================

@pytest.mark.django_db
def test_clinic_b_missing_required_field_returns_400(api_client):
    """Clinic B 缺少必填字段 → adapter validate 失败 → 400"""
    payload = {
        "pt_fname": "Maria",
        "pt_lname": "Garcia",
        "pt_id_num": "",         # MRN 为空
        "birth_date": "1990-03-15",
        "doc_name": "Dr. Lee",
        "doc_npi": "9876543210",
        "drug": "Humira",
        "main_icd10": "L40.0",
    }
    response = api_client.post(
        '/api/intake/?source=clinic_b',
        data=payload,
        format='json'
    )
    assert response.status_code == 400


# ============================================================
# 业务逻辑验证（通过 intake API 触发 service 层的重复检测）
# ============================================================

@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_provider_npi_conflict_through_intake(mock_task, api_client, clinic_b_payload):
    """外部数据也应该触发 Provider NPI 冲突检测"""
    # 先创建一个 Provider
    Provider.objects.create(name="Dr. Existing", npi="9876543210")

    # 用不同的名字但相同 NPI 提交
    clinic_b_payload["doc_name"] = "Dr. Different"
    clinic_b_payload["doc_npi"] = "9876543210"

    response = api_client.post(
        '/api/intake/?source=clinic_b',
        data=clinic_b_payload,
        format='json'
    )
    # 应该返回 409（BlockError）由 exception_handler 处理
    assert response.status_code == 409
    assert response.data.get('code') == 'PROVIDER_NPI_CONFLICT'


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_duplicate_order_same_day_through_intake(mock_task, api_client, clinic_b_payload):
    """外部数据也应该触发同天重复订单检测"""
    # 先创建第一个订单
    response1 = api_client.post(
        '/api/intake/?source=clinic_b',
        data=clinic_b_payload,
        format='json'
    )
    assert response1.status_code in (201, 202)

    # 同一天再提交相同患者+相同药
    response2 = api_client.post(
        '/api/intake/?source=clinic_b',
        data=clinic_b_payload,
        format='json'
    )
    assert response2.status_code == 409
    assert response2.data.get('code') == 'ORDER_SAME_DAY_DUPLICATE'


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_patient_reuse_through_intake(mock_task, api_client, clinic_b_payload):
    """相同患者信息第二次提交应该复用已有 Patient 记录"""
    # 第一次提交
    api_client.post('/api/intake/?source=clinic_b', data=clinic_b_payload, format='json')

    # 改药名避免同天重复，但患者信息不变
    clinic_b_payload["drug"] = "Ocrevus"
    api_client.post('/api/intake/?source=clinic_b', data=clinic_b_payload, format='json')

    # Patient 表应该只有 1 条记录
    assert Patient.objects.count() == 1
    # Order 表应该有 2 条
    assert Order.objects.count() == 2
