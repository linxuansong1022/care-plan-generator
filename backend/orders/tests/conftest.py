"""
conftest.py — 测试 Fixtures（夹具）
==================================
Fixture 就是"预制的测试数据"。
每个 test 函数可以通过参数名直接拿到这些数据，
pytest 会自动注入，不需要你手动调用。

类比：考试前老师发的"标准答题纸"——每道题拿到的都是干净的。
"""
import pytest
from datetime import date
from django.utils import timezone
from orders.models import Patient, Provider, Order


# ============================================================
# 基础数据 Fixtures
# ============================================================

@pytest.fixture
def sample_provider_data():
    """一组合法的 Provider 数据（还没存进数据库）"""
    return {
        'name': 'Dr. Sarah Johnson',
        'npi': '1234567890',
    }


@pytest.fixture
def sample_patient_data():
    """一组合法的 Patient 数据（还没存进数据库）"""
    return {
        'first_name': 'Jane',
        'last_name': 'Doe',
        'mrn': '123456',
        'dob': date(1979, 6, 8),
    }


@pytest.fixture
def sample_order_payload():
    """
    完整的 POST /api/orders/ 请求体。
    Integration test 用这个直接发 HTTP 请求。
    """
    return {
        'patient_first_name': 'Jane',
        'patient_last_name': 'Doe',
        'patient_mrn': '123456',
        'patient_dob': '1979-06-08',
        'provider_name': 'Dr. Sarah Johnson',
        'provider_npi': '1234567890',
        'medication_name': 'IVIG',
        'primary_diagnosis': 'G70.01',
        'additional_diagnoses': [],
        'medication_history': [],
        'patient_records': '',
    }


# ============================================================
# 数据库里已存在的记录 Fixtures
# ============================================================

@pytest.fixture
def existing_provider(db):
    """数据库里已经有一个 Provider"""
    return Provider.objects.create(
        name='Dr. Sarah Johnson',
        npi='1234567890',
    )


@pytest.fixture
def existing_patient(db):
    """数据库里已经有一个 Patient"""
    return Patient.objects.create(
        first_name='Jane',
        last_name='Doe',
        mrn='123456',
        dob=date(1979, 6, 8),
    )


@pytest.fixture
def existing_order(db, existing_patient, existing_provider):
    """数据库里已经有一个今天的 Order"""
    return Order.objects.create(
        patient=existing_patient,
        provider=existing_provider,
        medication_name='IVIG',
        primary_diagnosis='G70.01',
        status='pending',
    )


@pytest.fixture
def old_order(db, existing_patient, existing_provider):
    """数据库里有一个 3 天前的 Order（用于测试"同药不同天"）"""
    order = Order.objects.create(
        patient=existing_patient,
        provider=existing_provider,
        medication_name='IVIG',
        primary_diagnosis='G70.01',
        status='completed',
    )
    # 手动改 created_at 为 3 天前（created_at 有 auto_now_add，只能用 update 改）
    three_days_ago = timezone.now() - timezone.timedelta(days=3)
    Order.objects.filter(pk=order.pk).update(created_at=three_days_ago)
    order.refresh_from_db()
    return order
