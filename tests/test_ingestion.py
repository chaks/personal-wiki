"""Tests for PDFSourceAdapter."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def temp_source(tmp_path):
    """Create a temporary source file."""
    source_file = tmp_path / "test_source.md"
    source_file.write_text("# Test Document\n\nThis is test content.")
    return source_file


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "wiki" / "generated"
    output_dir.mkdir(parents=True)
    return output_dir


@pytest.fixture
def temp_wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    return wiki_dir


def test_adapter_initializes(temp_source, temp_output_dir, temp_wiki_dir):
    """PDFSourceAdapter initializes with source and output paths."""
    from src.ingestion.adapters import PDFSourceAdapter
    adapter = PDFSourceAdapter(
        source_path=temp_source,
        wiki_dir=temp_wiki_dir,
        output_dir=temp_output_dir,
    )
    assert adapter.source_path == temp_source
    assert adapter.output_dir == temp_output_dir
    assert adapter.wiki_dir == temp_wiki_dir


@pytest.mark.asyncio
@patch("src.ingestion.adapters.DocumentConverter")
async def test_adapter_runs_pipeline(mock_converter, temp_source, temp_output_dir, temp_wiki_dir):
    """PDFSourceAdapter.run_async() converts source and returns IngestionResult."""
    from src.ingestion.adapters import PDFSourceAdapter
    mock_instance = Mock()
    mock_result = Mock()
    mock_result.document.export_to_markdown.return_value = "# Converted\n\nMarkdown content"
    mock_instance.convert.return_value = mock_result
    mock_converter.return_value = mock_instance

    adapter = PDFSourceAdapter(
        source_path=temp_source,
        wiki_dir=temp_wiki_dir,
        output_dir=temp_output_dir,
    )
    result = await adapter.run_async()

    assert result.success is True
    assert result.output_path == temp_output_dir / "test_source.md"


@pytest.mark.asyncio
@patch("src.ingestion.adapters.DocumentConverter")
async def test_adapter_handles_failure(mock_converter, temp_source, temp_output_dir, temp_wiki_dir):
    """PDFSourceAdapter.run_async() returns failure on conversion error."""
    from src.ingestion.adapters import PDFSourceAdapter
    mock_instance = Mock()
    mock_instance.convert.side_effect = Exception("Conversion failed")
    mock_converter.return_value = mock_instance

    adapter = PDFSourceAdapter(
        source_path=temp_source,
        wiki_dir=temp_wiki_dir,
        output_dir=temp_output_dir,
    )
    result = await adapter.run_async()

    assert result.success is False
    assert "Conversion failed" in result.error


@pytest.mark.asyncio
@patch("src.ingestion.adapters.WikiIndexer")
@patch("src.ingestion.adapters.LinkResolver")
@patch("src.ingestion.adapters.WikiPageWriter")
@patch("src.ingestion.adapters.EntityExtractor")
@patch("src.ingestion.adapters.DocumentConverter")
async def test_adapter_extracts_entities_and_concepts(
    mock_converter, mock_extractor_class, mock_writer_class,
    mock_resolver_class, mock_indexer_class,
    temp_source, temp_output_dir, temp_wiki_dir
):
    """PDFSourceAdapter.run_async() extracts entities and concepts after conversion."""
    from src.ingestion.adapters import PDFSourceAdapter
    mock_instance = Mock()
    mock_result = Mock()
    mock_result.document.export_to_markdown.return_value = "# Test\n\nContent"
    mock_instance.convert.return_value = mock_result
    mock_converter.return_value = mock_instance

    mock_extractor = Mock()
    mock_extractor.extract.return_value = []
    mock_extractor.extract_concepts.return_value = []
    mock_extractor_class.return_value = mock_extractor

    mock_writer = Mock()
    mock_writer.write_entity.return_value = temp_wiki_dir / "entity.md"
    mock_writer.write_concept.return_value = temp_wiki_dir / "concept.md"
    mock_writer_class.return_value = mock_writer

    mock_resolver = Mock()
    mock_resolver.resolve_all.return_value = []
    mock_resolver_class.return_value = mock_resolver

    mock_indexer = Mock()
    mock_indexer.index_page.return_value = None
    mock_indexer_class.return_value = mock_indexer

    adapter = PDFSourceAdapter(
        source_path=temp_source,
        wiki_dir=temp_wiki_dir,
        output_dir=temp_output_dir,
    )
    result = await adapter.run_async()

    assert result.success is True


def test_ingestion_result_to_dict(temp_source):
    """IngestionResult serializes to dict."""
    from src.ingestion_result import IngestionResult
    result = IngestionResult(
        success=True,
        output_path=temp_source,
        entity_pages=[temp_source],
        concept_pages=[temp_source],
    )
    data = result.to_dict()
    assert data["success"] is True
    assert data["output_path"] == str(temp_source)
    assert len(data["entity_pages"]) == 1
    assert len(data["concept_pages"]) == 1
