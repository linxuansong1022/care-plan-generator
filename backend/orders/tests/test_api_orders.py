"""
test_api_orders.py — Integration Tests
=======================================
测试完整的 HTTP 请求 → 响应流程。
不测单个函数，测的是"前端发什么请求，后端返回什么"。

Unit Test vs Integration Test:
- Unit: check_patient({'mrn': '123456', ...}) → raise WarningException?
- Integration: POST /api/orders/ {mrn: '123456', ...} → HTTP 200 + warning JSON?
"""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from datetime import date
from django.utils import timezone
from orders.models import Patient, Provider, Order


@pytest.fixture
def api_client():
    """DRF 的测试客户端，用来模拟 HTTP 请求"""
    return APIClient()


# ============================================================
# 成功场景
# ============================================================

@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')  # mock 掉 Celery，不真的发任务
def test_create_order_success(mock_task, api_client, sample_order_payload):
    """
    正常提交一个新订单，应该：
    - 返回 202
    - 创建 Patient、Provider、Order
    - 触发 Celery task
    """
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 202
    assert Patient.objects.count() == 1
    assert Provider.objects.count() == 1
    assert Order.objects.count() == 1
    mock_task.assert_called_once()  # 确认 Celery task 被触发了


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_reuse_existing_patient_and_provider(mock_task, api_client, sample_order_payload,
                                              existing_patient, existing_provider):
    """
    提交的 Patient 和 Provider 已存在（MRN+名字+DOB 完全匹配），
    应该复用而不是创建新的
    """
    # 换一个不同的药，避免触发 order 重复检测
    sample_order_payload['medication_name'] = 'Rituximab'
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 202
    assert Patient.objects.count() == 1   # 没有新增
    assert Provider.objects.count() == 1  # 没有新增
    assert Order.objects.count() == 1


# ============================================================
# Provider Error 场景
# ============================================================

@pytest.mark.django_db
def test_provider_npi_conflict_returns_409(api_client, sample_order_payload, existing_provider):
    """NPI 已存在但名字不同 → 409 error"""
    sample_order_payload['provider_name'] = 'Dr. Totally Different'  # 名字不同
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 409
    assert response.data['type'] == 'error'
    assert response.data['code'] == 'PROVIDER_NPI_CONFLICT'


# ============================================================
# Patient Warning 场景
# ============================================================

@pytest.mark.django_db
def test_patient_mrn_mismatch_returns_warning(api_client, sample_order_payload, existing_patient):
    """MRN 相同但名字不同 → 200 warning"""
    sample_order_payload['patient_first_name'] = 'John'
    sample_order_payload['patient_last_name'] = 'Smith'
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 200
    assert response.data['type'] == 'warning'
    assert response.data['code'] == 'PATIENT_DUPLICATE_WARNING'
    assert len(response.data['detail']) >= 1


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_patient_warning_with_confirm_creates_order(mock_task, api_client,
                                                      sample_order_payload, existing_patient):
    """Patient 有 warning 但 confirm=True → 跳过警告，成功创建"""
    sample_order_payload['patient_first_name'] = 'John'
    sample_order_payload['patient_last_name'] = 'Smith'
    sample_order_payload['confirm'] = True  # 用户确认
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 202
    assert Order.objects.count() == 1


# ============================================================
# Order Duplicate 场景
# ============================================================

@pytest.mark.django_db
def test_same_day_order_returns_409_error(api_client, sample_order_payload, existing_order):
    """同患者 + 同药 + 同一天 → 409 error，不可跳过"""
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 409
    assert response.data['type'] == 'error'
    assert response.data['code'] == 'ORDER_SAME_DAY_DUPLICATE'


@pytest.mark.django_db
def test_different_day_order_returns_warning(api_client, sample_order_payload, old_order):
    """同患者 + 同药 + 不同天 → warning"""
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 200
    assert response.data['type'] == 'warning'
    assert response.data['code'] == 'ORDER_PREVIOUS_EXISTS'


@pytest.mark.django_db
@patch('orders.services.submit_care_plan_task')
def test_different_day_order_with_confirm_succeeds(mock_task, api_client,
                                                     sample_order_payload, old_order):
    """同患者 + 同药 + 不同天 + confirm=True → 成功"""
    sample_order_payload['confirm'] = True
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 202


# ============================================================
# Validation Error 场景（serializer 层）
# ============================================================

@pytest.mark.django_db
def test_missing_required_field_returns_400(api_client):
    """缺少必填字段 → 400"""
    response = api_client.post('/api/orders/', {}, format='json')

    assert response.status_code == 400
    assert response.data['type'] == 'error'
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
def test_invalid_dob_format_returns_400(api_client, sample_order_payload):
    """DOB 格式不对 → 400"""
    sample_order_payload['patient_dob'] = 'not-a-date'
    response = api_client.post('/api/orders/', sample_order_payload, format='json')

    assert response.status_code == 400
    assert response.data['type'] == 'error'


# ============================================================
# GET 接口测试
# ============================================================

@pytest.mark.django_db
def test_get_orders_list(api_client, existing_order):
    """GET /api/orders/ 应该返回订单列表"""
    response = api_client.get('/api/orders/')

    assert response.status_code == 200
    assert len(response.data) >= 1


@pytest.mark.django_db
def test_get_order_status_not_found(api_client):
    """查询不存在的订单 → 404"""
    response = api_client.get('/api/orders/99999/status/')

    assert response.status_code == 404
