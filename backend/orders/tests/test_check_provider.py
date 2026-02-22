"""
test_check_provider.py — Provider 重复检测 Unit Test
====================================================
测试 services.check_provider() 的所有场景
"""
import pytest
from orders.services import check_provider
from orders.exceptions import BlockError
from orders.models import Provider


# ────────────────────────────────────────────
# 场景 1: 全新 NPI → 返回 None，可以创建
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_new_npi_returns_none(sample_provider_data):
    """全新的 NPI，数据库里不存在，应该返回 None"""
    result = check_provider(sample_provider_data)
    assert result is None


# ────────────────────────────────────────────
# 场景 2: NPI 相同 + 名字相同 → 返回已有实例（复用）
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_npi_same_name_returns_existing(existing_provider, sample_provider_data):
    """NPI 和名字都匹配，应该返回已有的 Provider 实例"""
    result = check_provider(sample_provider_data)
    assert result is not None
    assert result.pk == existing_provider.pk
    assert result.name == 'Dr. Sarah Johnson'


# ────────────────────────────────────────────
# 场景 3: NPI 相同 + 名字不同 → raise BlockError
# ────────────────────────────────────────────
@pytest.mark.django_db
def test_same_npi_different_name_raises_block(existing_provider):
    """NPI 已存在但名字不同，应该 raise BlockError"""
    conflict_data = {
        'npi': '1234567890',        # 同一个 NPI
        'name': 'Dr. Michael Lee',  # 不同的名字
    }
    with pytest.raises(BlockError) as exc_info:
        check_provider(conflict_data)

    # 验证异常的内容
    assert exc_info.value.code == 'PROVIDER_NPI_CONFLICT'
    assert '1234567890' in exc_info.value.detail[0]
    assert 'Dr. Sarah Johnson' in exc_info.value.detail[0]
