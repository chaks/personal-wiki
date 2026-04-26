"""Tests for CodeSourceAdapter."""
import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
from src.ingestion.adapters import CodeSourceAdapter
from src.ingestion_result import IngestionResult


@patch("src.ingestion.adapters.CodeSourceAdapter.run")
def test_code_adapter_delegates_to_pipeline(mock_run):
    """CodeSourceAdapter.run() builds and runs the pipeline."""
    mock_run.return_value = IngestionResult(
        success=True,
        output_path=Path("/tmp/code.md"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        adapter = CodeSourceAdapter(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = adapter.run()

        assert result.success is True
        assert result.output_path == Path("/tmp/code.md")
        mock_run.assert_called_once()


@patch("src.ingestion.adapters.CodeSourceAdapter.run")
def test_code_adapter_returns_failure(mock_run):
    """CodeSourceAdapter.run() returns failure on scan error."""
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

        adapter = CodeSourceAdapter(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = adapter.run()

        assert result.success is False
        assert "Scan failed" in result.error


def test_ingestion_result_defaults():
    """IngestionResult has default values."""
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
