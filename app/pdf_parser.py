"""Extract text content from PDF files using PyMuPDF (fitz)."""

from pathlib import Path

import fitz  # PyMuPDF


def extract_text(pdf_path: str | Path) -> str:
    """Extract full text from a PDF file.

    Returns concatenated text from all pages with page markers.
    """
    doc = fitz.open(str(pdf_path))
    pages: list[str] = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"--- PAGE {i} ---\n{text}")

    doc.close()

    if not pages:
        raise ValueError("No extractable text found in PDF. The file may be scanned/image-only.")

    return "\n\n".join(pages)
