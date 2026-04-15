"""Use Google Gemini to extract structured data from sport-science paper text.

Uses the OpenAI-compatible endpoint provided by Google AI Studio,
so the SDK is openai (same interface, zero extra dependencies).

Free tier rate limits are strict (as low as 5 RPM on some models), so we:
  - Serialize concurrent calls via a semaphore
  - Retry on 429 RateLimitError, honoring the API's retryDelay hint
  - Fall back to exponential backoff if no hint is provided
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re

from openai import AsyncOpenAI, RateLimitError

from .config import settings
from .models import ExtractedData

logger = logging.getLogger(__name__)

# Free tier can be as low as 5 RPM — keep concurrency low to avoid bursts
_SEMAPHORE = asyncio.Semaphore(2)

# 429 retry policy — tuned to fail visibly within ~90s worst case,
# rather than hanging for many minutes on persistent quota exhaustion
MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 20.0  # seconds, used when the API gives no hint
MAX_RETRY_DELAY = 35.0  # hard cap per attempt

# Google AI Studio OpenAI-compatible base URL
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

EXTRACTION_SYSTEM = """\
You are an expert sport-science research methodologist. Your task is to extract \
structured data from a scientific paper. Be precise and conservative: if a piece \
of information is not clearly stated, return null rather than guessing.

Pay special attention to:
- Study design classification (be specific: RCT, meta-analysis, cohort, etc.)
- Author affiliations and institutional backing
- Funding sources and conflict-of-interest disclosures (often at the very end)
- Whether a funder commercially sells the product being tested (critical for COI)
- COI severity: mark "obvious" ONLY when the link between funder and product is \
  explicit and undeniable (e.g. "Funded by RedBull" in a study testing RedBull). \
  If the connection is indirect or unclear, mark "ambiguous". If no conflict, mark "none".
- Population type: distinguish elite/professional athletes from recreational/students
- For RCTs: evaluate every PEDro criterion carefully (C1-C11)
- Whether the study was conducted in the field (real training/match) vs laboratory
- Whether a control or comparison group was used
- Whether the study protocol was pre-registered (ClinicalTrials.gov, PROSPERO, OSF, etc.)
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
  "coi_severity": "one of: obvious, ambiguous, none — 'obvious' ONLY if funder explicitly and undeniably sells the tested product; 'ambiguous' if potential but unclear link; 'none' if no conflict",
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
  "has_control_group": true_or_false_or_null,
  "ecological_context": "one of: field, laboratory, mixed, unclear — 'field' = real training/match environment; 'laboratory' = controlled lab setting",
  "registered_protocol": true_or_false_or_null,
  "main_findings_summary": "brief summary string or null",
  "extraction_notes": "string or null — note any difficulties or ambiguities"
}}

IMPORTANT:
- pedro_criteria should ONLY be filled in if study_design is "rct". For non-RCT designs, set pedro_criteria to null.
- funder_sells_product is CRITICAL. Examine funding disclosures, COI statements, and author affiliations very carefully.
- coi_severity: use "obvious" ONLY when the evidence is undeniable (e.g. company X funds study AND company X sells the exact product being tested). If it is merely suspicious or indirect, use "ambiguous". Do NOT inflate — false COI flags damage good research.
- For population_type, "elite" means national team / Olympic / international level; "professional" means paid professional athletes; distinguish from "university_students" or "recreational".
- ecological_context: "field" means data was collected during actual sport practice, training sessions, or competitive matches. "laboratory" means treadmill, isokinetic dynamometer, or other controlled lab settings.
- registered_protocol: check if the paper mentions registration on ClinicalTrials.gov, PROSPERO, ISRCTN, OSF, UMIN, or similar registries.
- has_control_group: true if there is any comparison/control/placebo group; false if pre-post only on the same group with no comparison.
- Return ONLY the JSON object, no markdown formatting or extra text.

--- PAPER TEXT ---
{paper_text}
"""


def _parse_retry_delay(exc: RateLimitError) -> float | None:
    """Extract the retry delay (in seconds) from a Gemini 429 error body."""
    msg = str(exc)
    # Gemini wraps it as "Please retry in 29.18s." in the human message
    m = re.search(r"retry in\s+([\d.]+)s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Also try the structured RetryInfo field "retryDelay': '29s'"
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", msg)
    if m:
        return float(m.group(1))
    return None


async def _chat_with_retry(client: AsyncOpenAI, **kwargs):
    """Call chat.completions.create, retrying on 429 rate-limit errors."""
    last_exc: RateLimitError | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            last_exc = exc
            if attempt == MAX_RETRIES:
                break
            hinted = _parse_retry_delay(exc)
            if hinted is not None:
                delay = hinted + 1.0  # small safety margin
            else:
                delay = DEFAULT_RETRY_DELAY * attempt  # 30, 60, 90...
            delay = min(delay, MAX_RETRY_DELAY) + random.uniform(0, 2)
            logger.warning(
                "Gemini 429 on attempt %d/%d — sleeping %.1fs before retry",
                attempt,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _truncate_text(text: str, max_chars: int = 800_000) -> str:
    """Truncate text to fit within model context while keeping start and end.

    Gemini 2.5 Flash has a 1M token context (~4M chars), so we can be
    very generous. Papers often have funding/COI info at the end.
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


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if the model wrapped its output."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip()


async def extract_paper_data(paper_text: str) -> ExtractedData:
    """Send paper text to Gemini and parse the structured extraction."""
    client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=GEMINI_BASE_URL,
    )

    truncated = _truncate_text(paper_text)
    prompt = EXTRACTION_PROMPT.format(paper_text=truncated)

    async with _SEMAPHORE:
        response = await _chat_with_retry(
            client,
            model=settings.model_name,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )

    raw = _strip_fences(response.choices[0].message.content or "")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:500])
        raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

    return ExtractedData.model_validate(data)
