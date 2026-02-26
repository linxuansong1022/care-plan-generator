"""
Service to analyze recent care plans and extract skeleton structure.
Uses LLM to dynamically learn the care plan format from existing examples.
"""

import re
import structlog
from typing import Optional

from django.conf import settings

from .models import CarePlan

logger = structlog.get_logger(__name__)

# Default skeleton if no care plans exist or analysis fails
DEFAULT_SKELETON = """## OUTPUT FORMAT
Generate a care plan that MUST include the following sections:

1. Problem list / Drug therapy problems (DTPs)
2. Goals (SMART)
3. Pharmacist interventions / plan
4. Monitoring plan & lab schedule

Base your recommendations on the patient's actual data provided."""


def get_recent_care_plans(limit: int = 3) -> list[CarePlan]:
    """
    Fetch the most recent LLM-generated care plans.
    Excludes manually uploaded care plans.
    """
    return list(
        CarePlan.objects.filter(is_uploaded=False)
        .order_by("-created_at")[:limit]
    )


def extract_skeleton_with_llm(care_plans: list[CarePlan], llm_service) -> str:
    """
    Use LLM to analyze multiple care plans and extract common skeleton structure.
    """
    if not care_plans:
        logger.info("skeleton_analysis_no_plans", message="No care plans available for analysis")
        return DEFAULT_SKELETON

    # Build the analysis prompt
    examples = []
    for i, plan in enumerate(care_plans, 1):
        # Truncate content to avoid token limits
        content = plan.content[:3000] if len(plan.content) > 3000 else plan.content
        examples.append(f"### Example {i}:\n{content}")

    examples_text = "\n\n".join(examples)

    analysis_prompt = f"""Analyze the following care plan examples and extract the common skeleton/structure.

{examples_text}

---

Based on these examples, provide ONLY the section headers and structure that should be used for generating new care plans. Output in this exact format:

## OUTPUT FORMAT
Generate a care plan that MUST include the following sections:

[List the section headers you identified, numbered, with brief description of what each contains]

Do NOT include any actual content, just the structure/headers."""

    system_prompt = "You are a technical analyst. Extract only the structural skeleton from the provided examples. Be concise."

    try:
        response = llm_service.generate(
            prompt=analysis_prompt,
            system_prompt=system_prompt,
        )

        logger.info(
            "skeleton_analysis_completed",
            examples_count=len(care_plans),
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )

        return response.content

    except Exception as e:
        logger.error(
            "skeleton_analysis_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return DEFAULT_SKELETON


def extract_skeleton_simple(care_plans: list[CarePlan]) -> str:
    """
    Simple regex-based extraction of section headers without using LLM.
    Faster and cheaper alternative.
    """
    if not care_plans:
        return DEFAULT_SKELETON

    # Patterns to match markdown headers
    # Pattern 1: ## or ### headers with optional numbering
    header_pattern_1 = r'^#{1,3}\s+(?:\d+\.\s+)?([A-Z][A-Za-z\s/&\-]+)(?:\s*\(.*\))?:?$'
    # Pattern 2: Numbered headers like "1. PROBLEM LIST"
    header_pattern_2 = r'^\d+\.\s+([A-Z][A-Z\s/&\-]+)$'

    # Known important sections to look for (prioritized)
    priority_sections = [
        "PROBLEM LIST",
        "DRUG THERAPY PROBLEMS",
        "GOALS",
        "PHARMACIST INTERVENTIONS",
        "MONITORING PLAN",
        "LAB SCHEDULE",
        "PATIENT EDUCATION",
        "FOLLOW-UP",
    ]

    # Collect headers from all care plans
    all_headers = []
    for plan in care_plans:
        headers_1 = re.findall(header_pattern_1, plan.content, re.MULTILINE)
        headers_2 = re.findall(header_pattern_2, plan.content, re.MULTILINE)
        all_headers.extend(headers_1)
        all_headers.extend(headers_2)

    # Count occurrences and get common headers
    header_counts = {}
    for header in all_headers:
        # Normalize header: uppercase, remove extra spaces
        normalized = ' '.join(header.strip().upper().split())
        # Skip very short or generic headers
        if len(normalized) < 4 or normalized in ['THE', 'AND', 'FOR']:
            continue
        header_counts[normalized] = header_counts.get(normalized, 0) + 1

    if not header_counts:
        return DEFAULT_SKELETON

    # Sort by: 1) priority sections first, 2) then by count
    def sort_key(item):
        header, count = item
        # Check if it matches any priority section
        for i, priority in enumerate(priority_sections):
            if priority in header or header in priority:
                return (0, i, -count)  # Priority sections first
        return (1, 0, -count)  # Non-priority by count

    sorted_headers = sorted(header_counts.items(), key=sort_key)

    # Get top headers (main sections only, avoid sub-sections)
    main_sections = []
    seen_keywords = set()
    for header, count in sorted_headers:
        # Skip if this is likely a sub-section of something we already have
        keywords = set(header.split())
        if keywords & seen_keywords and len(keywords & seen_keywords) > 1:
            continue
        main_sections.append(header)
        seen_keywords.update(keywords)
        if len(main_sections) >= 6:  # Limit to 6 main sections
            break

    if not main_sections:
        return DEFAULT_SKELETON

    # Build skeleton output
    skeleton_parts = ["## OUTPUT FORMAT", "Generate a care plan that MUST include the following sections:", ""]

    for i, header in enumerate(main_sections, 1):
        skeleton_parts.append(f"{i}. {header.title()}")

    skeleton_parts.append("")
    skeleton_parts.append("Base your recommendations on the patient's actual data provided.")

    logger.info(
        "skeleton_extracted",
        sections_found=len(main_sections),
        sections=main_sections,
    )

    return "\n".join(skeleton_parts)


def get_dynamic_skeleton(use_llm: bool = True, llm_service=None) -> str:
    """
    Get the dynamic skeleton for care plan generation.

    Args:
        use_llm: If True, use LLM for analysis. If False, use simple regex extraction.
        llm_service: The LLM service instance (required if use_llm=True)

    Returns:
        The skeleton string to include in the system prompt.
    """
    care_plans = get_recent_care_plans(limit=3)

    logger.debug(
        "skeleton_fetch_started",
        plan_count=len(care_plans),
        use_llm=use_llm,
    )

    if not care_plans:
        logger.info("skeleton_using_default", reason="no_care_plans")
        return DEFAULT_SKELETON

    if use_llm and llm_service:
        return extract_skeleton_with_llm(care_plans, llm_service)
    else:
        return extract_skeleton_simple(care_plans)


def build_dynamic_system_prompt(skeleton: str) -> str:
    """
    Build the complete system prompt with dynamic skeleton.
    """
    return f"""You are a clinical pharmacist assistant. Your task is to generate a comprehensive pharmacist care plan based on the patient records provided.

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

{skeleton}
"""
