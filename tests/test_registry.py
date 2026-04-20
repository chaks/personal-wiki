# tests/test_registry.py
import json
import pytest
from pathlib import Path
from src.registry import SourceRegistry, SourceStatus, SourceEntry


@pytest.fixture
def registry_path(tmp_path):
    return tmp_path / "registry.json"


def test_registry_init_creates_empty_file(registry_path):
    """Registry initialization creates JSON file if not exists."""
    registry = SourceRegistry(registry_path)
    assert registry_path.exists()
    data = json.loads(registry_path.read_text())
    assert data["sources"] == []
    assert data["wiki_pages"] == {}


def test_add_source(registry_path):
    """Adding a source creates an entry with hash and status."""
    registry = SourceRegistry(registry_path)
    entry = registry.add_source(
        source_id="test-pdf",
        source_type="pdf",
        path="sources/test.pdf",
        content_hash="abc123"
    )
    assert entry.source_id == "test-pdf"
    assert entry.status == SourceStatus.PENDING
    assert entry.content_hash == "abc123"


def test_compute_content_hash(registry_path, tmp_path):
    """Content hash is SHA256 of file contents."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert SourceRegistry.compute_hash(test_file) == expected_hash


def test_has_source_changed_detects_new_hash(registry_path):
    """Returns True if content hash differs from stored."""
    registry = SourceRegistry(registry_path)
    registry.add_source("test", "pdf", "sources/test.pdf", "old-hash")
    assert registry.has_source_changed("test", "new-hash") is True
    assert registry.has_source_changed("test", "old-hash") is False


def test_get_source_returns_entry(registry_path):
    """Retrieving a source returns the full entry."""
    registry = SourceRegistry(registry_path)
    registry.add_source("test", "pdf", "sources/test.pdf", "hash1")
    entry = registry.get_source("test")
    assert entry is not None
    assert entry.source_id == "test"


def test_update_source_status(registry_path):
    """Updating status changes entry and timestamp."""
    registry = SourceRegistry(registry_path)
    registry.add_source("test", "pdf", "sources/test.pdf", "hash1")
    registry.update_status("test", SourceStatus.PROCESSED)
    entry = registry.get_source("test")
    assert entry.status == SourceStatus.PROCESSED


def test_link_wiki_page(registry_path):
    """Linking wiki pages records the mapping."""
    registry = SourceRegistry(registry_path)
    registry.add_source("test", "pdf", "sources/test.pdf", "hash1")
    registry.link_wiki_page("test", "wiki/entities/Concept1.md")
    entry = registry.get_source("test")
    assert "wiki/entities/Concept1.md" in entry.wiki_pages


def test_get_all_sources(registry_path):
    """Returns all source entries."""
    registry = SourceRegistry(registry_path)
    registry.add_source("test1", "pdf", "sources/test1.pdf", "hash1")
    registry.add_source("test2", "pdf", "sources/test2.pdf", "hash2")
    sources = registry.get_all_sources()
    assert len(sources) == 2
