"""
test_check_order.py — Order 重复检测 Unit Test
===============================================
测试 services.check_order_duplicate() 的所有场景
"""
import pytest
from orders.services import check_order_duplicate
from orders.exceptions import BlockError, WarningException


# ────────────────────────────────────────────
# 场景 1: 无重复 → 放行
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_no_duplicate_returns_none(existing_patient):
    """该患者从未下过这个药的订单"""
    result = check_order_duplicate(existing_patient, 'Rituximab')
    assert result is None


# ────────────────────────────────────────────
# 场景 2: 同患者 + 同药 + 同一天 → BlockError
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_day_duplicate_raises_block(existing_order):
    """今天已经有同样的订单，必须阻止"""
    patient = existing_order.patient
    with pytest.raises(BlockError) as exc_info:
        check_order_duplicate(patient, 'IVIG')

    assert exc_info.value.code == 'ORDER_SAME_DAY_DUPLICATE'


# ────────────────────────────────────────────
# 场景 3: 同患者 + 同药 + 不同天 → Warning
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_different_day_duplicate_raises_warning(old_order):
    """3 天前有过同样的订单，应该警告"""
    patient = old_order.patient
    with pytest.raises(WarningException) as exc_info:
        check_order_duplicate(patient, 'IVIG')

    assert exc_info.value.code == 'ORDER_PREVIOUS_EXISTS'


# ────────────────────────────────────────────
# 场景 4: 同患者 + 同药 + 不同天 + confirm=True → 放行
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_different_day_with_confirm_passes(old_order):
    """有旧订单但用户确认了，应该放行"""
    patient = old_order.patient
    result = check_order_duplicate(patient, 'IVIG', confirm=True)
    assert result is None


# ────────────────────────────────────────────
# 场景 5: 大小写不敏感
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_case_insensitive_medication(existing_order):
    """'ivig' 和 'IVIG' 应该被视为同一个药"""
    patient = existing_order.patient
    with pytest.raises(BlockError):
        check_order_duplicate(patient, 'ivig')  # 小写


# ────────────────────────────────────────────
# 场景 6: 不同药 → 不算重复
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_different_medication_no_conflict(existing_order):
    """同患者但不同药物，不算重复"""
    patient = existing_order.patient
    result = check_order_duplicate(patient, 'Rituximab')
    assert result is None
