"""Docling-based document ingestion pipeline — backward-compatible facade."""
import logging
from pathlib import Path
from typing import Optional

from src.pipeline.runner import PipelineRunner
from src.pipeline.stages import (
    PipelineContext,
    PipelineStage,
    ConvertStage,
    ExtractStage,
    WriteStage,
    ResolveStage,
    IndexStage,
)
from src.ingestion_result import IngestionResult

logger = logging.getLogger(__name__)


class DoclingIngestPipeline:
    """Orchestrates the document ingestion pipeline for PDF/Markdown files.

    Uses PipelineRunner with stages:
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
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.wiki_dir = Path(wiki_dir) if wiki_dir else self.output_dir.parent
        self.model = model
        self.schema_path = schema_path

    def _build_pipeline(self) -> PipelineRunner:
        runner = PipelineRunner()
        runner.add_stage(ConvertStage())
        runner.add_stage(ExtractStage(model=self.model, schema_path=self.schema_path))
        runner.add_stage(WriteStage())
        runner.add_stage(ResolveStage())
        runner.add_stage(IndexStage())
        return runner

    def _ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self) -> IngestionResult:
        logger.info(f"Starting ingestion pipeline: {self.source_path}")

        try:
            self._ensure_dirs()

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
