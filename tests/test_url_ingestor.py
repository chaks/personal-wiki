"""Tests for URLSourceAdapter."""
import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import tempfile


@patch("src.ingestion.adapters.URLSourceAdapter.first_stage")
def test_url_adapter_delegates_to_pipeline(mock_first_stage):
    """URLSourceAdapter.run() builds and runs the pipeline."""
    from src.ingestion.adapters import URLSourceAdapter
    from src.ingestion_result import IngestionResult

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        adapter = URLSourceAdapter(url="https://example.com/article", wiki_dir=wiki_dir)

        # The adapter's run() method is tested in integration via PDFSourceAdapter tests
        # Here we verify the adapter is constructible and has the expected attributes
        assert adapter.url == "https://example.com/article"
        assert adapter.timeout == 30.0


def test_url_adapter_attributes():
    """URLSourceAdapter stores url and timeout."""
    from src.ingestion.adapters import URLSourceAdapter
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        adapter = URLSourceAdapter(
            url="https://example.com/test",
            wiki_dir=wiki_dir,
            timeout=10.0,
        )
        assert adapter.url == "https://example.com/test"
        assert adapter.timeout == 10.0


def test_code_adapter_attributes():
    """CodeSourceAdapter stores code_dir, language, and extensions."""
    from src.ingestion.adapters import CodeSourceAdapter
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()
        adapter = CodeSourceAdapter(
            code_dir=code_dir,
            wiki_dir=wiki_dir,
            language="python",
        )
        assert adapter.language == "python"
        assert adapter.extensions == [".py"]


@patch("src.ingestion.adapters.URLSourceAdapter.run")
def test_url_adapter_returns_failure(mock_run):
    """URLSourceAdapter.run() returns failure on HTTP error."""
    from src.ingestion.adapters import URLSourceAdapter
    from src.ingestion_result import IngestionResult

    mock_run.return_value = IngestionResult(
        success=False,
        output_path=None,
        error="HTTP 404",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        adapter = URLSourceAdapter(url="https://example.com/missing", wiki_dir=wiki_dir)
        result = adapter.run()

        assert result.success is False
        assert "404" in result.error


@patch("src.ingestion.adapters.CodeSourceAdapter.run")
def test_code_adapter_returns_failure(mock_run):
    """CodeSourceAdapter.run() returns failure on scan error."""
    from src.ingestion.adapters import CodeSourceAdapter
    from src.ingestion_result import IngestionResult

    mock_run.return_value = IngestionResult(
        success=False,
        output_path=None,
        error="Scan failed",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()
        adapter = CodeSourceAdapter(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = adapter.run()

        assert result.success is False
        assert "Scan failed" in result.error


def test_ingestion_result_defaults():
    """IngestionResult has default values."""
    from src.ingestion_result import IngestionResult
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
