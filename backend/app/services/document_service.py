"""Document processing: upload, PDF extraction, chunking, and management."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from app.config import get_settings
from app.models import Document, DocumentChunk, DocStatus

logger = logging.getLogger(__name__)

# ── PDF Extraction ─────────────────────────────────────────────


def extract_text_from_pdf(file_path: Path) -> dict:
    """Extract text from a digital PDF using PyMuPDF.

    Returns:
        dict with keys: pages (list of {page_number, text, headings}),
                        page_count, title, is_scanned
    """
    doc = fitz.open(str(file_path))
    pages = []
    total_text_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        total_text_chars += len(text.strip())

        # Attempt to detect headings from font size
        headings = []
        try:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        # Heuristic: large font or bold = heading
                        if span["size"] >= 14 or "Bold" in span.get("font", ""):
                            heading_text = span["text"].strip()
                            if heading_text and len(heading_text) > 2:
                                headings.append(heading_text)
        except Exception:
            pass

        pages.append({
            "page_number": page_num + 1,
            "text": text,
            "headings": headings,
        })

    # Detect scanned / image-heavy PDFs
    is_scanned = total_text_chars < 50 * len(doc) if len(doc) > 0 else False

    # Try to get title from metadata
    metadata = doc.metadata or {}
    title = metadata.get("title", "") or ""
    if not title and pages:
        # Use first heading or first line as title
        first_headings = pages[0].get("headings", [])
        if first_headings:
            title = first_headings[0]
        else:
            first_line = pages[0]["text"].strip().split("\n")[0][:100]
            title = first_line if first_line else ""

    doc.close()

    return {
        "pages": pages,
        "page_count": len(pages),
        "title": title,
        "is_scanned": is_scanned,
    }


# ── Chunking ───────────────────────────────────────────────────

def chunk_document(
    document_id: str,
    pages: list[dict],
    max_chunk_size: int = 1500,
    overlap: int = 200,
) -> list[DocumentChunk]:
    """Split extracted pages into section-aware chunks.

    Strategy:
    1. Try to split on headings / section boundaries.
    2. Fall back to paragraph boundaries.
    3. Last resort: character-based splitting with overlap.
    """
    chunks: list[DocumentChunk] = []

    for page in pages:
        page_num = page["page_number"]
        text = page["text"].strip()
        if not text:
            continue

        headings = page.get("headings", [])
        current_heading = headings[0] if headings else None

        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this paragraph starts with a heading
            for h in headings:
                if para.startswith(h):
                    current_heading = h
                    break

            if len(current_chunk) + len(para) + 1 <= max_chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        document_id=document_id,
                        page_number=page_num,
                        heading=current_heading,
                        content=current_chunk,
                        char_count=len(current_chunk),
                    ))
                # Start new chunk (with overlap from previous)
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para

                # If single paragraph exceeds max, split it
                while len(current_chunk) > max_chunk_size:
                    split_at = current_chunk[:max_chunk_size].rfind('. ')
                    if split_at == -1:
                        split_at = max_chunk_size
                    else:
                        split_at += 1

                    chunks.append(DocumentChunk(
                        document_id=document_id,
                        page_number=page_num,
                        heading=current_heading,
                        content=current_chunk[:split_at].strip(),
                        char_count=split_at,
                    ))
                    current_chunk = current_chunk[split_at:].strip()

        # Flush remaining
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                document_id=document_id,
                page_number=page_num,
                heading=current_heading,
                content=current_chunk.strip(),
                char_count=len(current_chunk.strip()),
            ))

    logger.info("Chunked document %s into %d chunks", document_id, len(chunks))
    return chunks


# ── Document Lifecycle ─────────────────────────────────────────

def validate_upload(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate file type and size before processing."""
    settings = get_settings()

    if not filename.lower().endswith('.pdf'):
        return False, "Only PDF files are supported."

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File exceeds {settings.max_upload_size_mb}MB limit."

    # Basic filename sanitization
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename."

    return True, "OK"


def process_document(document_id: str, file_path: Path) -> tuple[Document, list[DocumentChunk]]:
    """Full pipeline: extract → chunk → return document + chunks.

    Does NOT call any paid APIs — extraction is local via PyMuPDF.
    """
    settings = get_settings()

    try:
        extraction = extract_text_from_pdf(file_path)

        if extraction["page_count"] > settings.max_pages:
            return Document(
                document_id=document_id,
                filename=file_path.name,
                status=DocStatus.ERROR,
                error_message=f"Document exceeds {settings.max_pages} page limit.",
                page_count=extraction["page_count"],
            ), []

        if extraction["is_scanned"]:
            logger.warning(
                "Document %s appears to be scanned. Text extraction may be incomplete. "
                "Sarvam Vision could improve results but is not called automatically.",
                document_id,
            )

        chunks = chunk_document(document_id, extraction["pages"])

        doc = Document(
            document_id=document_id,
            filename=file_path.name,
            title=extraction["title"] or file_path.stem,
            page_count=extraction["page_count"],
            status=DocStatus.READY,
            chunk_count=len(chunks),
            processed_at=datetime.now(timezone.utc),
            file_size_bytes=file_path.stat().st_size,
            is_scanned=extraction["is_scanned"],
        )

        return doc, chunks

    except Exception as e:
        logger.error("Document processing failed for %s: %s", document_id, str(e))
        return Document(
            document_id=document_id,
            filename=file_path.name,
            status=DocStatus.ERROR,
            error_message=str(e),
        ), []
