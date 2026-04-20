# src/ingestion.py
"""Docling-based document ingestion pipeline."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.extractor import EntityExtractor
from src.wiki_writer import WikiPageWriter
from src.link_resolver import LinkResolver

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
            "output_path": str(self.output_path),
            "entity_pages": [str(p) for p in self.entity_pages],
            "concept_pages": [str(p) for p in self.concept_pages],
            "error": self.error,
        }


class DoclingIngestor:
    """Converts sources to markdown using Docling."""

    def __init__(self, source_path: Path, output_dir: Path, wiki_dir: Optional[Path] = None):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.wiki_dir = Path(wiki_dir) if wiki_dir else self.output_dir.parent
        logger.debug(f"DoclingIngestor initialized: {source_path} -> {output_dir}, wiki_dir: {self.wiki_dir}")

    def _ensure_dirs(self):
        """Ensure output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self) -> IngestionResult:
        """Convert source to markdown and extract entities/concepts."""
        logger.info(f"Starting ingestion: {self.source_path}")

        try:
            self._ensure_dirs()

            # Step 1: Convert with Docling
            output_path = self._convert_with_docling()

            # Step 2: Extract entities and concepts
            extractor = EntityExtractor(
                model="gemma4:e2b",
                schema_path=Path(__file__).parent.parent / "config" / "schema.yaml",
            )
            content = output_path.read_text()
            source_name = self.source_path.name

            logger.debug(f"Extracting entities from {source_name}")
            entities = extractor.extract(content, source_doc=source_name)
            logger.debug(f"Extracting concepts from {source_name}")
            concepts = extractor.extract_concepts(content, source_doc=source_name)

            # Step 3: Write entity and concept pages
            writer = WikiPageWriter(self.wiki_dir)
            entity_paths = [writer.write_entity(e) for e in entities if e]
            concept_paths = [writer.write_concept(c) for c in concepts if c]

            logger.info(f"Created {len(entity_paths)} entity pages, {len(concept_paths)} concept pages")

            # Step 4: Resolve links
            resolver = LinkResolver(self.wiki_dir)
            resolver.resolve_all(output_path)

            logger.info(
                f"Ingestion successful: {self.source_path.name} -> {output_path} "
                f"({len(entity_paths)} entities, {len(concept_paths)} concepts)"
            )

            return IngestionResult(
                success=True,
                output_path=output_path,
                entity_pages=entity_paths,
                concept_pages=concept_paths,
            )
        except Exception as e:
            logger.error(f"Ingestion failed for {self.source_path}: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )

    def _convert_with_docling(self) -> Path:
        """Convert source to markdown using Docling.

        Returns:
            Path to the generated markdown file
        """
        # Use module-level _DoclingConverter (can be mocked in tests)
        # If not mocked, import the real one
        converter_class = _DoclingConverter
        if converter_class is None:
            from docling.document_converter import DocumentConverter
            converter_class = DocumentConverter
            logger.debug("Using real DocumentConverter from docling")
        else:
            logger.debug("Using mocked DocumentConverter")

        logger.debug(f"Converting document: {self.source_path}")
        converter = converter_class()
        result = converter.convert(str(self.source_path))

        logger.debug("Exporting to markdown")
        markdown_content = result.document.export_to_markdown()

        output_filename = self.source_path.stem + ".md"
        output_path = self.output_dir / output_filename
        output_path.write_text(markdown_content)

        return output_path
