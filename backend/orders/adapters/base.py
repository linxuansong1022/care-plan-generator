from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import date


# ===== 内部标准格式 =====

@dataclass
class InternalPatient:
    first_name: str
    last_name: str
    mrn: str
    dob: str                    # "YYYY-MM-DD" 字符串，因为 serializer 期望字符串再自己转

@dataclass
class InternalProvider:
    name: str
    npi: str

@dataclass
class InternalOrder:
    patient: InternalPatient
    provider: InternalProvider
    medication_name: str
    primary_diagnosis: str
    additional_diagnoses: List[str] = field(default_factory=list)
    medication_history: List[str] = field(default_factory=list)
    patient_records: str = ""
    confirm: bool = False       # Day 8 的 confirm 机制
    
    def to_dict(self) -> dict:
        """转成 serializer 期望的嵌套 dict 格式"""
        return asdict(self)
    
    def to_serializer_format(self) -> dict:
        """拍平成 serializer 期望的格式（给验证用）"""
        return {
            "patient_first_name": self.patient.first_name,
            "patient_last_name": self.patient.last_name,
            "patient_mrn": self.patient.mrn,
            "patient_dob": self.patient.dob,
            "provider_name": self.provider.name,
            "provider_npi": self.provider.npi,
            "medication_name": self.medication_name,
            "primary_diagnosis": self.primary_diagnosis,
            "additional_diagnoses": self.additional_diagnoses,
            "medication_history": self.medication_history,
            "patient_records": self.patient_records,
        }


# ===== 适配器基类 =====

class AdapterError(Exception):
    """adapter 阶段的错误，区别于业务层的 BlockError/WarningException"""
    pass


class BaseIntakeAdapter(ABC):
    
    def __init__(self):
        self.raw_data = None      # 保留原始数据，出问题时可以排查
    
    @abstractmethod
    def parse(self, raw_data) -> dict:
        """把原始输入解析成 Python 数据结构
        
        JSON 数据源：可能直接就是 dict（DRF 已解析）
        XML 数据源：需要手动解析
        """
        pass
    
    @abstractmethod
    def transform(self, parsed_data: dict) -> InternalOrder:
        """把解析后的数据映射成 InternalOrder
        
        这是每个 adapter 的核心工作：
        - 字段名映射（fname → first_name）
        - 格式转换（06/08/1979 → 1979-06-08）
        - 结构转换（扁平 → 嵌套）
        """
        pass
    
    def validate(self, order: InternalOrder) -> None:
        """验证转换后的数据是否完整
        
        注意：这不是业务验证（那是 serializer 和 service 的活）
        这只检查 adapter 转换有没有漏字段
        """
        if not order.patient.first_name:
            raise AdapterError("patient.first_name is missing after transform")
        if not order.patient.mrn:
            raise AdapterError("patient.mrn is missing after transform")
        if not order.provider.npi:
            raise AdapterError("provider.npi is missing after transform")
        if not order.medication_name:
            raise AdapterError("medication_name is missing after transform")
    
    def process(self, raw_data) -> InternalOrder:
        """模板方法：parse → transform → validate
        
        子类不要覆盖这个方法，只实现 parse 和 transform
        """
        self.raw_data = raw_data
        parsed = self.parse(raw_data)
        order = self.transform(parsed)
        self.validate(order)
        return order