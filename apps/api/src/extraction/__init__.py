"""Text extraction module for document processing.

Provides text extraction from PDFs and DOCX files.
No OCR - only native text extraction.
Arabic text is stored as-is (no reshaping or bidi transformations).
"""

from src.extraction.chunker import ChunkResult, create_chunks
from src.extraction.extractors import (
    ExtractionResult,
    extract_docx_text,
    extract_pdf_text,
    extract_text,
)

__all__ = [
    "ChunkResult",
    "ExtractionResult",
    "create_chunks",
    "extract_docx_text",
    "extract_pdf_text",
    "extract_text",
]
