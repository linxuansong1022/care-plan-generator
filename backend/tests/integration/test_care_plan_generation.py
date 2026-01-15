"""
Integration tests for Care Plan generation with real LLM.

These tests verify that the LLM output follows the required template structure.
Mark with @pytest.mark.integration to skip in unit test runs.
"""

import pytest
import re
from django.conf import settings

from apps.care_plans.prompts import build_care_plan_prompt
from apps.care_plans.llm_service import get_llm_service, ClaudeLLMService, OpenAILLMService
from apps.care_plans.skeleton_analyzer import get_dynamic_skeleton, build_dynamic_system_prompt


# Example patient records from the specification
EXAMPLE_PATIENT_RECORDS = """Name: A.B. (Fictional)
MRN: 00012345 (fictional)
DOB: 1979-06-08 (Age 46)
Sex: Female
Weight: 72 kg
Allergies: None known to medications (no IgA deficiency)
Medication: IVIG

Primary diagnosis: Generalized myasthenia gravis (AChR antibody positive), MGFA class IIb
Secondary diagnoses: Hypertension (well controlled), GERD
Home meds:
- Pyridostigmine 60 mg PO q6h PRN (current avg 3–4 doses/day)
- Prednisone 10 mg PO daily
- Lisinopril 10 mg PO daily
- Omeprazole 20 mg PO daily

Recent history:
- Progressive proximal muscle weakness and ptosis over 2 weeks with worsening speech and swallowing fatigue.
- Neurology recommends IVIG for rapid symptomatic control (planned course prior to planned thymectomy).
- Baseline respiratory status: no stridor; baseline FVC 2.8 L (predicted 4.0 L; ~70% predicted). No current myasthenic crisis but declining strength.

A. Baseline clinic note (pre-infusion)
Date: 2025-10-15
Vitals: BP 128/78, HR 78, RR 16, SpO2 98% RA, Temp 36.7°C
Exam: Ptosis bilateral, fatigable proximal weakness (4/5), speech slurred after repeated counting, no respiratory distress.
Labs: CBC WNL; BMP: Na 138, K 4.1, Cl 101, HCO3 24, BUN 12, SCr 0.78, eGFR >90 mL/min/1.73m².
IgG baseline: 10 g/L (for replacement context; note IVIG for immunomodulation here).
Plan: IVIG 2 g/kg total (144 g for 72 kg) given as 0.4 g/kg/day x 5 days in outpatient infusion center. Premedicate with acetaminophen + diphenhydramine; monitor vitals and FVC daily; continue pyridostigmine and prednisone.

B. Infusion visit note — Day 1
Date: 2025-10-16
IVIG product: Privigen (10% IVIG) — lot #P12345 (fictional)
Dose given: 28.8 g (0.4 g/kg × 72 kg) diluted per manufacturer instructions.
Premeds: Acetaminophen 650 mg PO + Diphenhydramine 25 mg PO 30 minutes pre-infusion.
Infusion start rate: 0.5 mL/kg/hr for first 30 minutes (per institution titration) then increased per tolerance to max manufacturer rate.
Vitals: q15 minutes first hour then q30 minutes; no fever, transient mild headache at 2 hours (resolved after slowing infusion).
Respiratory: FVC 2.7 L (stable).
Disposition: Completed infusion; observed 60 minutes post-infusion; discharged with plan for days 2–5.

C. Follow-up — 2 weeks post-course
Date: 2025-10-30
Clinical status: Subjective improvement in speech and proximal strength; fewer fatigability episodes. No thrombotic events or renal issues reported. Next neurology follow-up in 4 weeks to consider repeat course vs. thymectomy timing.
"""


class TestCarePlanOutputStructure:
    """Test that LLM output contains all required sections."""

    # Required sections from the template
    REQUIRED_SECTIONS = [
        "Problem list",
        "Drug therapy problems",
        "DTP",
        "Goals",
        "SMART",
        "Pharmacist interventions",
        "plan",
        "Monitoring plan",
        "lab schedule",
    ]

    # More specific section patterns (at least one from each group must match)
    SECTION_PATTERNS = [
        # Section 1: Problem list / Drug therapy problems (DTPs)
        [
            r"(?i)problem\s*list",
            r"(?i)drug\s*therapy\s*problem",
            r"(?i)\bDTP",
        ],
        # Section 2: Goals (SMART)
        [
            r"(?i)\bgoals?\b",
            r"(?i)\bSMART\b",
        ],
        # Section 3: Pharmacist interventions / plan
        [
            r"(?i)pharmacist\s*intervention",
            r"(?i)intervention.*plan",
            r"(?i)\bplan\b.*intervention",
        ],
        # Section 4: Monitoring plan & lab schedule
        [
            r"(?i)monitoring\s*plan",
            r"(?i)lab\s*schedule",
            r"(?i)monitoring.*lab",
        ],
    ]

    def _check_section_present(self, content: str, patterns: list) -> tuple[bool, str]:
        """Check if at least one pattern from the list matches."""
        for pattern in patterns:
            if re.search(pattern, content):
                return True, pattern
        return False, None

    def _validate_care_plan_structure(self, content: str) -> dict:
        """
        Validate that the care plan contains all required sections.

        Returns a dict with validation results.
        """
        results = {
            "is_valid": True,
            "sections_found": [],
            "sections_missing": [],
            "content_length": len(content),
        }

        section_names = [
            "Problem list / DTPs",
            "Goals (SMART)",
            "Pharmacist interventions / plan",
            "Monitoring plan & lab schedule",
        ]

        for i, patterns in enumerate(self.SECTION_PATTERNS):
            found, matched_pattern = self._check_section_present(content, patterns)
            if found:
                results["sections_found"].append({
                    "section": section_names[i],
                    "matched_pattern": matched_pattern,
                })
            else:
                results["sections_missing"].append(section_names[i])
                results["is_valid"] = False

        return results

    @pytest.mark.integration
    @pytest.mark.skipif(
        not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY,
        reason="No LLM API key configured"
    )
    def test_care_plan_output_has_all_required_sections(self):
        """
        Integration test: Verify LLM output contains all 4 required sections.

        This test calls the real LLM API and validates the response structure.
        """
        # Build prompt using the example patient records
        prompt = build_care_plan_prompt(
            first_name="A.",
            last_name="B.",
            mrn="00012345",
            dob="1979-06-08",
            sex="Female",
            weight_kg=72.0,
            allergies="None known to medications (no IgA deficiency)",
            primary_diagnosis_code="G70.00",
            primary_diagnosis_description="Generalized myasthenia gravis (AChR antibody positive), MGFA class IIb",
            additional_diagnoses=["I10 - Hypertension", "K21.0 - GERD"],
            medication_name="IVIG",
            medication_history=[
                "Pyridostigmine 60 mg PO q6h PRN",
                "Prednisone 10 mg PO daily",
                "Lisinopril 10 mg PO daily",
                "Omeprazole 20 mg PO daily",
            ],
            patient_records=EXAMPLE_PATIENT_RECORDS,
        )

        # Get LLM service and generate
        llm_service = get_llm_service()

        # Skip if using mock service (no real API key)
        if not isinstance(llm_service, (ClaudeLLMService, OpenAILLMService)):
            pytest.skip("No real LLM API key configured, skipping integration test")

        # Get dynamic system prompt (based on recent care plans or default)
        skeleton = get_dynamic_skeleton(use_llm=False)
        system_prompt = build_dynamic_system_prompt(skeleton)

        response = llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        # Validate the response
        assert response.content, "LLM returned empty content"
        assert len(response.content) > 500, f"Care plan too short: {len(response.content)} chars"

        # Check structure
        validation = self._validate_care_plan_structure(response.content)

        # Assert all sections present
        assert validation["is_valid"], (
            f"Care plan missing required sections: {validation['sections_missing']}\n"
            f"Sections found: {[s['section'] for s in validation['sections_found']]}\n"
            f"Content preview: {response.content[:1000]}..."
        )

        # Log success info
        print(f"\n✅ Care plan validation passed!")
        print(f"   Content length: {validation['content_length']} chars")
        print(f"   Sections found: {[s['section'] for s in validation['sections_found']]}")
        print(f"   Model used: {response.model}")
        print(f"   Tokens: {response.total_tokens}")
        print(f"   Generation time: {response.generation_time_ms}ms")

    @pytest.mark.integration
    @pytest.mark.skipif(
        not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY,
        reason="No LLM API key configured"
    )
    def test_care_plan_contains_patient_specific_content(self):
        """
        Integration test: Verify LLM output references the actual patient data.
        """
        prompt = build_care_plan_prompt(
            first_name="A.",
            last_name="B.",
            mrn="00012345",
            dob="1979-06-08",
            sex="Female",
            weight_kg=72.0,
            allergies="None known to medications (no IgA deficiency)",
            primary_diagnosis_code="G70.00",
            primary_diagnosis_description="Generalized myasthenia gravis",
            additional_diagnoses=["Hypertension", "GERD"],
            medication_name="IVIG",
            medication_history=[
                "Pyridostigmine 60 mg PO q6h PRN",
                "Prednisone 10 mg PO daily",
            ],
            patient_records=EXAMPLE_PATIENT_RECORDS,
        )

        llm_service = get_llm_service()

        if not isinstance(llm_service, (ClaudeLLMService, OpenAILLMService)):
            pytest.skip("No real LLM API key configured")

        # Get dynamic system prompt (based on recent care plans or default)
        skeleton = get_dynamic_skeleton(use_llm=False)
        system_prompt = build_dynamic_system_prompt(skeleton)

        response = llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        content_lower = response.content.lower()

        # Check that patient-specific terms appear in output
        patient_terms = [
            "ivig",
            "myasthenia",
            "pyridostigmine",
            "prednisone",
        ]

        found_terms = [term for term in patient_terms if term in content_lower]

        assert len(found_terms) >= 2, (
            f"Care plan should reference patient-specific medications/conditions. "
            f"Found only: {found_terms}"
        )

        print(f"\n✅ Patient-specific content check passed!")
        print(f"   Found terms: {found_terms}")


class TestBuildCarePlanPrompt:
    """Unit tests for the prompt building function."""

    def test_build_prompt_includes_all_sections(self):
        """Test that built prompt includes all patient data sections."""
        prompt = build_care_plan_prompt(
            first_name="John",
            last_name="Doe",
            mrn="12345678",
            dob="1990-01-15",
            sex="Male",
            weight_kg=75.0,
            allergies="Penicillin",
            primary_diagnosis_code="G70.00",
            primary_diagnosis_description="Myasthenia gravis",
            additional_diagnoses=["I10", "E11.9"],
            medication_name="IVIG",
            medication_history=["Aspirin 81mg daily", "Metformin 500mg twice daily"],
            patient_records="Sample clinical notes here.",
        )

        # Check all sections present
        assert "## PATIENT DEMOGRAPHICS" in prompt
        assert "## MEDICATION" in prompt
        assert "## DIAGNOSES" in prompt
        assert "## HOME MEDS" in prompt
        assert "## CLINICAL NOTES" in prompt

        # Check patient data included
        assert "John Doe" in prompt
        assert "12345678" in prompt
        assert "1990-01-15" in prompt
        assert "75.0 kg" in prompt
        assert "Penicillin" in prompt
        assert "G70.00" in prompt
        assert "IVIG" in prompt
        assert "Aspirin 81mg daily" in prompt
        assert "Sample clinical notes here." in prompt

    def test_build_prompt_handles_missing_optional_fields(self):
        """Test that prompt handles None/empty values gracefully."""
        prompt = build_care_plan_prompt(
            first_name="Jane",
            last_name="Smith",
            mrn="87654321",
            dob=None,
            sex=None,
            weight_kg=None,
            allergies=None,
            primary_diagnosis_code="G70.00",
            primary_diagnosis_description=None,
            additional_diagnoses=[],
            medication_name="Rituximab",
            medication_history=[],
            patient_records="Notes only.",
        )

        # Should have fallback values
        assert "Not provided" in prompt
        assert "None known" in prompt
        assert "None documented" in prompt

        # Required fields still present
        assert "Jane Smith" in prompt
        assert "87654321" in prompt
        assert "G70.00" in prompt
        assert "Rituximab" in prompt

    def test_build_prompt_formats_lists_correctly(self):
        """Test that lists are formatted as bullet points."""
        prompt = build_care_plan_prompt(
            first_name="Test",
            last_name="Patient",
            mrn="11111111",
            dob="2000-01-01",
            sex="Female",
            weight_kg=60.0,
            allergies="NKDA",
            primary_diagnosis_code="C83.30",
            primary_diagnosis_description="Diffuse large B-cell lymphoma",
            additional_diagnoses=["E11.9", "I10", "N18.3"],
            medication_name="R-CHOP",
            medication_history=["Med1", "Med2", "Med3"],
            patient_records="Clinical notes.",
        )

        # Check list formatting
        assert "- E11.9" in prompt
        assert "- I10" in prompt
        assert "- N18.3" in prompt
        assert "- Med1" in prompt
        assert "- Med2" in prompt
        assert "- Med3" in prompt
