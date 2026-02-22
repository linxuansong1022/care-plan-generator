from .base import BaseIntakeAdapter, InternalOrder, InternalPatient, InternalProvider, AdapterError

class ClinicBAdapter(BaseIntakeAdapter):
    def parse(self,raw_data):
        if not isinstance(raw_data,dict):
            raise AdapterError("Clinic B source must be a valid Json dictionary.")
        return raw_data

    def transform(self, parsed_data: dict) -> InternalOrder:
        # 1. 把他们用逗号分隔的 "past_meds" ("Aspirin, Tylenol") 变成 ["Aspirin", "Tylenol"]
        raw_meds = parsed_data.get("past_meds", "")
        med_history_list = [med.strip() for med in raw_meds.split(',')] if raw_meds else []
        
        # 2. 像套娃一样，把字典里的数据一件件装进我们规定的神圣公文包
        return InternalOrder(
            patient=InternalPatient(
                first_name=parsed_data.get("pt_fname", ""),
                last_name=parsed_data.get("pt_lname", ""),
                mrn=parsed_data.get("pt_id_num", ""),
                dob=parsed_data.get("birth_date", "")
            ),
            provider=InternalProvider(
                name=parsed_data.get("doc_name", ""),
                npi=parsed_data.get("doc_npi", "")
            ),
            medication_name=parsed_data.get("drug", ""),
            primary_diagnosis=parsed_data.get("main_icd10", ""),
            additional_diagnoses=[],  # Clinic B 发来的数据里没有这俩项，所以我们给空值
            patient_records="",       # 同上
            medication_history=med_history_list,  # 👈 这里接上我们第一步里拆开的列表！
            confirm=parsed_data.get("is_confirmed", False)  # 👈 注意！他家传的字典键名叫 "is_confirmed"
        )
