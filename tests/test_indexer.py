"""Tests for WikiIndexer — sync/async unified via async core + LLMProvider injection."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.indexer import WikiIndexer
from src.services.llm_provider import LLMProvider
from src.services.vector_store import SearchPoint


class FakeEmbeddingProvider:
    """Deterministic embedding provider for tests."""

    def __init__(self, dim=768):
        self.embed_calls = []
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [0.1] * self._dim

    async def embed_async(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [0.1] * self._dim


class FakeLLMProvider(LLMProvider):
    """Deterministic generation provider for tests."""

    def health_check(self) -> bool:
        return True

    async def generate_async(self, prompt: str, system=None) -> str:
        return "fake"

    async def generate_stream_async(self, prompt: str, system=None):
        async def gen():
            yield "fake"
        return gen()


class MockVectorStore:
    """Test double for async vector store."""

    def __init__(self):
        self.upserted_points = []
        self.search_queries = []

    async def upsert(self, collection_name: str, points: list[dict]) -> bool:
        self.upserted_points.extend(points)
        return True

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        self.search_queries.append((query_vector, limit))
        return [
            SearchPoint(
                id="test-id",
                score=0.95,
                payload={"path": "test.md", "content": "test content"}
            )
        ]

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


@pytest.fixture
def fake_embedder():
    return FakeEmbeddingProvider()


@pytest.fixture
def mock_store():
    return MockVectorStore()


class TestWikiIndexerInit:
    """WikiIndexer initialization tests."""

    def test_initializes_with_injected_embedder(self, wiki_dir, fake_embedder):
        """WikiIndexer accepts EmbeddingProvider and uses it for embeddings."""
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)
        assert indexer.embedding_provider is fake_embedder

    def test_initializes_with_vector_store(self, wiki_dir, fake_embedder):
        """WikiIndexer uses injected vector store."""
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)
        assert indexer.vector_store is mock_store


class TestWikiIndexerPage:
    """index_page / index_page_async tests."""

    @pytest.mark.asyncio
    async def test_index_page_async(self, wiki_dir, fake_embedder):
        """index_page_async embeds and stores a page."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        page_file = wiki_dir / "test.md"
        page_file.write_text("---\ntitle: Test\n---\n\nContent here")

        await indexer.index_page_async(page_file)

        assert len(mock_store.upserted_points) == 1
        assert mock_store.upserted_points[0]["payload"]["path"] == "test.md"
        assert len(fake_embedder.embed_calls) == 1  # single-chunk page, one embedding

    def test_index_page_sync(self, wiki_dir, fake_embedder):
        """index_page sync wrapper calls index_page_async internally."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        page_file = wiki_dir / "test.md"
        page_file.write_text("---\ntitle: Test\n---\n\nContent here")

        indexer.index_page(page_file)

        assert len(mock_store.upserted_points) == 1

    @pytest.mark.asyncio
    async def test_index_page_multi_chunk(self, wiki_dir, fake_embedder):
        """Multi-chunk pages produce chunk embeddings plus overview."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        # Create content large enough to trigger multi-chunk
        long_content = "## Section 1\n" + "A" * 4000
        page_file = wiki_dir / "long.md"
        page_file.write_text(long_content)

        await indexer.index_page_async(page_file)

        # At least 2 points: chunk(s) + overview
        assert len(mock_store.upserted_points) >= 2

    @pytest.mark.asyncio
    async def test_index_page_async_embeds_via_embedding_provider(self, wiki_dir, fake_embedder):
        """Embeddings come from EmbeddingProvider, not direct ollama call."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        page_file = wiki_dir / "test.md"
        page_file.write_text("Content")

        await indexer.index_page_async(page_file)

        assert len(fake_embedder.embed_calls) == 1
        assert fake_embedder.embed_calls[0] == "Content"


class TestWikiIndexerSearch:
    """search / search_async tests."""

    @pytest.mark.asyncio
    async def test_search_async(self, wiki_dir, fake_embedder):
        """search_async returns results from vector store."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        results = await indexer.search_async("test query", top_k=5)

        assert len(results) == 1
        assert results[0]["path"] == "test.md"
        assert results[0]["score"] == 0.95
        assert len(fake_embedder.embed_calls) == 1

    def test_search_sync(self, wiki_dir, fake_embedder):
        """search sync wrapper delegates to search_async."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        results = indexer.search("test query", top_k=5)

        assert len(results) == 1


class TestWikiIndexerBatch:
    """index_all_wiki_pages tests."""

    @pytest.mark.asyncio
    async def test_index_all_wiki_pages_async(self, wiki_dir, fake_embedder):
        """index_all_wiki_pages_async indexes all markdown files."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        (wiki_dir / "page1.md").write_text("Content 1")
        (wiki_dir / "page2.md").write_text("Content 2")
        (wiki_dir / "page3.md").write_text("Content 3")

        subdir = wiki_dir / "subdir"
        subdir.mkdir()
        (subdir / "page4.md").write_text("Content 4")

        count = await indexer.index_all_wiki_pages_async()

        assert count == 4

    def test_index_all_wiki_pages_sync(self, wiki_dir, fake_embedder):
        """index_all_wiki_pages sync wrapper delegates to async."""
        mock_store = MockVectorStore()
        indexer = WikiIndexer(wiki_dir, embedding_provider=fake_embedder, vector_store=mock_store)

        (wiki_dir / "page1.md").write_text("Content 1")
        (wiki_dir / "page2.md").write_text("Content 2")

        count = indexer.index_all_wiki_pages()

        assert count == 2
