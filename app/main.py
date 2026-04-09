"""Sport Science Quality Analyzer — FastAPI application."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .extractor import extract_paper_data
from .models import AnalysisResult
from .pdf_parser import extract_text
from .scoring import score_paper

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
    has_key = bool(settings.anthropic_api_key)
    return {"status": "ok", "api_key_configured": has_key}


# ---------------------------------------------------------------------------
# Single paper analysis
# ---------------------------------------------------------------------------
@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_paper(file: UploadFile):
    """Upload and analyze a single PDF paper."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

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
        result = await _analyze_single(save_path, file.filename)
    finally:
        # Clean up uploaded file
        save_path.unlink(missing_ok=True)

    return result


async def _analyze_single(pdf_path: Path, filename: str) -> AnalysisResult:
    """Core analysis pipeline for a single PDF."""
    # Step 1: Extract text
    try:
        text = extract_text(pdf_path)
    except Exception as exc:
        logger.error("PDF parsing failed for %s: %s", filename, exc)
        raise HTTPException(status_code=422, detail=f"Failed to extract text from PDF: {exc}") from exc

    # Step 2: LLM extraction
    try:
        extracted = await extract_paper_data(text)
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
async def analyze_batch(files: list[UploadFile]):
    """Upload and analyze multiple PDF papers (max 10)."""
    if len(files) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_batch_size} files per batch.",
        )

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

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

    # Analyze all concurrently (robust: one failure doesn't stop others)
    async def safe_analyze(pdf_path: Path, filename: str) -> AnalysisResult:
        try:
            return await _analyze_single(pdf_path, filename)
        except Exception as exc:
            logger.error("Batch item failed for %s: %s", filename, exc)
            # Return a minimal error result
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
                    explanation=f"Analysis failed: {exc}",
                ),
                confidence=ConfidenceReport(
                    total_fields=0,
                    extracted_fields=0,
                    confidence_pct=0,
                    level="low",
                ),
                error=str(exc),
            )

    tasks = [safe_analyze(p, name) for p, name in saved]
    results = await asyncio.gather(*tasks)

    # Clean up
    for p, _ in saved:
        p.unlink(missing_ok=True)

    return list(results)


# ---------------------------------------------------------------------------
# Demo / test endpoint (analyze without file upload — accepts raw text)
# ---------------------------------------------------------------------------
@app.post("/api/analyze/text", response_model=AnalysisResult)
async def analyze_text(body: dict):
    """Analyze raw paper text (for testing without PDF upload)."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    extracted = await extract_paper_data(text)
    return score_paper(extracted, filename="text_input")
