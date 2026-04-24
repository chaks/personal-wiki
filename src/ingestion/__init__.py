"""Ingestion pipelines for external sources."""
from src.ingestion.url_ingestor import URLIngestor, IngestionResult

__all__ = [
    "URLIngestor",
    "IngestionResult",
]
