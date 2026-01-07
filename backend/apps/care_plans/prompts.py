"""
LLM prompts for care plan generation.
"""

CARE_PLAN_SYSTEM_PROMPT = """You are an expert clinical pharmacist assistant specializing in creating comprehensive care plans for specialty pharmacy patients.

Your role is to analyze patient records and generate structured pharmacist care plans that follow evidence-based guidelines and best practices.

## Your Expertise Includes:
- Drug therapy problem identification
- SMART goal setting
- Pharmacist intervention planning
- Medication monitoring and safety
- Patient education strategies
- HIPAA-compliant documentation

## Output Requirements:
1. Generate care plans in a structured, professional format
2. Use clinical terminology appropriately
3. Include specific, actionable interventions
4. Reference current guidelines where applicable
5. Always prioritize patient safety
6. Be thorough but concise

## Important:
- Do not make up information not present in the patient records
- If information is missing, note what additional data would be helpful
- Always include monitoring parameters and follow-up recommendations
"""

CARE_PLAN_USER_PROMPT_TEMPLATE = """Generate a comprehensive pharmacist care plan based on the following patient information:

## PATIENT INFORMATION
- **Name**: {first_name} {last_name}
- **MRN**: {mrn}
- **Date of Birth**: {dob}
- **Sex**: {sex}
- **Weight**: {weight_kg} kg
- **Allergies**: {allergies}

## DIAGNOSIS
- **Primary Diagnosis**: {primary_diagnosis_code} - {primary_diagnosis_description}
- **Additional Diagnoses**: {additional_diagnoses}

## MEDICATION
- **Current Medication Order**: {medication_name}
- **Medication History**: {medication_history}

## CLINICAL RECORDS
{patient_records}

---

## REQUIRED OUTPUT STRUCTURE

Please generate a care plan with the following sections:

### 1. PROBLEM LIST / DRUG THERAPY PROBLEMS (DTPs)
Identify all relevant drug therapy problems including:
- Indication issues
- Efficacy concerns
- Safety risks
- Adherence barriers
- Drug interactions
- Cost/access issues

### 2. GOALS (SMART Format)
For each problem, specify:
- Specific: What exactly will be achieved
- Measurable: How progress will be tracked
- Achievable: Realistic given patient factors
- Relevant: Connected to patient's condition
- Time-bound: Expected timeline

### 3. PHARMACIST INTERVENTIONS / PLAN
Include detailed interventions for:
- Dosing & Administration
- Premedication (if applicable)
- Infusion rates & titration (if applicable)
- Hydration & organ protection
- Risk mitigation strategies
- Concomitant medications management
- Monitoring during therapy
- Adverse event management protocols
- Documentation & communication requirements

### 4. MONITORING PLAN & LAB SCHEDULE
Specify:
- Baseline labs required
- Monitoring frequency
- Parameters to track
- Follow-up schedule
- Red flags requiring immediate action

### 5. PATIENT EDUCATION POINTS
Key information for patient/caregiver including:
- Medication purpose and expectations
- Administration instructions
- Side effects to watch for
- When to seek medical attention
- Lifestyle considerations

---

Generate the care plan now, ensuring it is thorough, evidence-based, and specific to this patient's situation.
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
    """Build the user prompt for care plan generation."""
    
    # Format additional diagnoses
    if additional_diagnoses:
        additional_dx = "\n".join([f"  - {dx}" for dx in additional_diagnoses])
    else:
        additional_dx = "None documented"
    
    # Format medication history
    if medication_history:
        med_history = "\n".join([f"  - {med}" for med in medication_history])
    else:
        med_history = "None documented"
    
    return CARE_PLAN_USER_PROMPT_TEMPLATE.format(
        first_name=first_name,
        last_name=last_name,
        mrn=mrn,
        dob=dob or "Not provided",
        sex=sex or "Not provided",
        weight_kg=weight_kg or "Not provided",
        allergies=allergies or "None known",
        primary_diagnosis_code=primary_diagnosis_code,
        primary_diagnosis_description=primary_diagnosis_description or "",
        additional_diagnoses=additional_dx,
        medication_name=medication_name,
        medication_history=med_history,
        patient_records=patient_records,
    )
