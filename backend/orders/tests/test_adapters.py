# orders/tests/test_adapters.py
"""
Adapter Unit Tests
==================
测试每个 adapter 的 parse() → transform() → validate() 流程
不需要数据库，不需要 HTTP 请求，纯 Python 函数测试

测试策略：
1. 每个 adapter 测 happy path（正常数据能正确转换）
2. 每个 adapter 测 edge cases（缺字段、格式错误）
3. 测 BaseIntakeAdapter 的 validate() 拦截能力
4. 测 get_adapter() 工厂函数
"""

import pytest
from orders.adapters.base import (
    BaseIntakeAdapter, InternalOrder, InternalPatient, InternalProvider, AdapterError
)
from orders.adapters.cvs_web import CvsWebAdapter
from orders.adapters.clinic_b import ClinicBAdapter
from orders.adapters.pharmacorp import PharmaCorpAdapter
from orders.adapters.nordic import NordicHealthAdapter
from orders.adapters import get_adapter


# ============================================================
# 测试数据 Fixtures
# ============================================================

@pytest.fixture
def cvs_web_data():
    """CVS web form 标准格式"""
    return {
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
        "additional_diagnoses": ["I10", "K21.0"],
        "medication_history": ["Pyridostigmine 60mg"],
        "patient_records": "Progressive weakness noted",
        "confirm": False,
    }


@pytest.fixture
def clinic_b_data():
    """Clinic B 扁平 JSON 格式"""
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


@pytest.fixture
def pharmacorp_xml():
    """PharmaCorp XML 格式"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<PharmacyOrder>
  <Patient>
    <GivenName>James</GivenName>
    <SurName>Wilson</SurName>
    <MedRecordNum>112233</MedRecordNum>
    <DateOfBirth>11-20-1990</DateOfBirth>
  </Patient>
  <Prescriber>
    <FullName>Dr. Rachel Kim</FullName>
    <NationalProviderId>5566778899</NationalProviderId>
  </Prescriber>
  <ClinicalInfo>
    <DrugName>Ocrevus</DrugName>
    <PrimaryDiagCode>G35</PrimaryDiagCode>
  </ClinicalInfo>
  <OtherDiagCodes>
    <Code>I10</Code>
    <Code>E11.9</Code>
  </OtherDiagCodes>
</PharmacyOrder>"""


@pytest.fixture
def nordic_text():
    """Nordic Health 纯文本竖线分隔格式"""
    return (
        "PATIENT|Sven|Svensson|889900|1985-12-31\n"
        "DOCTOR|Dr. Erik|7788990011\n"
        "ORDER|Ibuprofen|M10.9|M12.0;M15.3|CONFIRMED\n"
    )


# ============================================================
# get_adapter() 工厂函数测试
# ============================================================

class TestGetAdapter:
    """测试工厂函数能正确返回 adapter 实例"""

    def test_returns_cvs_web_adapter(self):
        adapter = get_adapter("cvs_web")
        assert isinstance(adapter, CvsWebAdapter)

    def test_returns_clinic_b_adapter(self):
        adapter = get_adapter("clinic_b")
        assert isinstance(adapter, ClinicBAdapter)

    def test_returns_pharmacorp_adapter(self):
        adapter = get_adapter("pharmacorp")
        assert isinstance(adapter, PharmaCorpAdapter)

    def test_returns_nordic_adapter(self):
        adapter = get_adapter("nordic")
        assert isinstance(adapter, NordicHealthAdapter)

    def test_unknown_source_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown source"):
            get_adapter("nonexistent_hospital")

    def test_empty_source_raises_value_error(self):
        with pytest.raises(ValueError):
            get_adapter("")


# ============================================================
# CvsWebAdapter 测试
# ============================================================

class TestCvsWebAdapter:
    """CVS web form adapter — 数据已经是标准格式，基本上是透传"""

    def test_happy_path(self, cvs_web_data):
        adapter = CvsWebAdapter()
        result = adapter.process(cvs_web_data)

        assert isinstance(result, InternalOrder)
        assert result.patient.first_name == "Jane"
        assert result.patient.last_name == "Doe"
        assert result.patient.mrn == "123456"
        assert result.patient.dob == "1979-06-08"
        assert result.provider.name == "Dr. Smith"
        assert result.provider.npi == "1234567890"
        assert result.medication_name == "IVIG"
        assert result.primary_diagnosis == "G70.01"
        assert result.additional_diagnoses == ["I10", "K21.0"]
        assert result.medication_history == ["Pyridostigmine 60mg"]
        assert result.patient_records == "Progressive weakness noted"
        assert result.confirm is False

    def test_preserves_raw_data(self, cvs_web_data):
        """验证原始数据被保留用于排查"""
        adapter = CvsWebAdapter()
        adapter.process(cvs_web_data)
        assert adapter.raw_data == cvs_web_data

    def test_missing_optional_fields_default_to_empty(self):
        """只有必填字段，可选字段应该有默认值"""
        minimal_data = {
            "patient": {"first_name": "Jane", "last_name": "Doe", "mrn": "123456", "dob": "1979-06-08"},
            "provider": {"name": "Dr. Smith", "npi": "1234567890"},
            "medication_name": "IVIG",
            "primary_diagnosis": "G70.01",
        }
        adapter = CvsWebAdapter()
        result = adapter.process(minimal_data)

        assert result.additional_diagnoses == []
        assert result.medication_history == []
        assert result.patient_records == ""
        assert result.confirm is False

    def test_confirm_flag_preserved(self, cvs_web_data):
        """confirm=True 应该被正确传递"""
        cvs_web_data["confirm"] = True
        adapter = CvsWebAdapter()
        result = adapter.process(cvs_web_data)
        assert result.confirm is True

    def test_missing_patient_mrn_raises_adapter_error(self):
        """缺少 MRN → validate() 应该拦住"""
        data = {
            "patient": {"first_name": "Jane", "last_name": "Doe", "mrn": "", "dob": "1979-06-08"},
            "provider": {"name": "Dr. Smith", "npi": "1234567890"},
            "medication_name": "IVIG",
            "primary_diagnosis": "G70.01",
        }
        adapter = CvsWebAdapter()
        with pytest.raises(AdapterError, match="mrn"):
            adapter.process(data)


# ============================================================
# ClinicBAdapter 测试
# ============================================================

class TestClinicBAdapter:
    """Clinic B adapter — 扁平 JSON，字段名映射"""

    def test_happy_path(self, clinic_b_data):
        adapter = ClinicBAdapter()
        result = adapter.process(clinic_b_data)

        assert isinstance(result, InternalOrder)
        assert result.patient.first_name == "Maria"
        assert result.patient.last_name == "Garcia"
        assert result.patient.mrn == "654321"
        assert result.patient.dob == "1990-03-15"
        assert result.provider.name == "Dr. Lee"
        assert result.provider.npi == "9876543210"
        assert result.medication_name == "Humira"
        assert result.primary_diagnosis == "L40.0"

    def test_medication_history_split(self, clinic_b_data):
        """逗号分隔的 past_meds 应该被拆成列表"""
        adapter = ClinicBAdapter()
        result = adapter.process(clinic_b_data)
        assert result.medication_history == ["Methotrexate 15mg", "Prednisone 5mg"]

    def test_empty_past_meds(self, clinic_b_data):
        """past_meds 为空字符串时应该返回空列表"""
        clinic_b_data["past_meds"] = ""
        adapter = ClinicBAdapter()
        result = adapter.process(clinic_b_data)
        assert result.medication_history == []

    def test_no_past_meds_key(self, clinic_b_data):
        """没有 past_meds 字段时应该返回空列表"""
        del clinic_b_data["past_meds"]
        adapter = ClinicBAdapter()
        result = adapter.process(clinic_b_data)
        assert result.medication_history == []

    def test_confirm_flag_mapping(self, clinic_b_data):
        """is_confirmed 应该映射到 confirm"""
        clinic_b_data["is_confirmed"] = True
        adapter = ClinicBAdapter()
        result = adapter.process(clinic_b_data)
        assert result.confirm is True

    def test_non_dict_input_raises_adapter_error(self):
        """传入非 dict 应该在 parse() 阶段报错"""
        adapter = ClinicBAdapter()
        with pytest.raises(AdapterError, match="Json dictionary"):
            adapter.process("this is not json")

    def test_missing_required_field_raises_adapter_error(self):
        """缺少必填字段 → validate() 拦截"""
        data = {
            "pt_fname": "Maria",
            "pt_lname": "Garcia",
            "pt_id_num": "",       # MRN 为空
            "birth_date": "1990-03-15",
            "doc_name": "Dr. Lee",
            "doc_npi": "9876543210",
            "drug": "Humira",
            "main_icd10": "L40.0",
        }
        adapter = ClinicBAdapter()
        with pytest.raises(AdapterError, match="mrn"):
            adapter.process(data)

    def test_preserves_raw_data(self, clinic_b_data):
        adapter = ClinicBAdapter()
        adapter.process(clinic_b_data)
        assert adapter.raw_data == clinic_b_data


# ============================================================
# PharmaCorpAdapter 测试
# ============================================================

class TestPharmaCorpAdapter:
    """PharmaCorp adapter — XML 解析"""

    def test_happy_path(self, pharmacorp_xml):
        adapter = PharmaCorpAdapter()
        result = adapter.process(pharmacorp_xml)

        assert isinstance(result, InternalOrder)
        assert result.patient.first_name == "James"
        assert result.patient.last_name == "Wilson"
        assert result.patient.mrn == "112233"
        assert result.provider.name == "Dr. Rachel Kim"
        assert result.provider.npi == "5566778899"
        assert result.medication_name == "Ocrevus"
        assert result.primary_diagnosis == "G35"

    def test_date_format_conversion(self, pharmacorp_xml):
        """美国日期 MM-DD-YYYY → 标准 YYYY-MM-DD"""
        adapter = PharmaCorpAdapter()
        result = adapter.process(pharmacorp_xml)
        assert result.patient.dob == "1990-11-20"

    def test_additional_diagnoses_parsed(self, pharmacorp_xml):
        """多个 <Code> 节点应该变成列表"""
        adapter = PharmaCorpAdapter()
        result = adapter.process(pharmacorp_xml)
        assert result.additional_diagnoses == ["I10", "E11.9"]

    def test_bytes_input_accepted(self, pharmacorp_xml):
        """bytes 类型的输入也应该能处理"""
        adapter = PharmaCorpAdapter()
        result = adapter.process(pharmacorp_xml.encode('utf-8'))
        assert result.patient.first_name == "James"

    def test_invalid_xml_raises_adapter_error(self):
        """无效 XML 应该在 parse() 阶段报错"""
        adapter = PharmaCorpAdapter()
        with pytest.raises(AdapterError, match="valid XML"):
            adapter.process("<broken><xml")

    def test_missing_patient_name_raises_adapter_error(self):
        """缺少 patient name → validate() 拦截"""
        xml = """<?xml version="1.0"?>
<PharmacyOrder>
  <Patient>
    <GivenName></GivenName>
    <SurName>Wilson</SurName>
    <MedRecordNum>112233</MedRecordNum>
    <DateOfBirth>11-20-1990</DateOfBirth>
  </Patient>
  <Prescriber>
    <FullName>Dr. Kim</FullName>
    <NationalProviderId>5566778899</NationalProviderId>
  </Prescriber>
  <ClinicalInfo>
    <DrugName>Ocrevus</DrugName>
    <PrimaryDiagCode>G35</PrimaryDiagCode>
  </ClinicalInfo>
</PharmacyOrder>"""
        adapter = PharmaCorpAdapter()
        with pytest.raises(AdapterError, match="first_name"):
            adapter.process(xml)

    def test_no_additional_diagnoses(self):
        """没有 OtherDiagCodes 节点时应该返回空列表"""
        xml = """<?xml version="1.0"?>
<PharmacyOrder>
  <Patient>
    <GivenName>James</GivenName>
    <SurName>Wilson</SurName>
    <MedRecordNum>112233</MedRecordNum>
    <DateOfBirth>11-20-1990</DateOfBirth>
  </Patient>
  <Prescriber>
    <FullName>Dr. Kim</FullName>
    <NationalProviderId>5566778899</NationalProviderId>
  </Prescriber>
  <ClinicalInfo>
    <DrugName>Ocrevus</DrugName>
    <PrimaryDiagCode>G35</PrimaryDiagCode>
  </ClinicalInfo>
</PharmacyOrder>"""
        adapter = PharmaCorpAdapter()
        result = adapter.process(xml)
        assert result.additional_diagnoses == []

    def test_preserves_raw_data(self, pharmacorp_xml):
        adapter = PharmaCorpAdapter()
        adapter.process(pharmacorp_xml)
        assert adapter.raw_data == pharmacorp_xml

    def test_default_confirm_is_false(self, pharmacorp_xml):
        adapter = PharmaCorpAdapter()
        result = adapter.process(pharmacorp_xml)
        assert result.confirm is False


# ============================================================
# NordicHealthAdapter 测试
# ============================================================

class TestNordicHealthAdapter:
    """Nordic Health adapter — 纯文本竖线分隔"""

    def test_happy_path(self, nordic_text):
        adapter = NordicHealthAdapter()
        result = adapter.process(nordic_text)

        assert isinstance(result, InternalOrder)
        assert result.patient.first_name == "Sven"
        assert result.patient.last_name == "Svensson"
        assert result.patient.mrn == "889900"
        assert result.patient.dob == "1985-12-31"
        assert result.provider.name == "Dr. Erik"
        assert result.provider.npi == "7788990011"
        assert result.medication_name == "Ibuprofen"
        assert result.primary_diagnosis == "M10.9"

    def test_additional_diagnoses_split_by_semicolon(self, nordic_text):
        """分号分隔的副诊断应该变成列表"""
        adapter = NordicHealthAdapter()
        result = adapter.process(nordic_text)
        assert result.additional_diagnoses == ["M12.0", "M15.3"]

    def test_confirmed_flag_parsing(self, nordic_text):
        """CONFIRMED 应该映射为 confirm=True"""
        adapter = NordicHealthAdapter()
        result = adapter.process(nordic_text)
        assert result.confirm is True

    def test_not_confirmed(self):
        """非 CONFIRMED 应该是 False"""
        text = (
            "PATIENT|Sven|Svensson|889900|1985-12-31\n"
            "DOCTOR|Dr. Erik|7788990011\n"
            "ORDER|Ibuprofen|M10.9|M12.0|PENDING\n"
        )
        adapter = NordicHealthAdapter()
        result = adapter.process(text)
        assert result.confirm is False

    def test_bytes_input_accepted(self, nordic_text):
        """bytes 类型的输入也应该能处理"""
        adapter = NordicHealthAdapter()
        result = adapter.process(nordic_text.encode('utf-8'))
        assert result.patient.first_name == "Sven"

    def test_non_string_input_raises_adapter_error(self):
        """传入非 string/bytes 应该在 parse() 阶段报错"""
        adapter = NordicHealthAdapter()
        with pytest.raises(AdapterError, match="string"):
            adapter.process(12345)

    def test_empty_lines_ignored(self):
        """空行应该被忽略"""
        text = (
            "\n\n"
            "PATIENT|Sven|Svensson|889900|1985-12-31\n"
            "\n"
            "DOCTOR|Dr. Erik|7788990011\n"
            "\n\n"
            "ORDER|Ibuprofen|M10.9||CONFIRMED\n"
        )
        adapter = NordicHealthAdapter()
        result = adapter.process(text)
        assert result.patient.first_name == "Sven"

    def test_missing_medication_raises_adapter_error(self):
        """ORDER 行缺失 → medication_name 为空 → validate 拦截"""
        text = (
            "PATIENT|Sven|Svensson|889900|1985-12-31\n"
            "DOCTOR|Dr. Erik|7788990011\n"
        )
        adapter = NordicHealthAdapter()
        with pytest.raises(AdapterError, match="medication_name"):
            adapter.process(text)

    def test_preserves_raw_data(self, nordic_text):
        adapter = NordicHealthAdapter()
        adapter.process(nordic_text)
        assert adapter.raw_data == nordic_text

    def test_date_slash_to_dash_conversion(self):
        """1985/12/31 应该被转成 1985-12-31"""
        text = (
            "PATIENT|Sven|Svensson|889900|1985/12/31\n"
            "DOCTOR|Dr. Erik|7788990011\n"
            "ORDER|Ibuprofen|M10.9||CONFIRMED\n"
        )
        adapter = NordicHealthAdapter()
        result = adapter.process(text)
        assert result.patient.dob == "1985-12-31"


# ============================================================
# InternalOrder.to_dict() 测试
# ============================================================

class TestInternalOrderToDict:
    """测试 dataclass → dict 转换"""

    def test_to_dict_produces_nested_structure(self):
        order = InternalOrder(
            patient=InternalPatient(first_name="Jane", last_name="Doe", mrn="123456", dob="1979-06-08"),
            provider=InternalProvider(name="Dr. Smith", npi="1234567890"),
            medication_name="IVIG",
            primary_diagnosis="G70.01",
        )
        d = order.to_dict()

        assert d["patient"]["first_name"] == "Jane"
        assert d["patient"]["mrn"] == "123456"
        assert d["provider"]["npi"] == "1234567890"
        assert d["medication_name"] == "IVIG"

    def test_to_serializer_format_produces_flat_structure(self):
        """to_serializer_format() 应该输出 serializer 期望的扁平 key"""
        order = InternalOrder(
            patient=InternalPatient(first_name="Jane", last_name="Doe", mrn="123456", dob="1979-06-08"),
            provider=InternalProvider(name="Dr. Smith", npi="1234567890"),
            medication_name="IVIG",
            primary_diagnosis="G70.01",
            additional_diagnoses=["I10"],
            medication_history=["Aspirin"],
            patient_records="Some notes",
        )
        flat = order.to_serializer_format()

        # 验证 key 是 serializer 期望的扁平格式
        assert flat["patient_first_name"] == "Jane"
        assert flat["patient_last_name"] == "Doe"
        assert flat["patient_mrn"] == "123456"
        assert flat["patient_dob"] == "1979-06-08"
        assert flat["provider_name"] == "Dr. Smith"
        assert flat["provider_npi"] == "1234567890"
        assert flat["medication_name"] == "IVIG"
        assert flat["primary_diagnosis"] == "G70.01"
        assert flat["additional_diagnoses"] == ["I10"]
        assert flat["medication_history"] == ["Aspirin"]
        assert flat["patient_records"] == "Some notes"
        # confirm 不应该出现在 serializer 格式里
        assert "confirm" not in flat


# ============================================================
# BaseIntakeAdapter.validate() 测试
# ============================================================

class TestBaseAdapterValidation:
    """测试基类的 validate() 拦截缺失字段"""

    def _make_order(self, **overrides):
        """辅助方法：创建默认 InternalOrder，允许覆盖任意字段"""
        defaults = {
            "patient": InternalPatient(first_name="Jane", last_name="Doe", mrn="123456", dob="1979-06-08"),
            "provider": InternalProvider(name="Dr. Smith", npi="1234567890"),
            "medication_name": "IVIG",
            "primary_diagnosis": "G70.01",
        }
        defaults.update(overrides)
        return InternalOrder(**defaults)

    def test_valid_order_passes(self):
        """完整的 order 应该通过验证"""
        adapter = CvsWebAdapter()  # 用任意具体子类来测基类的 validate
        order = self._make_order()
        adapter.validate(order)  # 不应该 raise

    def test_empty_first_name_raises(self):
        adapter = CvsWebAdapter()
        order = self._make_order(
            patient=InternalPatient(first_name="", last_name="Doe", mrn="123456", dob="1979-06-08")
        )
        with pytest.raises(AdapterError, match="first_name"):
            adapter.validate(order)

    def test_empty_mrn_raises(self):
        adapter = CvsWebAdapter()
        order = self._make_order(
            patient=InternalPatient(first_name="Jane", last_name="Doe", mrn="", dob="1979-06-08")
        )
        with pytest.raises(AdapterError, match="mrn"):
            adapter.validate(order)

    def test_empty_npi_raises(self):
        adapter = CvsWebAdapter()
        order = self._make_order(
            provider=InternalProvider(name="Dr. Smith", npi="")
        )
        with pytest.raises(AdapterError, match="npi"):
            adapter.validate(order)

    def test_empty_medication_raises(self):
        adapter = CvsWebAdapter()
        order = self._make_order(medication_name="")
        with pytest.raises(AdapterError, match="medication_name"):
            adapter.validate(order)
