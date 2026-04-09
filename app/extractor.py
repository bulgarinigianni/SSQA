"""Use Claude to extract structured data from sport-science paper text."""

from __future__ import annotations

import json
import logging

import anthropic

from .config import settings
from .models import ExtractedData

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """\
You are an expert sport-science research methodologist. Your task is to extract \
structured data from a scientific paper. Be precise and conservative: if a piece \
of information is not clearly stated, return null rather than guessing.

Pay special attention to:
- Study design classification (be specific: RCT, meta-analysis, cohort, etc.)
- Author affiliations and institutional backing
- Funding sources and conflict-of-interest disclosures (often at the very end)
- Whether a funder commercially sells the product being tested (critical for COI)
- Population type: distinguish elite/professional athletes from recreational/students
- For RCTs: evaluate every PEDro criterion carefully (C1-C11)
"""

EXTRACTION_PROMPT = """\
Analyze the following sport-science paper and extract all relevant data.

Return ONLY a JSON object matching this exact schema (use null for unknown fields):

{{
  "title": "string or null",
  "authors": ["list of author names"],
  "year": number_or_null,
  "journal": "string or null",
  "doi": "string or null",
  "study_design": "one of: meta_analysis, systematic_review, rct, prospective_cohort, cross_sectional, case_series, case_study, narrative_review, expert_opinion, consensus_statement, other",
  "sample_size": number_or_null,
  "population_type": "one of: elite, professional, sub_elite, amateur, recreational, university_students, youth_academy, general_population, mixed, other",
  "sport": "string or null",
  "affiliations": ["list of institutional affiliations"],
  "funding_sources": ["list of funding sources"],
  "conflict_of_interest_statement": "string or null — copy the COI statement verbatim if found",
  "product_tested": "string or null — the specific product/supplement/device being evaluated",
  "funder_sells_product": true_or_false_or_null,
  "pedro_criteria": {{
    "c1_eligibility_specified": true_or_false_or_null,
    "c2_random_allocation": true_or_false_or_null,
    "c3_concealed_allocation": true_or_false_or_null,
    "c4_baseline_comparable": true_or_false_or_null,
    "c5_blinding_subjects": true_or_false_or_null,
    "c6_blinding_therapists": true_or_false_or_null,
    "c7_blinding_assessors": true_or_false_or_null,
    "c8_adequate_followup": true_or_false_or_null,
    "c9_intention_to_treat": true_or_false_or_null,
    "c10_between_group": true_or_false_or_null,
    "c11_point_variability": true_or_false_or_null
  }},
  "statistical_methods": "string or null",
  "effect_size_reported": true_or_false_or_null,
  "confidence_intervals_reported": true_or_false_or_null,
  "main_findings_summary": "brief summary string or null",
  "extraction_notes": "string or null — note any difficulties or ambiguities"
}}

IMPORTANT:
- pedro_criteria should ONLY be filled in if study_design is "rct". For non-RCT designs, set pedro_criteria to null.
- funder_sells_product is the MOST CRITICAL field. Examine funding disclosures, COI statements, and author affiliations very carefully.
- For population_type, "elite" means national team / Olympic / international level; "professional" means paid professional athletes; distinguish from "university_students" or "recreational".
- Return ONLY the JSON object, no markdown formatting or extra text.

--- PAPER TEXT ---
{paper_text}
"""


def _truncate_text(text: str, max_chars: int = 180_000) -> str:
    """Truncate text to fit within model context while keeping start and end.

    Papers often have funding/COI info at the end, so we keep both ends.
    """
    if len(text) <= max_chars:
        return text

    # Keep first 70% and last 30% to preserve funding/COI sections
    head_size = int(max_chars * 0.7)
    tail_size = max_chars - head_size
    return (
        text[:head_size]
        + "\n\n[... MIDDLE SECTION TRUNCATED FOR LENGTH ...]\n\n"
        + text[-tail_size:]
    )


async def extract_paper_data(paper_text: str) -> ExtractedData:
    """Send paper text to Claude and parse the structured extraction."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    truncated = _truncate_text(paper_text)
    prompt = EXTRACTION_PROMPT.format(paper_text=truncated)

    message = await client.messages.create(
        model=settings.model_name,
        max_tokens=4096,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last fence lines
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:500])
        raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

    return ExtractedData.model_validate(data)
