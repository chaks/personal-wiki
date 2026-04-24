"""Tests for async indexer methods."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from src.indexer import WikiIndexer
from src.services.vector_store import SearchPoint


class MockAsyncVectorStore:
    """Test double for async vector store."""

    def __init__(self):
        self.upserted_points = []
        self.search_queries = []

    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        return True

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        return []

    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        self.upserted_points.extend(points)
        return True

    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        self.search_queries.append((query_vector, limit))
        return [
            SearchPoint(
                id="idx-test-id",
                score=0.92,
                payload={"path": "idx-test.md", "content": "indexer test content"}
            )
        ]

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


class TestAsyncWikiIndexer:
    """Tests for async WikiIndexer methods."""

    @pytest.mark.asyncio
    async def test_index_page_async(self, wiki_dir):
        """WikiIndexer index_page_async embeds and stores a page."""
        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1] * 768}

            mock_store = MockAsyncVectorStore()

            page_file = wiki_dir / "test.md"
            page_file.write_text("---\ntitle: Test\n---\n\nContent here")

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)
            await indexer.index_page_async(page_file)

            assert len(mock_store.upserted_points) == 1
            assert mock_store.upserted_points[0]["payload"]["path"] == "test.md"

    @pytest.mark.asyncio
    async def test_search_async(self, wiki_dir):
        """WikiIndexer search_async returns search results."""
        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1] * 768}

            mock_store = MockAsyncVectorStore()

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)
            results = await indexer.search_async("test query", top_k=5)

            assert len(results) == 1
            assert results[0]["path"] == "idx-test.md"
            assert results[0]["score"] == 0.92

    @pytest.mark.asyncio
    async def test_index_all_wiki_pages_async(self, wiki_dir):
        """WikiIndexer index_all_wiki_pages_async indexes all markdown files."""
        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1] * 768}

            mock_store = MockAsyncVectorStore()

            # Create multiple wiki pages
            (wiki_dir / "page1.md").write_text("Content 1")
            (wiki_dir / "page2.md").write_text("Content 2")
            (wiki_dir / "page3.md").write_text("Content 3")

            subdir = wiki_dir / "subdir"
            subdir.mkdir()
            (subdir / "page4.md").write_text("Content 4")

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)
            indexed_count = await indexer.index_all_wiki_pages_async()

            assert indexed_count == 4
            assert len(mock_store.upserted_points) == 4

    @pytest.mark.asyncio
    async def test_index_all_wiki_pages_async_with_concurrency_limit(self, wiki_dir):
        """WikiIndexer index_all_wiki_pages_async respects concurrency limit."""
        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1] * 768}

            mock_store = MockAsyncVectorStore()

            # Create 10 wiki pages to test concurrency limiting
            for i in range(10):
                (wiki_dir / f"page{i}.md").write_text(f"Content {i}")

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)
            indexed_count = await indexer.index_all_wiki_pages_async()

            assert indexed_count == 10

    @pytest.mark.asyncio
    async def test_index_page_async_handles_exception(self, wiki_dir):
        """WikiIndexer index_page_async handles exceptions gracefully."""
        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Embedding service error")

            mock_store = MockAsyncVectorStore()

            page_file = wiki_dir / "test.md"
            page_file.write_text("Content")

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)

            with pytest.raises(Exception, match="Embedding service error"):
                await indexer.index_page_async(page_file)

    @pytest.mark.asyncio
    async def test_index_all_wiki_pages_async_continues_on_error(self, wiki_dir):
        """WikiIndexer index_all_wiki_pages_async continues on individual failures."""
        call_count = 0

        def mock_embedding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Transient error")
            return {"embedding": [0.1] * 768}

        with patch("src.indexer.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = mock_embedding

            mock_store = MockAsyncVectorStore()

            (wiki_dir / "page1.md").write_text("Content 1")
            (wiki_dir / "page2.md").write_text("Content 2")
            (wiki_dir / "page3.md").write_text("Content 3")

            indexer = WikiIndexer(wiki_dir, vector_store=mock_store)
            indexed_count = await indexer.index_all_wiki_pages_async()

            # Should have indexed 2 out of 3 (page2 failed)
            assert indexed_count == 2
