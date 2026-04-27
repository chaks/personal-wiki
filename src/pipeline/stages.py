"""Pipeline stage abstractions for the ingestion pipeline."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Carries data through the pipeline stages."""
    source_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    wiki_dir: Optional[Path] = None
    content: str = ""
    source_doc: Optional[str] = None
    entities: list = field(default_factory=list)
    concepts: list = field(default_factory=list)
    output_path: Optional[Path] = None
    entity_pages: list[Path] = field(default_factory=list)
    concept_pages: list[Path] = field(default_factory=list)
    error: Optional[Any] = None
    data: dict[str, Any] = field(default_factory=dict)


class PipelineStage(ABC):
    """Abstract base class for all pipeline stages."""

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute this stage's operation."""
        pass

    def __str__(self) -> str:
        return self.__class__.__name__


class ConvertStage(PipelineStage):
    """Converts source document to markdown using Docling."""

    def __init__(self, converter):
        self.converter = converter

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Converting document: {context.source_path}")

        result = self.converter.convert(str(context.source_path))

        markdown_content = result.document.export_to_markdown()

        output_filename = context.source_path.stem + ".md"
        output_path = context.output_dir / output_filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content)

        context.content = markdown_content
        context.output_path = output_path
        context.source_doc = context.source_path.name

        logger.info(f"Converted to markdown: {output_path}")
        return context


class ExtractStage(PipelineStage):
    """Extracts entities and concepts from markdown content."""

    def __init__(self, extractor):
        self.extractor = extractor

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Extracting entities and concepts from: {context.source_doc}")

        context.entities = self.extractor.extract(context.content, source_doc=context.source_doc)
        context.concepts = self.extractor.extract_concepts(context.content, source_doc=context.source_doc)

        logger.info(f"Extracted {len(context.entities)} entities and {len(context.concepts)} concepts")
        return context


class WriteStage(PipelineStage):
    """Writes entity and concept pages to the wiki."""

    def __init__(self, writer):
        self.writer = writer

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Writing entity and concept pages to: {context.wiki_dir}")

        context.entity_pages = [
            path for path in
            (self.writer.write_entity(e) for e in context.entities if e)
            if path is not None
        ]
        context.concept_pages = [
            path for path in
            (self.writer.write_concept(c) for c in context.concepts if c)
            if path is not None
        ]

        logger.info(f"Created {len(context.entity_pages)} entity pages, "
                    f"{len(context.concept_pages)} concept pages")
        return context


class ResolveStage(PipelineStage):
    """Resolves wiki links and creates placeholder pages."""

    def __init__(self, resolver):
        self.resolver = resolver

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Resolving wiki links in: {context.output_path}")

        self.resolver.resolve_all(context.output_path)

        logger.info("Link resolution complete")
        return context


class IndexStage(PipelineStage):
    """Indexes all generated pages in Qdrant for semantic search."""

    def __init__(self, indexer):
        self.indexer = indexer

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info("Indexing pages in Qdrant")

        pages_to_index = [context.output_path] + context.entity_pages + context.concept_pages

        indexed_count = 0
        for page_path in pages_to_index:
            try:
                self.indexer.index_page(page_path)
                indexed_count += 1
                logger.debug(f"Indexed: {page_path}")
            except Exception as e:
                logger.warning(f"Failed to index {page_path}: {e}")

        logger.info(f"Indexed {indexed_count} pages in Qdrant")
        return context
