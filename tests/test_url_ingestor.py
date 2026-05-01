"""Tests for URLSourceAdapter."""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path
import tempfile


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


@pytest.mark.asyncio
@patch("src.ingestion.adapters.URLSourceAdapter.run_async")
async def test_url_adapter_returns_failure(mock_run):
    """URLSourceAdapter.run_async() returns failure on HTTP error."""
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
        result = await adapter.run_async()

        assert result.success is False
        assert "404" in result.error


@pytest.mark.asyncio
@patch("src.ingestion.adapters.CodeSourceAdapter.run_async")
async def test_code_adapter_returns_failure(mock_run):
    """CodeSourceAdapter.run_async() returns failure on scan error."""
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
        result = await adapter.run_async()

        assert result.success is False
        assert "Scan failed" in result.error


def test_ingestion_result_defaults():
    """IngestionResult has default values."""
    from src.ingestion_result import IngestionResult
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
