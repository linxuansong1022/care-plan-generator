"""
LLM prompts for care plan generation.

Note: The system prompt is now dynamically generated based on recent care plans.
See skeleton_analyzer.py for the dynamic system prompt generation.
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
