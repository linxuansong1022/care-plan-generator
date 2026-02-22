# adapters/cvs_web.py
from .base import BaseIntakeAdapter, InternalOrder, InternalPatient, InternalProvider

class CvsWebAdapter(BaseIntakeAdapter):
    """CVS 内部 web form — 数据格式已经是标准格式"""
    
    def parse(self, raw_data):
        # DRF 已经把 JSON 解析成 dict 了
        return raw_data
    
    def transform(self, parsed_data: dict) -> InternalOrder:
        p = parsed_data.get("patient", {})
        prov = parsed_data.get("provider", {})
        return InternalOrder(
            patient=InternalPatient(
                first_name=p.get("first_name", ""),
                last_name=p.get("last_name", ""),
                mrn=p.get("mrn", ""),
                dob=p.get("dob", ""),
            ),
            provider=InternalProvider(
                name=prov.get("name", ""),
                npi=prov.get("npi", ""),
            ),
            medication_name=parsed_data.get("medication_name", ""),
            primary_diagnosis=parsed_data.get("primary_diagnosis", ""),
            additional_diagnoses=parsed_data.get("additional_diagnoses", []),
            medication_history=parsed_data.get("medication_history", []),
            patient_records=parsed_data.get("patient_records", ""),
            confirm=parsed_data.get("confirm", False),
        )