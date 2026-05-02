from __future__ import annotations
# src/registry.py
"""Source registry with content-hash based change detection."""
import hashlib
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class SourceEntry:
    """Represents a tracked source."""

    def __init__(
        self,
        source_id: str,
        source_type: str,
        path: str | None = None,
        url: str | None = None,
        content_hash: str = "",
        status: SourceStatus = SourceStatus.PENDING,
        wiki_pages: Optional[list[str]] = None,
        tags: list[str] | None = None,
        added_at: str | None = None,
        last_processed_at: str | None = None,
        error: str | None = None,
    ):
        self.source_id = source_id
        self.source_type = source_type
        self.path = path
        self.url = url
        self.content_hash = content_hash
        self.status = status
        self.wiki_pages = wiki_pages or []
        self.tags = tags or []
        self.added_at = added_at or datetime.now(timezone.utc).isoformat()
        self.last_processed_at = last_processed_at
        self.error = error

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "path": self.path,
            "url": self.url,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "wiki_pages": self.wiki_pages,
            "tags": self.tags,
            "added_at": self.added_at,
            "last_processed_at": self.last_processed_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SourceEntry":
        return cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            path=data.get("path"),
            url=data.get("url"),
            content_hash=data.get("content_hash", ""),
            status=SourceStatus(data.get("status", "pending")),
            wiki_pages=data.get("wiki_pages", []),
            tags=data.get("tags", []),
            added_at=data.get("added_at"),
            last_processed_at=data.get("last_processed_at"),
            error=data.get("error"),
        )


class SourceRegistry:
    """Manages source tracking with content-hash based change detection."""

    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self._data: dict = {"sources": [], "wiki_pages": {}, "last_updated": None}
        self._sources: dict[str, SourceEntry] = {}
        logger.debug(f"Initializing SourceRegistry: {registry_path}")
        self._load()

    def _load(self) -> None:
        """Load registry from disk or create empty."""
        if self.registry_path.exists():
            logger.info(f"Loading registry from {self.registry_path}")
            self._data = json.loads(self.registry_path.read_text())
            for source_data in self._data.get("sources", []):
                entry = SourceEntry.from_dict(source_data)
                self._sources[entry.source_id] = entry
            logger.info(f"Loaded {len(self._sources)} sources from registry")
        else:
            logger.info(f"Creating new registry at {self.registry_path}")
            self._save()

    def _save(self) -> None:
        """Persist registry to disk."""
        self._data["sources"] = [e.to_dict() for e in self._sources.values()]
        self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(self._data, indent=2))
        logger.debug(f"Saved registry with {len(self._sources)} sources")

    @staticmethod
    def compute_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file contents."""
        hash_val = hashlib.sha256(file_path.read_bytes()).hexdigest()
        logger.debug(f"Computed hash for {file_path}: {hash_val[:16]}...")
        return hash_val

    def add_source(
        self,
        source_id: str,
        source_type: str,
        path: str,
        content_hash: str,
        url: str | None = None,
        tags: list[str] | None = None,
    ) -> SourceEntry:
        """Add a new source entry."""
        logger.info(f"Adding source: {source_id} (type={source_type})")
        entry = SourceEntry(
            source_id=source_id,
            source_type=source_type,
            path=path,
            url=url,
            content_hash=content_hash,
            tags=tags or [],
        )
        self._sources[source_id] = entry
        self._save()
        return entry

    def get_source(self, source_id: str) -> SourceEntry | None:
        """Retrieve a source entry by ID."""
        return self._sources.get(source_id)

    def get_all_sources(self) -> list[SourceEntry]:
        """Return all source entries."""
        return list(self._sources.values())

    def has_source_changed(self, source_id: str, new_hash: str) -> bool:
        """Check if source content has changed."""
        entry = self._sources.get(source_id)
        if not entry:
            logger.debug(f"Source {source_id} not in registry (changed=True)")
            return True
        changed = entry.content_hash != new_hash
        logger.debug(
            f"Source {source_id} changed: {changed} "
            f"(old={entry.content_hash[:8]}..., new={new_hash[:8]}...)"
        )
        return changed

    def update_status(
        self,
        source_id: str,
        status: SourceStatus,
        error: str | None = None,
    ) -> None:
        """Update source status."""
        entry = self._sources.get(source_id)
        if entry:
            old_status = entry.status
            entry.status = status
            entry.error = error
            if status in (SourceStatus.PROCESSED, SourceStatus.FAILED):
                entry.last_processed_at = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.info(f"Source {source_id} status: {old_status.value} -> {status.value}")
            if error:
                logger.error(f"Source {source_id} error: {error}")

    def link_wiki_page(self, source_id: str, wiki_path: str) -> None:
        """Link a wiki page to a source."""
        entry = self._sources.get(source_id)
        if entry and wiki_path not in entry.wiki_pages:
            entry.wiki_pages.append(wiki_path)
            self._save()

    def record_successful_ingestion(
        self,
        source_id: str,
        source_type: str,
        path: str,
        content_hash: str,
        tags: list[str] | None = None,
        wiki_page_path: str | None = None,
        url: str | None = None,
    ) -> SourceEntry:
        """Record successful ingestion in one call.

        Combines add_source, link_wiki_page, and update_status into
        a single operation for successful ingestions.

        Args:
            source_id: Unique source identifier
            source_type: Type of source (pdf, url, markdown, code)
            path: Source file path
            content_hash: SHA256 hash of source content
            tags: Optional tags
            wiki_page_path: Path to generated wiki page
            url: Optional URL for url-type sources

        Returns:
            The created SourceEntry
        """
        logger.info(f"Recording successful ingestion: {source_id}")

        # Step 1: Add source
        entry = self.add_source(
            source_id=source_id,
            source_type=source_type,
            path=path,
            content_hash=content_hash,
            url=url,
            tags=tags or [],
        )

        # Step 2: Link wiki page
        if wiki_page_path:
            self.link_wiki_page(source_id, wiki_page_path)

        # Step 3: Update status
        self.update_status(source_id, SourceStatus.PROCESSED)

        return entry


# --- Wiki browsing utilities ---


def _list_pages(wiki_dir: Path, namespace: str) -> list[str]:
    """List all page names in a wiki namespace (directory).

    Args:
        wiki_dir: Root wiki directory
        namespace: Subdirectory name (e.g., 'entities', 'concepts')

    Returns:
        Sorted list of page names (filenames without .md extension)
    """
    ns_dir = Path(wiki_dir) / namespace
    pages = []
    if ns_dir.exists():
        for f in ns_dir.glob("*.md"):
            pages.append(f.stem)
    return sorted(pages)


def list_entities(wiki_dir: Path) -> list[str]:
    """List all entity page names in the wiki.

    Args:
        wiki_dir: Root wiki directory

    Returns:
        Sorted list of entity names
    """
    return _list_pages(wiki_dir, "entities")


def list_concepts(wiki_dir: Path) -> list[str]:
    """List all concept page names in the wiki.

    Args:
        wiki_dir: Root wiki directory

    Returns:
        Sorted list of concept names
    """
    return _list_pages(wiki_dir, "concepts")

