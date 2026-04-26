"""Ingestion pipelines for external sources."""
from src.ingestion.adapters import (
    SourceAdapter,
    PDFSourceAdapter,
    URLSourceAdapter,
    CodeSourceAdapter,
)
from src.ingestion_result import IngestionResult

__all__ = [
    "IngestionResult",
    "SourceAdapter",
    "PDFSourceAdapter",
    "URLSourceAdapter",
    "CodeSourceAdapter",
]
