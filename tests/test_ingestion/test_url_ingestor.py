"""Tests for URL ingestion pipeline."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from src.ingestion.url_ingestor import URLIngestor, IngestionResult


def test_url_ingestor_fetches_content():
    """URLIngestor processes content successfully."""
    with patch.object(URLIngestor, '_fetch_content') as mock_fetch, \
         patch.object(URLIngestor, '_html_to_markdown') as mock_convert, \
         patch.object(URLIngestor, '_extract_title') as mock_title, \
         patch.object(URLIngestor, '_generate_output_path') as mock_path, \
         patch.object(URLIngestor, '_ensure_dirs'):

        mock_fetch.return_value = "<html><body>Test</body></html>"
        mock_convert.return_value = "# Test\n\nContent"
        mock_title.return_value = "Test Article"
        mock_path.return_value = Path("/tmp/test.md")

        with patch("src.ingestion.url_ingestor.EntityExtractor") as MockExtractor, \
             patch("src.ingestion.url_ingestor.WikiPageWriter") as MockWriter, \
             patch("src.ingestion.url_ingestor.LinkResolver") as MockResolver, \
             patch("src.ingestion.url_ingestor.WikiIndexer") as MockIndexer:

            MockExtractor.return_value.extract.return_value = []
            MockExtractor.return_value.extract_concepts.return_value = []
            MockWriter.return_value.write_entity.return_value = Path("/tmp/entity.md")
            MockResolver.return_value.resolve_all = Mock()
            MockIndexer.return_value.index_page = Mock()

            with tempfile.TemporaryDirectory() as tmpdir:
                wiki_dir = Path(tmpdir)
                ingestor = URLIngestor(url="https://example.com/article", wiki_dir=wiki_dir)
                result = ingestor.ingest()

                assert result.success is True


@patch("httpx.Client")
def test_url_ingestor_handles_fetch_failure(mock_httpx_client):
    """URLIngestor handles HTTP errors."""
    mock_httpx_client.return_value.__enter__.side_effect = Exception("404 Not Found")
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        ingestor = URLIngestor(url="https://example.com/missing", wiki_dir=wiki_dir)
        result = ingestor.ingest()

        assert result.success is False
        assert "404" in result.error or "HTTP" in result.error.upper()


def test_url_ingestor_extract_title():
    """URLIngestor extracts title from HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        ingestor = URLIngestor(url="https://example.com", wiki_dir=wiki_dir)

        html = "<html><head><title>My Page Title</title></head><body></body></html>"
        title = ingestor._extract_title(html)

        assert title == "My Page Title"


def test_url_ingestor_extract_title_default():
    """URLIngestor returns default title when not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        ingestor = URLIngestor(url="https://example.com", wiki_dir=wiki_dir)

        html = "<html><head></head><body></body></html>"
        title = ingestor._extract_title(html)

        assert title == "untitled"


def test_ingestion_result_default_values():
    """IngestionResult has default values for optional fields."""
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
