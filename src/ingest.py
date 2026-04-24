#!/usr/bin/env python3
"""Ingest sources from config/sources.yaml into wiki."""
import logging
import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logging for CLI
from src.logging_config import setup_logging
root = Path(__file__).parent.parent
setup_logging(log_dir=root / "logs", level=logging.INFO)

logger = logging.getLogger(__name__)

from src.ingestion import DoclingIngestor
from src.registry import SourceRegistry, SourceStatus


def load_sources(config_path: Path) -> list[dict]:
    """Load sources from YAML config."""
    logger.debug(f"Loading sources from {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    sources = config.get("sources", [])
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

    processed = 0
    skipped = 0
    failed = 0

    for source in sources:
        source_type = source.get("type")
        source_id = f"{source_type}:{source.get('path') or source.get('url')}"
        tags = source.get("tags", [])

        if source_type == "pdf":
            source_path = Path(source["path"])
            if not source_path.exists():
                print(f"  [SKIP] {source_path} does not exist")
                logger.warning(f"Source not found: {source_path}")
                skipped += 1
                continue

            content_hash = registry.compute_hash(source_path)
            if not registry.has_source_changed(source_id, content_hash):
                print(f"  [SKIP] {source_path.name} (unchanged)")
                logger.debug(f"Source unchanged: {source_path.name}")
                skipped += 1
                continue

            print(f"  [INGEST] {source_path.name}...")
            logger.info(f"Ingesting: {source_path.name}")
            ingestor = DoclingIngestor(source_path, wiki_dir / "generated", wiki_dir=wiki_dir)
            result = ingestor.ingest()

            if result.success:
                print(f"    -> {result.output_path}")
                logger.info(f"Ingested {source_path.name} -> {result.output_path}")
                registry.add_source(
                    source_id=source_id,
                    source_type=source_type,
                    path=str(source_path),
                    content_hash=content_hash,
                    tags=tags,
                )
                registry.link_wiki_page(source_id, str(result.output_path))
                registry.update_status(source_id, SourceStatus.PROCESSED)
                processed += 1
            else:
                print(f"    ERROR: {result.error}")
                logger.error(f"Ingestion failed: {result.error}")
                registry.update_status(source_id, SourceStatus.FAILED, result.error)
                failed += 1

        elif source_type == "markdown":
            source_path = Path(source["path"])
            if not source_path.exists():
                print(f"  [SKIP] {source_path} does not exist")
                logger.warning(f"Markdown not found: {source_path}")
                skipped += 1
                continue
            # Markdown files are already in wiki format, just copy
            output_path = wiki_dir / source_path.relative_to(source_path.parent.parent)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(source_path.read_text())
            print(f"  [COPY] {source_path.name} -> {output_path}")
            logger.info(f"Copied markdown: {source_path.name} -> {output_path}")

            # Index the copied markdown file
            from src.indexer import WikiIndexer
            indexer = WikiIndexer(wiki_dir)
            indexer.index_page(output_path)
            logger.info(f"Indexed {output_path} in Qdrant")
            processed += 1

        elif source_type == "url":
            from src.ingestion.url_ingestor import URLIngestor

            url = source["url"]
            print(f"  [INGEST] URL: {url}...")
            logger.info(f"Ingesting URL: {url}")

            ingestor = URLIngestor(url=url, wiki_dir=wiki_dir)
            result = ingestor.ingest()

            if result.success:
                print(f"    -> {result.output_path}")
                logger.info(f"Ingested URL {url} -> {result.output_path}")
                registry.add_source(
                    source_id=f"url:{url}",
                    source_type="url",
                    path=url,
                    tags=tags,
                )
                registry.link_wiki_page(f"url:{url}", str(result.output_path))
                registry.update_status(f"url:{url}", SourceStatus.PROCESSED)
                processed += 1
            else:
                print(f"    ERROR: {result.error}")
                logger.error(f"URL ingestion failed: {result.error}")
                registry.update_status(f"url:{url}", SourceStatus.FAILED, result.error)
                failed += 1

        elif source_type == "code":
            from src.ingestion.code_ingestor import CodeIngestor

            code_path = Path(source["path"])
            language = source.get("language", "python")

            if not code_path.exists():
                print(f"  [SKIP] Code path does not exist: {code_path}")
                logger.warning(f"Code path not found: {code_path}")
                skipped += 1
                continue

            print(f"  [INGEST] Code ({language}): {code_path}...")
            logger.info(f"Ingesting code ({language}): {code_path}")

            ingestor = CodeIngestor(code_dir=code_path, wiki_dir=wiki_dir, language=language)
            result = ingestor.ingest()

            if result.success:
                if result.output_path:
                    print(f"    -> {result.output_path}")
                    logger.info(f"Ingested code {code_path} -> {result.output_path}")
                    registry.add_source(
                        source_id=f"code:{code_path}:{language}",
                        source_type="code",
                        path=str(code_path),
                        tags=tags,
                    )
                    registry.link_wiki_page(f"code:{code_path}:{language}", str(result.output_path))
                    registry.update_status(f"code:{code_path}:{language}", SourceStatus.PROCESSED)
                processed += 1
            else:
                print(f"    ERROR: {result.error}")
                logger.error(f"Code ingestion failed: {result.error}")
                registry.update_status(f"code:{code_path}:{language}", SourceStatus.FAILED, result.error)
                failed += 1

    print("\nDone! Check the wiki/ directory for generated markdown files.")
    logger.info(f"Ingestion complete: {processed} processed, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
