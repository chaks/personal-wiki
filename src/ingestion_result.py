"""Canonical IngestionResult dataclass."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
