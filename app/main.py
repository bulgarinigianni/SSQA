"""Sport Science Quality Analyzer — FastAPI application."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .extractor import InvalidAPIKeyError, QuotaExhaustedError, extract_paper_data
from .models import AnalysisResult
from .pdf_parser import extract_text
from .scoring import score_paper

QUOTA_ERROR_MESSAGE = (
    "Gemini API quota exhausted. Possible causes: (1) the API key's daily "
    "free-tier quota has been used up, (2) no free-tier quota is allocated "
    "for the configured model, or (3) too many requests in a short time. "
    "Try again later, switch to a lighter model (e.g. gemini-2.5-flash-lite), "
    "or provide a personal API key from Google AI Studio "
    "(https://aistudio.google.com/apikey)."
)
AUTH_ERROR_MESSAGE = (
    "Invalid Gemini API key. Please verify the key in Google AI Studio "
    "(https://aistudio.google.com/apikey)."
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sport Science Quality Analyzer",
    description="AI-powered audit tool for sport-science research quality assessment",
    version="1.0.0",
)

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Static files & SPA
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    has_key = bool(settings.gemini_api_key)
    return {"status": "ok", "api_key_configured": has_key, "model": settings.model_name}


# ---------------------------------------------------------------------------
# Single paper analysis
# ---------------------------------------------------------------------------
def _resolve_key(user_key: str | None) -> str:
    """Return the effective Gemini API key or raise 400 if none available."""
    key = (user_key or "").strip() or settings.gemini_api_key
    if not key:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Gemini API key provided. Enter your personal key in the "
                "UI (stored locally in your browser) or set GEMINI_API_KEY on "
                "the server."
            ),
        )
    return key


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_paper(
    file: UploadFile,
    x_gemini_api_key: str | None = Header(None, alias="X-Gemini-API-Key"),
):
    """Upload and analyze a single PDF paper."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    key = _resolve_key(x_gemini_api_key)

    # Save uploaded file
    file_id = uuid.uuid4().hex[:12]
    save_path = UPLOAD_DIR / f"{file_id}.pdf"
    content = await file.read()

    if len(content) > settings.max_pdf_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_pdf_size_mb} MB.",
        )

    save_path.write_bytes(content)

    try:
        result = await _analyze_single(save_path, file.filename, api_key=key)
    except QuotaExhaustedError as exc:
        raise HTTPException(status_code=429, detail=QUOTA_ERROR_MESSAGE) from exc
    except InvalidAPIKeyError as exc:
        raise HTTPException(status_code=401, detail=f"{AUTH_ERROR_MESSAGE} ({exc})") from exc
    finally:
        save_path.unlink(missing_ok=True)

    return result


async def _analyze_single(
    pdf_path: Path,
    filename: str,
    api_key: str | None = None,
) -> AnalysisResult:
    """Core analysis pipeline for a single PDF."""
    # Step 1: Extract text
    try:
        text = extract_text(pdf_path)
    except Exception as exc:
        logger.error("PDF parsing failed for %s: %s", filename, exc)
        raise HTTPException(status_code=422, detail=f"Failed to extract text from PDF: {exc}") from exc

    # Step 2: LLM extraction — let quota/auth errors propagate unchanged
    try:
        extracted = await extract_paper_data(text, api_key=api_key)
    except (QuotaExhaustedError, InvalidAPIKeyError):
        raise
    except Exception as exc:
        logger.error("LLM extraction failed for %s: %s", filename, exc)
        raise HTTPException(
            status_code=502, detail=f"AI extraction failed: {exc}"
        ) from exc

    # Step 3: Score
    result = score_paper(extracted, filename=filename)
    return result


# ---------------------------------------------------------------------------
# Batch analysis
# ---------------------------------------------------------------------------
@app.post("/api/analyze/batch", response_model=list[AnalysisResult])
async def analyze_batch(
    files: list[UploadFile],
    x_gemini_api_key: str | None = Header(None, alias="X-Gemini-API-Key"),
):
    """Upload and analyze multiple PDF papers (max 10)."""
    if len(files) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_batch_size} files per batch.",
        )

    key = _resolve_key(x_gemini_api_key)

    # Save all files first
    saved: list[tuple[Path, str]] = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        file_id = uuid.uuid4().hex[:12]
        save_path = UPLOAD_DIR / f"{file_id}.pdf"
        content = await f.read()
        if len(content) > settings.max_pdf_size_mb * 1024 * 1024:
            continue
        save_path.write_bytes(content)
        saved.append((save_path, f.filename))

    if not saved:
        raise HTTPException(status_code=400, detail="No valid PDF files in batch.")

    # Analyze all concurrently (robust: one failure doesn't stop others).
    # But if quota is exhausted, short-circuit with a 429 instead of returning
    # 10 identical "error" rows — this is almost always a user-recoverable issue
    # that deserves a loud, explicit surface.
    quota_hit = asyncio.Event()

    async def safe_analyze(pdf_path: Path, filename: str) -> AnalysisResult:
        if quota_hit.is_set():
            err = "Skipped: Gemini quota exhausted on a previous item"
        else:
            try:
                return await _analyze_single(pdf_path, filename, api_key=key)
            except QuotaExhaustedError as exc:
                quota_hit.set()
                err = f"Gemini quota exhausted: {exc}"
            except InvalidAPIKeyError as exc:
                quota_hit.set()
                err = f"Invalid API key: {exc}"
            except Exception as exc:
                logger.error("Batch item failed for %s: %s", filename, exc)
                err = str(exc)

        from .models import ConfidenceReport, ExtractedData, ScoringBreakdown

        return AnalysisResult(
            filename=filename,
            extracted=ExtractedData(),
            scoring=ScoringBreakdown(
                design_category="other",
                design_cap=0,
                base_methodology_score=0,
                raw_score=0,
                final_score=0,
                category="error",
                category_label="ERROR",
                explanation=f"Analysis failed: {err}",
            ),
            confidence=ConfidenceReport(
                total_fields=0,
                extracted_fields=0,
                confidence_pct=0,
                level="low",
            ),
            error=err,
        )

    tasks = [safe_analyze(p, name) for p, name in saved]
    results = await asyncio.gather(*tasks)

    # Clean up
    for p, _ in saved:
        p.unlink(missing_ok=True)

    # If every single paper failed due to quota, surface a 429 so the UI shows
    # the dedicated quota-exhausted message instead of a list of error cards.
    if quota_hit.is_set() and all(r.error for r in results):
        raise HTTPException(status_code=429, detail=QUOTA_ERROR_MESSAGE)

    return list(results)


# ---------------------------------------------------------------------------
# Demo / test endpoint (analyze without file upload — accepts raw text)
# ---------------------------------------------------------------------------
@app.post("/api/analyze/text", response_model=AnalysisResult)
async def analyze_text(
    body: dict,
    x_gemini_api_key: str | None = Header(None, alias="X-Gemini-API-Key"),
):
    """Analyze raw paper text (for testing without PDF upload)."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    key = _resolve_key(x_gemini_api_key)

    try:
        extracted = await extract_paper_data(text, api_key=key)
    except QuotaExhaustedError as exc:
        raise HTTPException(status_code=429, detail=QUOTA_ERROR_MESSAGE) from exc
    except InvalidAPIKeyError as exc:
        raise HTTPException(status_code=401, detail=f"{AUTH_ERROR_MESSAGE} ({exc})") from exc

    return score_paper(extracted, filename="text_input")
