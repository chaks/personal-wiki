"""Ingestion pipelines for external sources."""
from src.ingestion.url_ingestor import URLIngestor
from src.ingestion.code_ingestor import CodeIngestor

# Re-export DoclingIngestor from the module (not in the package to avoid name shadowing)
from src.docling_ingestor import DoclingIngestor, IngestionResult, DoclingIngestPipeline

__all__ = [
    "URLIngestor",
    "CodeIngestor",
    "DoclingIngestor",
    "DoclingIngestPipeline",
    "IngestionResult",
]
