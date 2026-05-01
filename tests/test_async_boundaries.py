"""Tests for async/sync boundary fixes."""
import pytest
from pathlib import Path
import tempfile

from src.extractor import EntityExtractor, Entity, Concept
from src.services.llm_provider import LLMProvider
from src.indexer import WikiIndexer
from src.services.vector_store import VectorStore
from src.services.embedding_provider import EmbeddingProvider
from src.ingestion.markdown_copy_adapter import MarkdownCopyAdapter


class MockLLMProvider(LLMProvider):
    """Test double for LLM provider."""

    async def generate_async(self, prompt: str, system: str = "") -> str:
        return "ENTITY: TestEntity|person|A test entity"

    def generate(self, prompt: str, system: str = "") -> str:
        raise RuntimeError("Should not call sync generate")

    async def generate_stream_async(self, prompt: str, system: str = ""):
        async def gen():
            yield "test"
        return gen()

    def health_check(self) -> bool:
        return True


class MockEmbeddingProvider(EmbeddingProvider):
    """Test double for EmbeddingProvider."""

    @property
    def dimension(self) -> int:
        return 768

    def embed(self, text: str) -> list[float]:
        return [0.1] * 768

    async def embed_async(self, text: str) -> list[float]:
        return [0.1] * 768


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


@pytest.mark.asyncio
async def test_extractor_extract_is_async():
    """EntityExtractor.extract must be async-native."""
    extractor = EntityExtractor(llm_provider=MockLLMProvider())
    result = await extractor.extract("test document")
    assert len(result) == 1
    assert result[0].name == "TestEntity"


@pytest.mark.asyncio
async def test_extractor_extract_concepts_is_async():
    """EntityExtractor.extract_concepts must be async-native."""
    class MockLLMWithConcepts(LLMProvider):
        async def generate_async(self, prompt: str, system: str = "") -> str:
            return "CONCEPT: Testing|Verification methodology|N/A"

        def generate(self, prompt: str, system: str = "") -> str:
            raise RuntimeError("Should not call sync generate")

        async def generate_stream_async(self, prompt: str, system: str = ""):
            async def gen():
                yield "test"
            return gen()

        def health_check(self) -> bool:
            return True

    extractor = EntityExtractor(llm_provider=MockLLMWithConcepts())
    result = await extractor.extract_concepts("test document")
    assert len(result) == 1
    assert result[0].name == "Testing"


def test_indexer_requires_vector_store():
    """WikiIndexer must require VectorStore at construction, no lazy fallback."""
    with pytest.raises(TypeError, match="vector_store"):
        WikiIndexer(Path("/tmp/wiki"))  # Missing required vector_store


def test_indexer_no_lazy_init():
    """WikiIndexer must not create QdrantStore lazily."""
    store = InMemoryVectorStore()
    indexer = WikiIndexer(Path("/tmp/wiki"), vector_store=store)
    # This should use the injected store, not create QdrantStore
    assert indexer.vector_store is store


@pytest.mark.asyncio
async def test_markdown_copy_adapter_run_async():
    """MarkdownCopyAdapter.run_async must be async-native."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()
        source_path = Path(tmpdir) / "test.md"
        source_path.write_text("# Test")

        store = InMemoryVectorStore()
        indexer = WikiIndexer(wiki_dir, vector_store=store, embedding_provider=MockEmbeddingProvider())

        adapter = MarkdownCopyAdapter(source_path=source_path, wiki_dir=wiki_dir, indexer=indexer)
        result = await adapter.run_async()

        assert result.success
        assert result.output_path.exists()