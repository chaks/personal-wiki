"""Ingestion pipelines for external sources."""
from src.ingestion.adapters import (
    SourceAdapter,
    PDFSourceAdapter,
    URLSourceAdapter,
    CodeSourceAdapter,
)
from src.ingestion.url_ingestor import URLIngestor
from src.ingestion.code_ingestor import CodeIngestor
from src.docling_ingestor import DoclingIngestor, DoclingIngestPipeline
from src.ingestion_result import IngestionResult

__all__ = [
    "IngestionResult",
    "SourceAdapter",
    "PDFSourceAdapter",
    "URLSourceAdapter",
    "CodeSourceAdapter",
    "URLIngestor",
    "CodeIngestor",
    "DoclingIngestor",
    "DoclingIngestPipeline",
]
