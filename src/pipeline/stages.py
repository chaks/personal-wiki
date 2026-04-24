# src/pipeline/stages.py
"""Pipeline stage abstractions for the ingestion pipeline."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from src.extractor import Entity, Concept

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Carries data through the pipeline stages.

    Each stage reads from and writes to this context, allowing
    data to flow through the pipeline.

    Attributes:
        source_path: Path to the source document being ingested
        output_dir: Directory for generated markdown output
        wiki_dir: Root directory for wiki pages
        content: Markdown content (populated after conversion)
        source_doc: Source document name reference
        entities: Extracted entities
        concepts: Extracted concepts
        output_path: Path to generated markdown file
        entity_pages: Paths to created entity pages
        concept_pages: Paths to created concept pages
        error: Error message if a stage failed
        data: Additional stage-specific data
    """
    source_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    wiki_dir: Optional[Path] = None
    content: str = ""
    source_doc: Optional[str] = None
    entities: list[Entity] = field(default_factory=list)
    concepts: list[Concept] = field(default_factory=list)
    output_path: Optional[Path] = None
    entity_pages: list[Path] = field(default_factory=list)
    concept_pages: list[Path] = field(default_factory=list)
    error: Optional[Any] = None
    data: dict[str, Any] = field(default_factory=dict)


class PipelineStage(ABC):
    """Abstract base class for all pipeline stages.

    Each stage receives a PipelineContext, performs its operation,
    and returns the (possibly modified) context.

    Subclasses must implement the execute() method.
    """

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute this stage's operation.

        Args:
            context: The pipeline context carrying data through stages

        Returns:
            The modified (or same) pipeline context
        """
        pass

    def __str__(self) -> str:
        return self.__class__.__name__


class IngestStage(PipelineStage):
    """Base class for ingestion stages.

    Ingestion stages are responsible for reading input data
    and adding it to the pipeline context.
    """

    pass


class TransformStage(PipelineStage):
    """Base class for transformation stages.

    Transformation stages process existing data in the context
    and produce new derived data.
    """

    pass


class OutputStage(PipelineStage):
    """Base class for output stages.

    Output stages write data from the context to external systems
    (files, databases, etc.).
    """

    pass
