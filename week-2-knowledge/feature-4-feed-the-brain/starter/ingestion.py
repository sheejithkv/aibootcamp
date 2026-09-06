"""
Feature 4 starter: text extraction and chunking — YOUR IMPLEMENTATION GOES HERE.

The complete version lives in shared/ingestion.py (read it for reference).
"""

import io
import re
from pathlib import Path
from typing import Callable


# =============================================================================
# Extraction
# =============================================================================

def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from the given file bytes.

    Supported:
      .txt
      .pdf
      .docx
    """
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="replace")

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if ext == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(
            para.text
            for para in doc.paragraphs
            if para.text.strip()
        )

    raise ValueError(
        f"Unsupported file type: '{ext}'. Supported formats: .txt, .pdf, .docx."
    )


def extract_pages(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Extract text per page.

    For PDF: one entry per page.
    For TXT/DOCX: one entry containing all text.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))

        return [
            {
                "page_number": i + 1,
                "text": page.extract_text() or "",
            }
            for i, page in enumerate(reader.pages)
        ]

    return [
        {
            "page_number": 1,
            "text": extract_text(file_bytes, filename),
        }
    ]


# =============================================================================
# Chunking strategies
# =============================================================================

def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Sentence-aware fixed-size chunking.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        slen = len(sentence)

        if current and current_len + slen > chunk_size:
            chunks.append(" ".join(current))

            tail: list[str] = []
            tail_len = 0

            for s in reversed(current):
                candidate_len = len(s) + 1

                if tail_len + candidate_len > overlap:
                    break

                tail.insert(0, s)
                tail_len += candidate_len

            current = tail
            current_len = tail_len

        current.append(sentence)
        current_len += slen + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_by_paragraph(
    text: str,
    max_chunk_size: int = 800,
) -> list[str]:
    """
    Paragraph-based chunking.
    """
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\n+", text)
        if p.strip()
    ]

    chunks: list[str] = []

    for para in paragraphs:
        if len(para) <= max_chunk_size:
            chunks.append(para)
        else:
            chunks.extend(
                chunk_text(
                    para,
                    chunk_size=max_chunk_size,
                )
            )

    return chunks


def chunk_by_page(
    pages: list[dict],
    max_page_size: int = 2000,
) -> list[dict]:
    """
    Per-page chunking preserving page metadata.
    """
    result: list[dict] = []
    chunk_index = 0

    for page in pages:
        text = page["text"].strip()
        page_num = page["page_number"]

        if not text:
            continue

        if len(text) <= max_page_size:
            result.append(
                {
                    "text": text,
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1

        else:
            for sub in chunk_text(
                text,
                chunk_size=max_page_size,
            ):
                result.append(
                    {
                        "text": sub,
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1

    return result


# =============================================================================
# Strategy registry
# =============================================================================

def _sentence_strategy(
    text: str,
    pages: list[dict],
) -> list[dict]:
    return [
        {
            "text": c,
            "page_number": None,
            "chunk_index": i,
        }
        for i, c in enumerate(chunk_text(text))
    ]


def _paragraph_strategy(
    text: str,
    pages: list[dict],
) -> list[dict]:
    return [
        {
            "text": c,
            "page_number": None,
            "chunk_index": i,
        }
        for i, c in enumerate(chunk_by_paragraph(text))
    ]


CHUNKING_STRATEGIES: dict[
    str,
    Callable[[str, list[dict]], list[dict]]
] = {
    "sentence": _sentence_strategy,
    "paragraph": _paragraph_strategy,
}
