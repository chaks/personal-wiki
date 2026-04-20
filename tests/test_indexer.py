# tests/test_indexer.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.indexer import WikiIndexer


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


def test_indexer_initializes(wiki_dir):
    """Indexer initializes with wiki directory."""
    indexer = WikiIndexer(wiki_dir, "http://localhost:6333")
    assert indexer.wiki_dir == wiki_dir
    assert indexer.qdrant_url == "http://localhost:6333"


@patch("src.indexer.ollama")
@patch("src.indexer.QdrantClient")
def test_index_wiki_page(mock_client, mock_ollama, wiki_dir):
    """Indexer embeds and stores wiki page."""
    mock_qdrant = Mock()
    mock_client.return_value = mock_qdrant
    mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}

    page_file = wiki_dir / "concepts" / "test.md"
    page_file.parent.mkdir()
    page_file.write_text("---\ntitle: Test\n---\n\nContent here")

    indexer = WikiIndexer(wiki_dir, "http://localhost:6333")
    indexer.index_page(page_file)

    mock_qdrant.upsert.assert_called_once()


@patch("src.indexer.ollama")
@patch("src.indexer.QdrantClient")
def test_search_returns_results(mock_client, mock_ollama, wiki_dir):
    """Search returns relevant wiki pages."""
    mock_qdrant = Mock()
    mock_client.return_value = mock_qdrant
    mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}

    # Mock search results
    mock_hit = Mock()
    mock_hit.payload = {"path": "test.md", "content": "test content"}
    mock_hit.score = 0.95
    mock_qdrant.search.return_value = [mock_hit]

    indexer = WikiIndexer(wiki_dir, "http://localhost:6333")
    results = indexer.search("test query", top_k=5)

    assert isinstance(results, list)
