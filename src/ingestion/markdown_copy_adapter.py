"""Copy-only markdown adapter — copies markdown files and indexes them."""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from src.indexer import WikiIndexer
from src.ingestion_result import IngestionResult

logger = logging.getLogger(__name__)


class MarkdownCopyAdapter:
    """Copies markdown source files to the wiki directory and indexes them.

    Unlike PDF/URL adapters, this skips conversion, extraction, and link
    resolution. It performs a direct file copy preserving the relative
    path structure, then indexes the result.
    """

    def __init__(
        self,
        source_path: Path,
        wiki_dir: Path,
        indexer: Optional[WikiIndexer] = None,
    ):
        self.source_path = Path(source_path)
        self.wiki_dir = Path(wiki_dir)
        self._indexer = indexer

    def run(self) -> IngestionResult:
        logger.info(f"Copying markdown: {self.source_path}")
        try:
            if not self.source_path.exists():
                return IngestionResult(
                    success=False,
                    output_path=None,
                    error=f"Source not found: {self.source_path}",
                )

            output_path = self._compute_output_path()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(self.source_path.read_text())
            logger.info(f"Copied to {output_path}")

            indexer = self._get_indexer()
            if indexer:
                asyncio.run(indexer.index_page_async(output_path))
                logger.info(f"Indexed {output_path}")

            return IngestionResult(
                success=True,
                output_path=output_path,
            )
        except Exception as e:
            logger.error(f"Markdown copy failed: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )

    def _compute_output_path(self) -> Path:
        """Compute the wiki output path, preserving relative structure.

        For source at 'sources/markdown/notes.md', output goes to
        'wiki/markdown/notes.md' (parent of parent is sources/, so
        relative to that gives 'markdown/notes.md').
        """
        rel = self.source_path.relative_to(self.source_path.parent.parent)
        return self.wiki_dir / rel

    def _get_indexer(self) -> Optional[WikiIndexer]:
        if self._indexer is not None:
            return self._indexer
        from src.services.embedding_provider import OllamaEmbeddingProvider
        return WikiIndexer(
            self.wiki_dir,
            embedding_provider=OllamaEmbeddingProvider(),
        )
