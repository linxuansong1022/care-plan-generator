"""
LLM prompts for care plan generation.
"""

CARE_PLAN_SYSTEM_PROMPT = """You are a clinical pharmacist assistant. Your task is to generate a comprehensive pharmacist care plan based on the patient records provided.

## INPUT
You will receive patient information that may include:
- Patient Demographics (Name, MRN, DOB, Sex, Weight, Allergies)
- Medication
- Primary diagnosis
- Secondary diagnoses
- Home meds
- Recent history
- Clinical Notes (e.g., Baseline clinic note, Infusion visit note, Follow-up notes)

Note: The input format may vary. Extract relevant information from whatever format is provided.

## OUTPUT
Generate a care plan that MUST include the following sections:

1. Problem list / Drug therapy problems (DTPs)
2. Goals (SMART)
3. Pharmacist interventions / plan
4. Monitoring plan & lab schedule

Base your recommendations on the patient's actual data provided.
"""

CARE_PLAN_USER_PROMPT_TEMPLATE = """Please generate a pharmacist care plan for the following patient:

{patient_records}
"""


def build_care_plan_prompt(
    first_name: str,
    last_name: str,
    mrn: str,
    dob: str,
    sex: str,
    weight_kg: float,
    allergies: str,
    primary_diagnosis_code: str,
    primary_diagnosis_description: str,
    additional_diagnoses: list,
    medication_name: str,
    medication_history: list,
    patient_records: str,
) -> str:
    """Build the user prompt for care plan generation.

    Assembles all patient data into a structured format for the LLM.
    """

    # Build patient records string with all available data
    sections = []

    # Patient Demographics
    sections.append("## PATIENT DEMOGRAPHICS")
    sections.append(f"- Name: {first_name} {last_name}")
    sections.append(f"- MRN: {mrn}")
    sections.append(f"- DOB: {dob or 'Not provided'}")
    sections.append(f"- Sex: {sex or 'Not provided'}")
    sections.append(f"- Weight: {weight_kg} kg" if weight_kg else "- Weight: Not provided")
    sections.append(f"- Allergies: {allergies or 'None known'}")

    # Medication (current order)
    sections.append("")
    sections.append("## MEDICATION")
    sections.append(f"- Current Medication Order: {medication_name}")

    # Diagnoses
    sections.append("")
    sections.append("## DIAGNOSES")
    sections.append(f"- Primary Diagnosis: {primary_diagnosis_code}")
    if primary_diagnosis_description:
        sections.append(f"  ({primary_diagnosis_description})")

    if additional_diagnoses:
        sections.append("- Secondary Diagnoses:")
        for dx in additional_diagnoses:
            sections.append(f"  - {dx}")

    # Home meds / Medication History
    sections.append("")
    sections.append("## HOME MEDS")
    if medication_history:
        for med in medication_history:
            sections.append(f"- {med}")
    else:
        sections.append("- None documented")

    # Clinical Notes
    sections.append("")
    sections.append("## CLINICAL NOTES")
    sections.append(patient_records)

    # Combine all sections
    combined_records = "\n".join(sections)

    return CARE_PLAN_USER_PROMPT_TEMPLATE.format(patient_records=combined_records)
