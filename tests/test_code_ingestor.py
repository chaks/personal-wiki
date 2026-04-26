"""Tests for CodeIngestor (thin wrapper around CodeSourceAdapter)."""
import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
from src.ingestion.code_ingestor import CodeIngestor
from src.ingestion_result import IngestionResult


@patch("src.ingestion.adapters.CodeSourceAdapter.run")
def test_code_ingestor_delegates_to_adapter(mock_run):
    """CodeIngestor.ingest() delegates to CodeSourceAdapter.run()."""
    mock_run.return_value = IngestionResult(
        success=True,
        output_path=Path("/tmp/code.md"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = ingestor.ingest()

        assert result.success is True
        assert result.output_path == Path("/tmp/code.md")
        mock_run.assert_called_once()


@patch("src.ingestion.adapters.CodeSourceAdapter.run")
def test_code_ingestor_returns_failure(mock_run):
    """CodeIngestor propagates adapter failures."""
    mock_run.return_value = IngestionResult(
        success=False,
        output_path=None,
        error="Scan failed",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = ingestor.ingest()

        assert result.success is False
        assert "Scan failed" in result.error


def test_ingestion_result_defaults():
    """IngestionResult has default values."""
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
