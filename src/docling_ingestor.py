# src/ingestion.py
"""Docling-based document ingestion pipeline using pipeline stages."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.extractor import EntityExtractor, Entity, Concept
from src.wiki_writer import WikiPageWriter
from src.link_resolver import LinkResolver
from src.indexer import WikiIndexer
from src.pipeline.stages import PipelineContext, PipelineStage
from src.pipeline.runner import PipelineRunner

logger = logging.getLogger(__name__)

# Placeholder for DoclingConverter - gets replaced when docling is installed
# Tests mock this symbol directly
_DoclingConverter = None


@dataclass
class IngestionResult:
    """Result of ingesting a source."""

    success: bool
    output_path: Optional[Path]
    error: Optional[str] = None
    entity_pages: list[Path] = field(default_factory=list)
    concept_pages: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output_path": str(self.output_path) if self.output_path else None,
            "entity_pages": [str(p) for p in self.entity_pages],
            "concept_pages": [str(p) for p in self.concept_pages],
            "error": self.error,
        }


# ============================================================================
# Pipeline Stages
# ============================================================================

class ConvertStage(PipelineStage):
    """Converts source document to markdown using Docling.

    Reads the source_path from context and outputs markdown content.
    """

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute document conversion.

        Args:
            context: Pipeline context with source_path and output_dir

        Returns:
            Context with content and output_path populated
        """
        logger.info(f"Converting document: {context.source_path}")

        # Use module-level _DoclingConverter (can be mocked in tests)
        converter_class = _DoclingConverter
        if converter_class is None:
            from docling.document_converter import DocumentConverter
            converter_class = DocumentConverter
            logger.debug("Using real DocumentConverter from docling")
        else:
            logger.debug("Using mocked DocumentConverter")

        converter = converter_class()
        result = converter.convert(str(context.source_path))

        markdown_content = result.document.export_to_markdown()

        output_filename = context.source_path.stem + ".md"
        output_path = context.output_dir / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content)

        context.content = markdown_content
        context.output_path = output_path
        context.source_doc = context.source_path.name

        logger.info(f"Converted to markdown: {output_path}")
        return context


class ExtractStage(PipelineStage):
    """Extracts entities and concepts from markdown content.

    Uses EntityExtractor with LLM to extract structured entities and concepts.
    """

    def __init__(
        self,
        model: str = "gemma4:e2b",
        schema_path: Optional[Path] = None,
    ):
        """Initialize the extraction stage.

        Args:
            model: Ollama model to use for extraction
            schema_path: Optional path to schema.yaml for custom prompts
        """
        self.model = model
        self.schema_path = schema_path

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute entity and concept extraction.

        Args:
            context: Pipeline context with content and source_doc

        Returns:
            Context with entities and concepts populated
        """
        logger.info(f"Extracting entities and concepts from: {context.source_doc}")

        extractor = EntityExtractor(
            model=self.model,
            schema_path=self.schema_path,
        )

        context.entities = extractor.extract(context.content, source_doc=context.source_doc)
        context.concepts = extractor.extract_concepts(context.content, source_doc=context.source_doc)

        logger.info(f"Extracted {len(context.entities)} entities and {len(context.concepts)} concepts")
        return context


class WriteStage(PipelineStage):
    """Writes entity and concept pages to the wiki.

    Uses WikiPageWriter to create markdown pages for each extracted entity
    and concept.
    """

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute page writing.

        Args:
            context: Pipeline context with wiki_dir, entities, and concepts

        Returns:
            Context with entity_pages and concept_pages populated
        """
        logger.info(f"Writing entity and concept pages to: {context.wiki_dir}")

        writer = WikiPageWriter(context.wiki_dir)

        context.entity_pages = [
            path for path in
            (writer.write_entity(e) for e in context.entities if e)
            if path is not None
        ]
        context.concept_pages = [
            path for path in
            (writer.write_concept(c) for c in context.concepts if c)
            if path is not None
        ]

        logger.info(f"Created {len(context.entity_pages)} entity pages, "
                    f"{len(context.concept_pages)} concept pages")
        return context


class ResolveStage(PipelineStage):
    """Resolves wiki links and creates placeholder pages.

    Uses LinkResolver to find missing links in the output markdown
    and creates placeholder pages for them.
    """

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute link resolution.

        Args:
            context: Pipeline context with wiki_dir and output_path

        Returns:
            Context with resolved link placeholders created
        """
        logger.info(f"Resolving wiki links in: {context.output_path}")

        resolver = LinkResolver(context.wiki_dir)
        resolver.resolve_all(context.output_path)

        logger.info("Link resolution complete")
        return context


class IndexStage(PipelineStage):
    """Indexes all generated pages in Qdrant for semantic search.

    Uses WikiIndexer to embed and index the output markdown file
    and all generated entity/concept pages.
    """

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute page indexing.

        Args:
            context: Pipeline context with wiki_dir, output_path,
                     entity_pages, and concept_pages

        Returns:
            Context with all pages indexed
        """
        logger.info("Indexing pages in Qdrant")

        indexer = WikiIndexer(context.wiki_dir)
        pages_to_index = [context.output_path] + context.entity_pages + context.concept_pages

        indexed_count = 0
        for page_path in pages_to_index:
            try:
                indexer.index_page(page_path)
                indexed_count += 1
                logger.debug(f"Indexed: {page_path}")
            except Exception as e:
                logger.warning(f"Failed to index {page_path}: {e}")

        logger.info(f"Indexed {indexed_count} pages in Qdrant")
        return context


# ============================================================================
# Pipeline Orchestrator
# ============================================================================

class DoclingIngestPipeline:
    """Orchestrates the document ingestion pipeline.

    Replaces the monolithic DoclingIngestor with a composable pipeline
    of stages:
    1. Convert - Convert source to markdown using Docling
    2. Extract - Extract entities and concepts using LLM
    3. Write - Write entity and concept pages to wiki
    4. Resolve - Resolve wiki links and create placeholders
    5. Index - Index all pages in Qdrant
    """

    def __init__(
        self,
        source_path: Path,
        output_dir: Path,
        wiki_dir: Optional[Path] = None,
        model: str = "gemma4:e2b",
        schema_path: Optional[Path] = None,
    ):
        """Initialize the ingestion pipeline.

        Args:
            source_path: Path to source document to ingest
            output_dir: Directory for generated markdown output
            wiki_dir: Root directory for wiki pages (defaults to output_dir.parent)
            model: Ollama model for entity/concept extraction
            schema_path: Optional path to schema.yaml for custom prompts
        """
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.wiki_dir = Path(wiki_dir) if wiki_dir else self.output_dir.parent
        self.model = model
        self.schema_path = schema_path

        logger.debug(f"DoclingIngestPipeline initialized: "
                     f"{self.source_path} -> {self.output_dir}, "
                     f"wiki_dir: {self.wiki_dir}")

    def _build_pipeline(self) -> PipelineRunner:
        """Build the pipeline with all stages.

        Returns:
            Configured PipelineRunner with all stages
        """
        runner = PipelineRunner()
        runner.add_stage(ConvertStage())
        runner.add_stage(ExtractStage(model=self.model, schema_path=self.schema_path))
        runner.add_stage(WriteStage())
        runner.add_stage(ResolveStage())
        runner.add_stage(IndexStage())
        return runner

    def _ensure_dirs(self):
        """Ensure output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self) -> IngestionResult:
        """Run the ingestion pipeline.

        Returns:
            IngestionResult with success status and output paths
        """
        logger.info(f"Starting ingestion pipeline: {self.source_path}")

        try:
            self._ensure_dirs()

            # Build and run pipeline
            runner = self._build_pipeline()
            context = PipelineContext(
                source_path=self.source_path,
                output_dir=self.output_dir,
                wiki_dir=self.wiki_dir,
            )

            result_context = runner.run(context)

            logger.info(
                f"Ingestion successful: {self.source_path.name} -> {result_context.output_path} "
                f"({len(result_context.entity_pages)} entities, "
                f"{len(result_context.concept_pages)} concepts)"
            )

            return IngestionResult(
                success=True,
                output_path=result_context.output_path,
                entity_pages=result_context.entity_pages,
                concept_pages=result_context.concept_pages,
            )

        except Exception as e:
            logger.error(f"Ingestion failed for {self.source_path}: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )


# Backward compatibility alias
DoclingIngestor = DoclingIngestPipeline
