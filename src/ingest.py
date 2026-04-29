#!/usr/bin/env python3
"""Ingest sources from config/sources.yaml into wiki."""
import logging
import sys
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logging for CLI
from src.logging_config import setup_logging
root = Path(__file__).parent.parent
setup_logging(log_dir=root / "logs", level=logging.INFO)

logger = logging.getLogger(__name__)

from src.ingestion.adapters import PDFSourceAdapter, URLSourceAdapter, CodeSourceAdapter
from src.ingestion.markdown_copy_adapter import MarkdownCopyAdapter
from src.ingestion_result import IngestionResult
from src.registry import SourceRegistry, SourceStatus


class IngestOutcome(Enum):
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SourceSpec:
    """Canonical representation of a source to ingest."""
    source_type: str
    source_id: str
    file_path: Path = None
    url: str = None
    language: str = None
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


def run_source(
    spec: SourceSpec,
    wiki_dir: Path,
    registry: Optional[SourceRegistry],
    reporter: Reporter,
) -> IngestOutcome:
    """Run ingestion for a single source.

    Args:
        spec: What to ingest.
        wiki_dir: Wiki directory.
        registry: Source registry for change tracking (None to skip).
        reporter: Where to print status.

    Returns:
        Outcome of the ingestion attempt.
    """
    if spec.source_type == "url":
        reporter.ingesting(f"URL: {spec.url}")
        adapter = URLSourceAdapter(url=spec.url, wiki_dir=wiki_dir)
        result = adapter.run()

        if result.success:
            reporter.success(f"URL: {spec.url}", result.output_path)
            if registry:
                registry.add_source(
                    source_id=spec.source_id,
                    source_type="url",
                    path=spec.url,
                    content_hash="",
                    tags=spec.tags,
                )
                registry.link_wiki_page(spec.source_id, str(result.output_path))
                registry.update_status(spec.source_id, SourceStatus.PROCESSED)
            return IngestOutcome.PROCESSED
        else:
            reporter.failure(f"URL: {spec.url}", result.error)
            if registry:
                registry.update_status(spec.source_id, SourceStatus.FAILED, result.error)
            return IngestOutcome.FAILED

    # File-based sources (pdf, markdown)
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

    if spec.source_type == "pdf" or (spec.source_type == "markdown" and spec.markdown_full_pipeline):
        adapter = PDFSourceAdapter(
            source_path=spec.file_path,
            wiki_dir=wiki_dir,
            output_dir=wiki_dir / "generated",
        )
    elif spec.source_type == "markdown":
        # Copy-only path: handled by caller
        return IngestOutcome.SKIPPED
    elif spec.source_type == "code":
        adapter = CodeSourceAdapter(
            code_dir=spec.file_path,
            wiki_dir=wiki_dir,
            language=spec.language or "python",
        )
    else:
        reporter.failure(spec.source_id, f"Unknown source type: {spec.source_type}")
        return IngestOutcome.FAILED

    result = adapter.run()

    if result.success:
        reporter.success(spec.file_path.name, result.output_path)
        if registry:
            registry.add_source(
                source_id=spec.source_id,
                source_type=spec.source_type,
                path=str(spec.file_path),
                content_hash=content_hash,
                tags=spec.tags,
            )
            registry.link_wiki_page(spec.source_id, str(result.output_path))
            registry.update_status(spec.source_id, SourceStatus.PROCESSED)
        return IngestOutcome.PROCESSED
    else:
        reporter.failure(spec.file_path.name, result.error)
        if registry:
            registry.update_status(spec.source_id, SourceStatus.FAILED, result.error)
        return IngestOutcome.FAILED


def load_sources(config_path: Path) -> list[dict]:
    """Load sources from YAML config."""
    logger.debug(f"Loading sources from {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    sources = config.get("sources") or []
    logger.info(f"Loaded {len(sources)} sources from config")
    return sources


def main():
    root = Path(__file__).parent.parent
    config_path = root / "config" / "sources.yaml"
    wiki_dir = root / "wiki"
    state_dir = root / "state"

    logger.info("Starting ingestion pipeline")

    registry = SourceRegistry(state_dir / "registry.json")
    sources = load_sources(config_path)

    if not sources:
        logger.warning("No sources configured in config/sources.yaml")
        print("No sources configured in config/sources.yaml")
        return

    print(f"Found {len(sources)} source(s) to ingest...\n")
    logger.info(f"Found {len(sources)} sources to ingest")

    reporter = FileReporter()
    processed = 0
    skipped = 0
    failed = 0

    for source in sources:
        source_type = source.get("type")
        source_id = f"{source_type}:{source.get('path') or source.get('url')}"
        tags = source.get("tags", [])

        if source_type == "markdown" and not source.get("full_pipeline", False):
            source_path = Path(source["path"])
            if not source_path.exists():
                reporter.skip(str(source_path), "does not exist")
                skipped += 1
                continue

            adapter = MarkdownCopyAdapter(source_path=source_path, wiki_dir=wiki_dir)
            result = adapter.run()
            if result.success:
                reporter.copying(source_path.name, result.output_path)
                registry.link_wiki_page(source_id, str(result.output_path))
                registry.update_status(source_id, SourceStatus.PROCESSED)
                processed += 1
            else:
                reporter.failure(source_path.name, result.error)
                registry.update_status(source_id, SourceStatus.FAILED, result.error)
                failed += 1
            continue

        spec = SourceSpec(
            source_type=source_type,
            source_id=source_id,
            file_path=Path(source["path"]) if source.get("path") else None,
            url=source.get("url"),
            language=source.get("language"),
            tags=tags,
            markdown_full_pipeline=source.get("full_pipeline", False),
        )

        outcome = run_source(spec, wiki_dir=wiki_dir, registry=registry, reporter=reporter)
        if outcome == IngestOutcome.PROCESSED:
            processed += 1
        elif outcome == IngestOutcome.SKIPPED:
            skipped += 1
        elif outcome == IngestOutcome.FAILED:
            failed += 1

    print("\nDone! Check the wiki/ directory for generated markdown files.")
    logger.info(f"Ingestion complete: {processed} processed, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
