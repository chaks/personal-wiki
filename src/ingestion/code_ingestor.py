"""Code ingestion pipeline — backward-compatible thin wrapper."""
from pathlib import Path
from typing import Optional

from src.ingestion.adapters import CodeSourceAdapter
from src.ingestion_result import IngestionResult


class CodeIngestor:
    """Processes code repositories and generates documentation.

    This class delegates to CodeSourceAdapter for all work.
    Kept as a thin wrapper for backward compatibility.
    """

    def __init__(
        self,
        code_dir: Path,
        wiki_dir: Path,
        language: str = "python",
        output_dir: Optional[Path] = None,
    ):
        self.code_dir = code_dir
        self.language = language
        self._adapter = CodeSourceAdapter(
            code_dir=code_dir,
            wiki_dir=wiki_dir,
            language=language,
            output_dir=output_dir,
        )

    def ingest(self) -> IngestionResult:
        return self._adapter.run()
