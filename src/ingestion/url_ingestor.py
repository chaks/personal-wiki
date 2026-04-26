"""URL ingestion pipeline — backward-compatible thin wrapper."""
from pathlib import Path
from typing import Optional

from src.ingestion.adapters import URLSourceAdapter
from src.ingestion_result import IngestionResult


class URLIngestor:
    """Fetches URL content and converts to markdown.

    This class delegates to URLSourceAdapter for all work.
    Kept as a thin wrapper for backward compatibility.
    """

    def __init__(
        self,
        url: str,
        wiki_dir: Path,
        output_dir: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        self.url = url
        self._adapter = URLSourceAdapter(
            url=url,
            wiki_dir=wiki_dir,
            output_dir=output_dir,
            timeout=timeout,
        )

    def ingest(self) -> IngestionResult:
        return self._adapter.run()
