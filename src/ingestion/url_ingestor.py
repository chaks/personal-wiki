"""URL ingestion pipeline - fetches and converts web pages to markdown."""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from src.extractor import EntityExtractor
from src.wiki_writer import WikiPageWriter
from src.link_resolver import LinkResolver
from src.indexer import WikiIndexer

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of ingesting a source."""
    success: bool
    output_path: Optional[Path]
    error: Optional[str] = None
    entity_pages: list[Path] = field(default_factory=list)
    concept_pages: list[Path] = field(default_factory=list)


class URLIngestor:
    """Fetches URL content and converts to markdown."""

    def __init__(
        self,
        url: str,
        wiki_dir: Path,
        output_dir: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        """Initialize URL ingestor.

        Args:
            url: URL to ingest
            wiki_dir: Wiki directory for output
            output_dir: Optional specific output directory (default: wiki_dir/generated)
            timeout: HTTP request timeout in seconds
        """
        self.url = url
        self.wiki_dir = Path(wiki_dir)
        self.output_dir = Path(output_dir) if output_dir else self.wiki_dir / "generated"
        self.timeout = timeout
        logger.debug(f"URLIngestor initialized: {url} -> {self.output_dir}")

    def _ensure_dirs(self):
        """Ensure output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_content(self) -> str:
        """Fetch HTML content from URL."""
        logger.info(f"Fetching URL: {self.url}")
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(self.url)
            response.raise_for_status()
            return response.text

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to markdown using Docling."""
        from docling.document_converter import DocumentConverter

        logger.debug("Converting HTML to markdown")
        converter = DocumentConverter()
        result = converter.convert_string(html_content, mime_type="text/html")
        return result.document.export_to_markdown()

    def _generate_output_path(self, title: str) -> Path:
        """Generate output path from page title."""
        slug = title.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c in "-_")
        return self.output_dir / f"{slug}.md"

    def _extract_title(self, html_content: str) -> str:
        """Extract page title from HTML."""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html_content)
        if match:
            return match.group(1).strip()
        return "untitled"

    def ingest(self) -> IngestionResult:
        """Fetch URL, convert to markdown, and extract entities/concepts."""
        logger.info(f"Starting URL ingestion: {self.url}")

        try:
            self._ensure_dirs()

            # Step 1: Fetch content
            html_content = self._fetch_content()

            # Step 2: Convert to markdown
            markdown_content = self._html_to_markdown(html_content)

            # Step 3: Extract title for output path
            title = self._extract_title(html_content)
            output_path = self._generate_output_path(title)

            # Step 4: Write markdown
            output_path.write_text(markdown_content)
            logger.info(f"Wrote markdown to {output_path}")

            # Step 5: Extract entities and concepts
            extractor = EntityExtractor(
                model="gemma4:e2b",
                schema_path=Path(__file__).parent.parent / "config" / "schema.yaml",
            )
            entities = extractor.extract(markdown_content, source_doc=self.url)
            concepts = extractor.extract_concepts(markdown_content, source_doc=self.url)

            # Step 6: Write entity/concept pages
            writer = WikiPageWriter(self.wiki_dir)
            entity_paths = [writer.write_entity(e) for e in entities if e]
            concept_paths = [writer.write_concept(c) for c in concepts if c]

            logger.info(f"Created {len(entity_paths)} entity pages, {len(concept_paths)} concept pages")

            # Step 7: Resolve links
            resolver = LinkResolver(self.wiki_dir)
            resolver.resolve_all(output_path)

            # Step 8: Index in Qdrant
            indexer = WikiIndexer(self.wiki_dir)
            pages_to_index = [output_path] + entity_paths + concept_paths
            for page_path in pages_to_index:
                try:
                    indexer.index_page(page_path)
                except Exception as e:
                    logger.warning(f"Failed to index {page_path}: {e}")

            logger.info(f"URL ingestion successful: {self.url} -> {output_path}")
            return IngestionResult(
                success=True,
                output_path=output_path,
                entity_pages=entity_paths,
                concept_pages=concept_paths,
            )

        except Exception as e:
            logger.error(f"URL ingestion failed for {self.url}: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )
