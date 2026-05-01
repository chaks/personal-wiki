"""Tests for pipeline stages."""
import pytest
from pathlib import Path
import tempfile

from src.services.pipeline_stages import (
    ExtractStage, WriteStage, ResolveStage, IndexStage,
    EntityExtractorStage, WikiPageWriterStage, LinkResolverStage, WikiIndexerStage
)
from src.ingestion.adapters import PDFSourceAdapter
from src.factories import create_default_pipeline_stages, create_default_indexer
from src.extractor import Entity, Concept
from src.services.llm_provider import LLMProvider
from src.services.vector_store import VectorStore
from src.services.embedding_provider import EmbeddingProvider


class MockExtractStage(ExtractStage):
    async def extract_async(self, content: str, source_doc: str) -> tuple[list[Entity], list[Concept]]:
        return [Entity("Test", "person", "desc")], []


class MockWriteStage(WriteStage):
    async def write_async(self, entities: list, concepts: list) -> tuple[list[Path], list[Path]]:
        return [Path("/tmp/entity.md")], []


class MockResolveStage(ResolveStage):
    async def resolve_async(self, page_path: Path) -> list[Path]:
        return []


class MockIndexStage(IndexStage):
    async def index_async(self, pages: list[Path]) -> int:
        return len(pages)


@pytest.mark.asyncio
async def test_extract_stage_interface():
    """ExtractStage must have extract_async method."""
    stage = MockExtractStage()
    entities, concepts = await stage.extract_async("test", "test.md")
    assert len(entities) == 1


@pytest.mark.asyncio
async def test_write_stage_interface():
    """WriteStage must have write_async method."""
    stage = MockWriteStage()
    entity_pages, concept_pages = await stage.write_async([], [])
    assert len(entity_pages) == 1


@pytest.mark.asyncio
async def test_resolve_stage_interface():
    """ResolveStage must have resolve_async method."""
    stage = MockResolveStage()
    placeholders = await stage.resolve_async(Path("/tmp/test.md"))
    assert placeholders == []


@pytest.mark.asyncio
async def test_index_stage_interface():
    """IndexStage must have index_async method."""
    stage = MockIndexStage()
    count = await stage.index_async([Path("/tmp/a.md"), Path("/tmp/b.md")])
    assert count == 2


# --- Real Stage Implementation Tests ---


class TestLLM(LLMProvider):
    """Test LLM provider."""
    async def generate_async(self, prompt: str, system: str = "") -> str:
        return "ENTITY: Alice|person|Developer\nCONCEPT: Testing|Verification|N/A"

    async def generate_stream_async(self, prompt: str, system: str = ""):
        async def gen():
            yield "test"
        return gen()

    def health_check(self) -> bool:
        return True


class TestStore(VectorStore):
    """Test vector store."""
    async def upsert(self, collection_name: str, points: list[dict]) -> bool:
        return True

    async def search(self, collection_name: str, query_vector: list[float], limit: int = 5) -> list:
        return []

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {}


class TestEmbedding(EmbeddingProvider):
    """Test embedding provider."""
    @property
    def dimension(self) -> int:
        return 768

    def embed(self, text: str) -> list[float]:
        return [0.1] * 768

    async def embed_async(self, text: str) -> list[float]:
        return [0.1] * 768


@pytest.mark.asyncio
async def test_entity_extractor_stage_real():
    """EntityExtractorStage wraps EntityExtractor."""
    stage = EntityExtractorStage(TestLLM())
    entities, concepts = await stage.extract_async("test content", "test.md")
    assert len(entities) >= 1


@pytest.mark.asyncio
async def test_wiki_page_writer_stage_real():
    """WikiPageWriterStage wraps WikiPageWriter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stage = WikiPageWriterStage(Path(tmpdir))
        entity = Entity("TestEntity", "person", "A test")
        entity_pages, concept_pages = await stage.write_async([entity], [])
        assert len(entity_pages) == 1


@pytest.mark.asyncio
async def test_link_resolver_stage_real():
    """LinkResolverStage wraps LinkResolver."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        test_page = wiki_dir / "test.md"
        test_page.write_text("# Test\n\n[[MissingLink]]")

        stage = LinkResolverStage(wiki_dir)
        placeholders = await stage.resolve_async(test_page)
        assert len(placeholders) == 1


@pytest.mark.asyncio
async def test_wiki_indexer_stage_real():
    """WikiIndexerStage wraps WikiIndexer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        test_page = wiki_dir / "test.md"
        test_page.write_text("# Test")

        store = TestStore()
        stage = WikiIndexerStage(wiki_dir, store, TestEmbedding())
        count = await stage.index_async([test_page])
        assert count == 1


@pytest.mark.asyncio
async def test_adapter_run_async_with_stages():
    """SourceAdapter.run_async uses injected stages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        output_dir = wiki_dir / "generated"
        output_dir.mkdir(parents=True)

        # Create a minimal PDF-like markdown file
        source_path = Path(tmpdir) / "test.md"
        source_path.write_text("# Test Document\n\nContent here.")

        stages = {
            "extract": EntityExtractorStage(TestLLM()),
            "write": WikiPageWriterStage(wiki_dir),
            "resolve": LinkResolverStage(wiki_dir),
            "index": WikiIndexerStage(wiki_dir, TestStore(), TestEmbedding()),
        }

        adapter = PDFSourceAdapter(
            source_path=source_path,
            wiki_dir=wiki_dir,
            output_dir=output_dir,
        )
        result = await adapter.run_async(
            extract_stage=stages["extract"],
            write_stage=stages["write"],
            resolve_stage=stages["resolve"],
            index_stage=stages["index"],
        )

        assert result.success


# --- Factory Tests ---


@pytest.mark.asyncio
async def test_create_default_pipeline_stages():
    """Factory creates all pipeline stages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        stages = create_default_pipeline_stages(wiki_dir)
        assert stages["extract"] is not None
        assert stages["write"] is not None
        assert stages["resolve"] is not None
        assert stages["index"] is not None


def test_create_default_indexer():
    """Factory creates WikiIndexer with production adapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        indexer = create_default_indexer(wiki_dir)
        assert indexer is not None
        assert indexer.vector_store is not None