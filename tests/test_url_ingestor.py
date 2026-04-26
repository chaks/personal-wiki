"""Tests for URLIngestor (thin wrapper around URLSourceAdapter)."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
from src.ingestion.url_ingestor import URLIngestor
from src.ingestion_result import IngestionResult


@patch("src.ingestion.adapters.URLSourceAdapter.run")
def test_url_ingestor_delegates_to_adapter(mock_run):
    """URLIngestor.ingest() delegates to URLSourceAdapter.run()."""
    mock_run.return_value = IngestionResult(
        success=True,
        output_path=Path("/tmp/test.md"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        ingestor = URLIngestor(url="https://example.com/article", wiki_dir=wiki_dir)
        result = ingestor.ingest()

        assert result.success is True
        assert result.output_path == Path("/tmp/test.md")
        mock_run.assert_called_once()


@patch("src.ingestion.adapters.URLSourceAdapter.run")
def test_url_ingestor_returns_failure(mock_run):
    """URLIngestor propagates adapter failures."""
    mock_run.return_value = IngestionResult(
        success=False,
        output_path=None,
        error="HTTP 404",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        ingestor = URLIngestor(url="https://example.com/missing", wiki_dir=wiki_dir)
        result = ingestor.ingest()

        assert result.success is False
        assert "404" in result.error


def test_ingestion_result_default_values():
    """IngestionResult has default values for optional fields."""
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
