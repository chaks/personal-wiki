import importlib
import pytest
from src.indexer import WikiIndexer


def test_sync_vector_store_removed():
    with pytest.raises(ImportError):
        from src.services.vector_store import SyncVectorStore


def test_wiki_indexer_has_no_sync_wrappers(wiki_dir):
    """WikiIndexer no longer has sync index_page/search methods."""
    indexer = WikiIndexer(wiki_dir)
    assert hasattr(indexer, 'index_page_async')
    assert hasattr(indexer, 'search_async')
    assert hasattr(indexer, 'index_all_wiki_pages_async')
    assert not hasattr(indexer, 'index_page')
    assert not hasattr(indexer, 'search')
    assert not hasattr(indexer, 'index_all_wiki_pages')


@pytest.fixture
def wiki_dir(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir
