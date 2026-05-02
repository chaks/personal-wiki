from __future__ import annotations
#!/usr/bin/env python3
"""Ingest sources from config/sources.yaml into wiki."""
import asyncio
import logging
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# Initialize logging for CLI
from src.logging_config import setup_logging
root = Path(__file__).parent.parent
setup_logging(log_dir=root / "logs", level=logging.INFO)

logger = logging.getLogger(__name__)

from src.ingestion.adapters import PDFSourceAdapter, URLSourceAdapter, CodeSourceAdapter
from src.ingestion.markdown_copy_adapter import MarkdownCopyAdapter
from src.ingestion_result import IngestionResult
from src.registry import SourceRegistry, SourceStatus
from src.factories import create_default_pipeline_stages


class IngestOutcome(Enum):
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SourceSpec:
    """Canonical representation of a source to ingest."""
    source_type: str
    source_id: str
    file_path: Path | None = None
    url: str | None = None
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    markdown_full_pipeline: bool = False


class Reporter(ABC):
    """Interface for ingestion status reporting."""

    @abstractmethod
    def skip(self, name: str, reason: str): ...
    @abstractmethod
    def ingesting(self, name: str): ...
    @abstractmethod
    def success(self, name: str, output_path: Path): ...
    @abstractmethod
    def failure(self, name: str, error: str): ...
    @abstractmethod
    def copying(self, name: str, output_path: Path): ...


class FileReporter(Reporter):
    """Reports ingestion status to stdout."""

    def skip(self, name: str, reason: str):
        print(f"  [SKIP] {name} ({reason})")

    def ingesting(self, name: str):
        print(f"  [INGEST] {name}...")

    def success(self, name: str, output_path: Path):
        print(f"    -> {output_path}")

    def failure(self, name: str, error: str):
        print(f"    ERROR: {error}")

    def copying(self, name: str, output_path: Path):
        print(f"  [COPY] {name} -> {output_path}")


class NullReporter(Reporter):
    """Silent reporter for testing and non-CLI callers."""

    def skip(self, name: str, reason: str):
        pass

    def ingesting(self, name: str):
        pass

    def success(self, name: str, output_path: Path):
        pass

    def failure(self, name: str, error: str):
        pass

    def copying(self, name: str, output_path: Path):
        pass


def _build_adapter(spec: SourceSpec, wiki_dir: Path):
    """Create the appropriate source adapter for the given source type."""
    if spec.source_type == "url":
        return URLSourceAdapter(url=spec.url, wiki_dir=wiki_dir)
    if spec.source_type == "pdf":
        return PDFSourceAdapter(
            source_path=spec.file_path,
            wiki_dir=wiki_dir,
            output_dir=wiki_dir / "generated",
        )
    if spec.source_type == "markdown" and spec.markdown_full_pipeline:
        return PDFSourceAdapter(
            source_path=spec.file_path,
            wiki_dir=wiki_dir,
            output_dir=wiki_dir / "generated",
        )
    if spec.source_type == "markdown":
        return MarkdownCopyAdapter(source_path=spec.file_path, wiki_dir=wiki_dir)
    if spec.source_type == "code":
        return CodeSourceAdapter(
            code_dir=spec.file_path,
            wiki_dir=wiki_dir,
            language=spec.language or "python",
        )
    return None


def _record_result(
    spec: SourceSpec,
    result,
    wiki_dir: Path,
    registry: SourceRegistry | None,
    reporter: Reporter,
    content_hash: str = "",
) -> IngestOutcome:
    """Record the ingestion result and return the outcome."""
    if result.success:
        reporter.success(spec.file_path.name, result.output_path)
        if registry:
            registry.record_successful_ingestion(
                source_id=spec.source_id,
                source_type=spec.source_type,
                path=str(spec.file_path),
                content_hash=content_hash,
                tags=spec.tags,
                wiki_page_path=str(result.output_path),
            )
        return IngestOutcome.PROCESSED
    else:
        reporter.failure(spec.file_path.name, result.error)
        if registry:
            registry.update_status(spec.source_id, SourceStatus.FAILED, result.error)
        return IngestOutcome.FAILED


async def run_source_async(
    spec: SourceSpec,
    wiki_dir: Path,
    registry: SourceRegistry | None,
    reporter: Reporter,
    stages: dict | None = None,
) -> IngestOutcome:
    """Run ingestion asynchronously for a single source.

    Args:
        spec: What to ingest.
        wiki_dir: Wiki directory.
        registry: Source registry for change tracking.
        reporter: Where to print status.
        stages: Pipeline stages (uses defaults if None).

    Returns:
        Outcome of the ingestion attempt.
    """
    if stages is None:
        stages = create_default_pipeline_stages(wiki_dir)

    # URL source
    if spec.source_type == "url":
        reporter.ingesting(f"URL: {spec.url}")
        adapter = URLSourceAdapter(url=spec.url, wiki_dir=wiki_dir)
        result = await adapter.run_async(
            extract_stage=stages.get("extract"),
            write_stage=stages.get("write"),
            resolve_stage=stages.get("resolve"),
            index_stage=stages.get("index"),
        )

        if result.success:
            reporter.success(f"URL: {spec.url}", result.output_path)
            if registry:
                registry.record_successful_ingestion(
                    source_id=spec.source_id,
                    source_type="url",
                    path=spec.url,
                    content_hash="",
                    tags=spec.tags,
                    wiki_page_path=str(result.output_path),
                )
            return IngestOutcome.PROCESSED
        else:
            reporter.failure(f"URL: {spec.url}", result.error)
            if registry:
                registry.update_status(spec.source_id, SourceStatus.FAILED, result.error)
            return IngestOutcome.FAILED

    # File-based sources
    if spec.file_path and not spec.file_path.exists():
        reporter.skip(str(spec.file_path), "does not exist")
        return IngestOutcome.SKIPPED

    content_hash = ""
    if spec.file_path and registry:
        content_hash = registry.compute_hash(spec.file_path)
        if not registry.has_source_changed(spec.source_id, content_hash):
            reporter.skip(spec.file_path.name, "unchanged")
            return IngestOutcome.SKIPPED

    reporter.ingesting(spec.file_path.name)
    logger.info(f"Ingesting: {spec.file_path.name}")

    adapter = _build_adapter(spec, wiki_dir)
    if adapter is None:
        reporter.failure(spec.source_id, f"Unknown source type: {spec.source_type}")
        return IngestOutcome.FAILED

    result = await adapter.run_async(
        extract_stage=stages.get("extract"),
        write_stage=stages.get("write"),
        resolve_stage=stages.get("resolve"),
        index_stage=stages.get("index"),
    )

    return _record_result(spec, result, wiki_dir, registry, reporter, content_hash)


def run_source(
    spec: SourceSpec,
    wiki_dir: Path,
    registry: SourceRegistry | None,
    reporter: Reporter,
) -> IngestOutcome:
    """Run ingestion for a single source (deprecated sync wrapper)."""
    return asyncio.run(run_source_async(spec, wiki_dir, registry, reporter))


def load_sources(config_path: Path) -> list[dict]:
    """Load sources from YAML config."""
    logger.debug(f"Loading sources from {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    sources = config.get("sources") or []
    logger.info(f"Loaded {len(sources)} sources from config")
    return sources


async def main_async():
    """Async entry point for ingestion."""
    root = Path(__file__).parent.parent
    config_path = root / "config" / "sources.yaml"
    wiki_dir = root / "wiki"
    state_dir = root / "state"

    logger.info("Starting ingestion pipeline (async)")

    registry = SourceRegistry(state_dir / "registry.json")
    sources = load_sources(config_path)

    if not sources:
        logger.warning("No sources configured")
        print("No sources configured")
        return

    print(f"Found {len(sources)} source(s)...\n")

    stages = create_default_pipeline_stages(wiki_dir)

    reporter = FileReporter()
    processed = 0
    skipped = 0
    failed = 0

    for source in sources:
        source_type = source.get("type")
        source_id = f"{source_type}:{source.get('path') or source.get('url')}"
        tags = source.get("tags", [])

        spec = SourceSpec(
            source_type=source_type,
            source_id=source_id,
            file_path=Path(source["path"]) if source.get("path") else None,
            url=source.get("url"),
            language=source.get("language"),
            tags=tags,
            markdown_full_pipeline=source.get("full_pipeline", False),
        )

        outcome = await run_source_async(
            spec, wiki_dir, registry, reporter, stages
        )
        if outcome == IngestOutcome.PROCESSED:
            processed += 1
        elif outcome == IngestOutcome.SKIPPED:
            skipped += 1
        elif outcome == IngestOutcome.FAILED:
            failed += 1

    print(f"\nDone! {processed} processed, {skipped} skipped, {failed} failed")
    logger.info(f"Ingestion complete: {processed} processed, {skipped} skipped, {failed} failed")


def main():
    """Entry point — owns event loop."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
