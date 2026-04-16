"""Use Google Gemini to extract structured data from sport-science paper text.

We call Gemini's **native REST API** directly via httpx. Previously we used
the OpenAI-compatible endpoint through the openai SDK, but that layer
occasionally triggered Google's "Multiple authentication credentials
received" 400 error when the environment had overlapping auth env vars
(OPENAI_API_KEY / GOOGLE_API_KEY / GEMINI_API_KEY). Going direct lets us
send exactly one credential (x-goog-api-key) and nothing else.

Free-tier rate limits are strict (as low as 5 RPM on some models), so we:
  - Serialize concurrent calls via a semaphore
  - Retry on 429, honoring the API's retryDelay hint
  - Fall back to exponential backoff if no hint is provided
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re

import httpx

from .config import settings
from .models import ExtractedData

logger = logging.getLogger(__name__)


class QuotaExhaustedError(Exception):
    """Raised when Gemini returns 429 that isn't going to resolve with retries.

    Covers both permanent "limit: 0" quota allocation errors and the case where
    retries are exhausted without success.
    """


class InvalidAPIKeyError(Exception):
    """Raised when the Gemini API key is missing/invalid/expired."""


class _GeminiRateLimited(Exception):
    """Internal signal carrying the parsed 429 body so the retry loop can inspect it."""

    def __init__(self, body: dict):
        self.body = body or {}
        super().__init__(self.body.get("error", {}).get("message", "Rate limited"))


# Free tier can be as low as 5 RPM — keep concurrency low to avoid bursts
_SEMAPHORE = asyncio.Semaphore(2)

# 429 retry policy — tuned to fail visibly within ~90s worst case,
# rather than hanging for many minutes on persistent quota exhaustion
MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 20.0  # seconds, used when the API gives no hint
MAX_RETRY_DELAY = 35.0  # hard cap per attempt

# Native Gemini REST API base
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Per-request HTTP timeout. Paper extraction usually takes 5-30s; give generous slack.
HTTP_TIMEOUT = 90.0

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


def _parse_retry_delay(body: dict) -> float | None:
    """Extract the retry delay (seconds) from a Gemini 429 error body."""
    try:
        msg = body.get("error", {}).get("message", "") or ""
        m = re.search(r"retry in\s+([\d.]+)s", msg, re.IGNORECASE)
        if m:
            return float(m.group(1))
        for detail in body.get("error", {}).get("details", []) or []:
            rd = detail.get("retryDelay")
            if rd:
                m = re.match(r"([\d.]+)s", str(rd))
                if m:
                    return float(m.group(1))
    except (AttributeError, TypeError):
        pass
    return None


def _is_permanent_quota_error(body: dict) -> bool:
    """Detect 429s that won't resolve by retrying (no free-tier allocation, daily limit)."""
    try:
        msg = (body.get("error", {}).get("message", "") or "").lower()
    except AttributeError:
        return False
    if "limit: 0" in msg:
        return True
    if "per day" in msg or "daily" in msg:
        return True
    return False


def _extract_error_message(body: dict, status: int, fallback: str) -> str:
    try:
        err = body.get("error") or {}
        msg = err.get("message")
        if msg:
            return msg
    except AttributeError:
        pass
    return fallback or f"HTTP {status}"


async def _single_call(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    api_key: str,
) -> dict:
    """One POST to Gemini. Translates HTTP errors into domain exceptions."""
    try:
        response = await client.post(
            url,
            json=payload,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=HTTP_TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise TimeoutError("Gemini API request timed out.") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Network error calling Gemini: {exc}") from exc

    try:
        body = response.json()
    except Exception:
        body = {}

    if response.status_code == 200:
        return body

    if response.status_code == 429:
        raise _GeminiRateLimited(body)

    message = _extract_error_message(body, response.status_code, response.text)
    lowered = message.lower()
    if (
        response.status_code in (401, 403)
        or "api key not valid" in lowered
        or "api_key_invalid" in lowered
        or "api key expired" in lowered
    ):
        raise InvalidAPIKeyError(message)

    raise RuntimeError(f"Gemini API error {response.status_code}: {message}")


async def _call_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    api_key: str,
) -> dict:
    """Retry wrapper honoring Gemini's retryDelay hint."""
    last_body: dict = {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await _single_call(client, url, payload, api_key)
        except _GeminiRateLimited as exc:
            last_body = exc.body
            if _is_permanent_quota_error(exc.body):
                logger.warning("Gemini quota permanently exhausted: %s", exc)
                raise QuotaExhaustedError(
                    "Gemini API quota is permanently exhausted for this key "
                    "(daily limit or zero free-tier allocation)."
                ) from exc
            if attempt == MAX_RETRIES:
                break
            hinted = _parse_retry_delay(exc.body)
            if hinted is not None:
                delay = hinted + 1.0
            else:
                delay = DEFAULT_RETRY_DELAY * attempt
            delay = min(delay, MAX_RETRY_DELAY) + random.uniform(0, 2)
            logger.warning(
                "Gemini 429 on attempt %d/%d — sleeping %.1fs before retry",
                attempt,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)

    raise QuotaExhaustedError(
        "Gemini API rate limit persists after retries: "
        f"{_extract_error_message(last_body, 429, 'rate limited')}"
    )


def _truncate_text(text: str, max_chars: int = 800_000) -> str:
    """Truncate text to fit within model context while keeping start and end.

    Gemini 2.5 Flash has a 1M token context (~4M chars), so we can be
    very generous. Papers often have funding/COI info at the end.
    """
    if len(text) <= max_chars:
        return text
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


def _extract_response_text(response_body: dict) -> str:
    """Pull the generated text out of a Gemini generateContent response."""
    candidates = response_body.get("candidates") or []
    if not candidates:
        pf = response_body.get("promptFeedback") or {}
        block_reason = pf.get("blockReason")
        if block_reason:
            raise RuntimeError(f"Gemini blocked the request: {block_reason}")
        raise RuntimeError("Gemini returned no candidates.")

    cand = candidates[0]
    content = cand.get("content") or {}
    parts = content.get("parts") or []
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    text = "".join(text_parts).strip()
    if not text:
        finish_reason = cand.get("finishReason")
        raise RuntimeError(
            f"Gemini returned an empty response (finishReason={finish_reason})."
        )
    return text


async def extract_paper_data(
    paper_text: str,
    api_key: str | None = None,
) -> ExtractedData:
    """Send paper text to Gemini and parse the structured extraction.

    If ``api_key`` is provided, it overrides the server-configured
    ``settings.gemini_api_key``. This enables each end-user to bring their
    own key so quota is scoped to the caller.
    """
    key = (api_key or "").strip() or settings.gemini_api_key
    if not key:
        raise InvalidAPIKeyError(
            "No Gemini API key available (neither user-provided nor server-configured)."
        )

    truncated = _truncate_text(paper_text)
    prompt = EXTRACTION_PROMPT.format(paper_text=truncated)

    payload = {
        "systemInstruction": {
            "parts": [{"text": EXTRACTION_SYSTEM}],
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]},
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_API_BASE}/models/{settings.model_name}:generateContent"

    async with _SEMAPHORE:
        async with httpx.AsyncClient() as client:
            response_body = await _call_with_retry(client, url, payload, key)

    raw = _strip_fences(_extract_response_text(response_body))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:500])
        raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

    return ExtractedData.model_validate(data)
