"""
test_check_patient.py — Patient 重复检测 Unit Test
==================================================
测试 services.check_patient() 的所有场景

Patient 检测是最复杂的，有 6 种场景：
1. 全新患者 → None
2. MRN+名字+DOB 完全匹配 → 返回已有实例
3. MRN 相同 + 名字不同 → WarningException
4. MRN 相同 + DOB 不同 → WarningException
5. 名字+DOB 相同 + MRN 不同 → WarningException
6. 有 Warning 但 confirm=True → 跳过警告
"""
import pytest
from datetime import date
from orders.services import check_patient
from orders.exceptions import WarningException
from orders.models import Patient


# ────────────────────────────────────────────
# 场景 1: 全新患者
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_new_patient_returns_none(sample_patient_data):
    """数据库里没有这个患者，返回 None（后面会创建）"""
    result = check_patient(sample_patient_data)
    assert result is None


# ────────────────────────────────────────────
# 场景 2: 完全匹配 → 复用
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_exact_match_returns_existing(existing_patient, sample_patient_data):
    """MRN、名字、DOB 全部一致，返回已有实例"""
    result = check_patient(sample_patient_data)
    assert result is not None
    assert result.pk == existing_patient.pk


# ────────────────────────────────────────────
# 场景 3: MRN 相同 + 名字不同 → Warning
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_mrn_different_name_raises_warning(existing_patient):
    """MRN 已存在但名字不同，raise WarningException"""
    conflict_data = {
        'mrn': '123456',              # 同一个 MRN
        'first_name': 'John',         # 不同名字
        'last_name': 'Smith',
        'dob': date(1979, 6, 8),      # DOB 相同
    }
    with pytest.raises(WarningException) as exc_info:
        check_patient(conflict_data)

    assert exc_info.value.code == 'PATIENT_DUPLICATE_WARNING'
    assert 'MRN 123456' in exc_info.value.detail[0]


# ────────────────────────────────────────────
# 场景 4: MRN 相同 + DOB 不同 → Warning
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_mrn_different_dob_raises_warning(existing_patient):
    """MRN 已存在但 DOB 不同"""
    conflict_data = {
        'mrn': '123456',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'dob': date(1990, 1, 1),       # 不同 DOB
    }
    with pytest.raises(WarningException) as exc_info:
        check_patient(conflict_data)

    assert exc_info.value.code == 'PATIENT_DUPLICATE_WARNING'


# ────────────────────────────────────────────
# 场景 5: 名字+DOB 相同 + MRN 不同 → Warning
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_name_dob_different_mrn_raises_warning(existing_patient):
    """名字和 DOB 都匹配但 MRN 不同，可能是同一个人"""
    conflict_data = {
        'mrn': '999999',               # 不同 MRN
        'first_name': 'Jane',          # 同名字
        'last_name': 'Doe',
        'dob': date(1979, 6, 8),       # 同 DOB
    }
    with pytest.raises(WarningException) as exc_info:
        check_patient(conflict_data)

    assert exc_info.value.code == 'PATIENT_DUPLICATE_WARNING'
    assert '999999' in exc_info.value.detail[0]


# ────────────────────────────────────────────
# 场景 6: 有 Warning 但 confirm=True → 跳过
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_warning_skipped_with_confirm(existing_patient):
    """同样的冲突数据，但 confirm=True 时不应该 raise"""
    conflict_data = {
        'mrn': '123456',
        'first_name': 'John',          # 不同名字（正常会触发 warning）
        'last_name': 'Smith',
        'dob': date(1979, 6, 8),
    }
    # confirm=True → 不 raise，返回 None
    result = check_patient(conflict_data, confirm=True)
    assert result is None


# ────────────────────────────────────────────
# 场景 7: MRN 冲突 + 名字+DOB 冲突同时存在
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_multiple_warnings_collected(existing_patient):
    """
    如果 MRN 冲突和名字+DOB 冲突同时触发，
    detail 应该包含多条警告信息
    """
    # 先创建另一个患者，名字+DOB 和提交的一样但 MRN 不同
    Patient.objects.create(
        first_name='Bob',
        last_name='Wilson',
        mrn='888888',
        dob=date(1985, 3, 15),
    )

    # 提交的数据：MRN 匹配 existing_patient（但名字不同），
    # 名字+DOB 匹配 bob（但 MRN 不同）
    conflict_data = {
        'mrn': '123456',                # 匹配 existing_patient 的 MRN
        'first_name': 'Bob',            # 不是 existing_patient 的名字
        'last_name': 'Wilson',
        'dob': date(1985, 3, 15),       # 不是 existing_patient 的 DOB
    }

    with pytest.raises(WarningException) as exc_info:
        check_patient(conflict_data)

    # 应该有两条 warning：MRN 冲突 + 名字 DOB 冲突
    assert len(exc_info.value.detail) == 2


# ────────────────────────────────────────────
# 场景 8: 完全不相关的患者 → 无冲突
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_completely_different_patient_no_conflict(existing_patient):
    """MRN 不同、名字不同、DOB 不同 → 没有冲突"""
    new_data = {
        'mrn': '999999',
        'first_name': 'Alice',
        'last_name': 'Wang',
        'dob': date(2000, 12, 25),
    }
    result = check_patient(new_data)
    assert result is None
