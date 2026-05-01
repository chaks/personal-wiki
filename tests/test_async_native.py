import importlib
import pytest
from pathlib import Path
from src.indexer import WikiIndexer
from src.services.vector_store import VectorStore


class InMemoryVectorStore(VectorStore):
    """Test double for VectorStore."""
    def __init__(self):
        self.points = []

    async def upsert(self, collection_name: str, points: list[dict]) -> bool:
        self.points.extend(points)
        return True

    async def search(self, collection_name: str, query_vector: list[float], limit: int = 5) -> list:
        return []

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


def test_sync_vector_store_removed():
    with pytest.raises(ImportError):
        from src.services.vector_store import SyncVectorStore


def test_wiki_indexer_has_async_methods(wiki_dir):
    """WikiIndexer has async methods."""
    store = InMemoryVectorStore()
    indexer = WikiIndexer(wiki_dir, vector_store=store)
    assert hasattr(indexer, 'index_page_async')
    assert hasattr(indexer, 'search_async')
    assert hasattr(indexer, 'index_all_wiki_pages_async')


@pytest.fixture
def wiki_dir(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir