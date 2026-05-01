"""Pipeline stage interfaces for ingestion."""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.extractor import Entity, Concept
from src.extractor import EntityExtractor
from src.wiki_writer import WikiPageWriter
from src.link_resolver import LinkResolver
from src.indexer import WikiIndexer
from src.services.llm_provider import LLMProvider
from src.services.embedding_provider import EmbeddingProvider
from src.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ExtractStage(ABC):
    """Interface for entity/concept extraction stage."""

    @abstractmethod
    async def extract_async(
        self, content: str, source_doc: str
    ) -> tuple[list[Entity], list[Concept]]:
        """Extract entities and concepts from content.

        Args:
            content: Document content
            source_doc: Source document path

        Returns:
            Tuple of (entities, concepts)
        """
        pass


class WriteStage(ABC):
    """Interface for wiki page writing stage."""

    @abstractmethod
    async def write_async(
        self, entities: list[Entity], concepts: list[Concept]
    ) -> tuple[list[Path], list[Path]]:
        """Write entity and concept pages.

        Args:
            entities: Extracted entities
            concepts: Extracted concepts

        Returns:
            Tuple of (entity_page_paths, concept_page_paths)
        """
        pass


class ResolveStage(ABC):
    """Interface for link resolution stage."""

    @abstractmethod
    async def resolve_async(self, page_path: Path) -> list[Path]:
        """Resolve wikilinks in a page.

        Args:
            page_path: Path to the markdown file

        Returns:
            List of created placeholder paths
        """
        pass


class IndexStage(ABC):
    """Interface for semantic indexing stage."""

    @abstractmethod
    async def index_async(self, pages: list[Path]) -> int:
        """Index pages in vector store.

        Args:
            pages: List of page paths to index

        Returns:
            Number of successfully indexed pages
        """
        pass


# --- Real Stage Implementations ---


class EntityExtractorStage(ExtractStage):
    """ExtractStage using EntityExtractor."""

    def __init__(self, llm_provider: LLMProvider):
        self.extractor = EntityExtractor(llm_provider=llm_provider)

    async def extract_async(
        self, content: str, source_doc: str
    ) -> tuple[list[Entity], list[Concept]]:
        entities = await self.extractor.extract(content, source_doc=source_doc)
        concepts = await self.extractor.extract_concepts(content, source_doc=source_doc)
        return entities, concepts


class WikiPageWriterStage(WriteStage):
    """WriteStage using WikiPageWriter."""

    def __init__(self, wiki_dir: Path):
        self.writer = WikiPageWriter(wiki_dir)

    async def write_async(
        self, entities: list[Entity], concepts: list[Concept]
    ) -> tuple[list[Path], list[Path]]:
        # WikiPageWriter methods are sync (file I/O), wrap in async
        import asyncio
        entity_pages = await asyncio.to_thread(
            lambda: [p for p in (self.writer.write_entity(e) for e in entities if e) if p]
        )
        concept_pages = await asyncio.to_thread(
            lambda: [p for p in (self.writer.write_concept(c) for c in concepts if c) if p]
        )
        return entity_pages, concept_pages


class LinkResolverStage(ResolveStage):
    """ResolveStage using LinkResolver."""

    def __init__(self, wiki_dir: Path):
        self.resolver = LinkResolver(wiki_dir)

    async def resolve_async(self, page_path: Path) -> list[Path]:
        import asyncio
        return await asyncio.to_thread(self.resolver.resolve_all, page_path)


class WikiIndexerStage(IndexStage):
    """IndexStage using WikiIndexer."""

    def __init__(
        self,
        wiki_dir: Path,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
    ):
        self.indexer = WikiIndexer(
            wiki_dir,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )

    async def index_async(self, pages: list[Path]) -> int:
        indexed = 0
        for page in pages:
            try:
                await self.indexer.index_page_async(page)
                indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index {page}: {e}")
        return indexed