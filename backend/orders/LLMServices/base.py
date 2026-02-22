from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    
    def generate_care_plan(self, order) -> str:
        prompt = self._build_prompt(order)
        return self._call_api(prompt)
    
    def _build_prompt(self, order) -> str:
        """调用 Google Gemini API 生成 Care Plan（同步）"""
        prompt = f"""You are a clinical pharmacist creating a care plan for a specialty pharmacy patient.

    Patient Information:
    - Name: {order.patient.first_name} {order.patient.last_name}
    - Date of Birth: {order.patient.dob}
    - MRN: {order.patient.mrn}

    Provider: {order.provider.name} (NPI: {order.provider.npi})

    Medication: {order.medication_name}
    Primary Diagnosis (ICD-10): {order.primary_diagnosis}
    Additional Diagnoses: {', '.join(order.additional_diagnoses) if order.additional_diagnoses else 'None'}
    Medication History: {', '.join(order.medication_history) if order.medication_history else 'None'}
    Patient Records/Notes: {order.patient_records if order.patient_records else 'None provided'}

    Please generate a comprehensive pharmaceutical care plan with EXACTLY these four sections:

    1. **Problem List / Drug Therapy Problems (DTPs)**
    - Identify potential drug therapy problems related to the prescribed medication and diagnoses

    2. **Goals (SMART format)**
    - Specific, Measurable, Achievable, Relevant, Time-bound goals for this patient

    3. **Pharmacist Interventions / Plan**
    - Specific actions the pharmacist should take
    - Patient education points
    - Coordination with the prescribing provider

    4. **Monitoring Plan & Lab Schedule**
    - Labs to monitor and frequency
    - Clinical parameters to track
    - Follow-up schedule

    Be specific and clinically relevant to the medication and diagnoses provided."""
        
        return prompt


    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        # 每个子类必须实现自己的 API 调用
        pass