"""Tests for WikiPageCatalog."""
import pytest
from pathlib import Path
import tempfile

from src.catalog import WikiPageCatalog


def test_catalog_find_all_pages():
    """WikiPageCatalog finds all markdown pages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        (wiki_dir / "a.md").write_text("A")
        (wiki_dir / "sub").mkdir()
        (wiki_dir / "sub" / "b.md").write_text("B")

        catalog = WikiPageCatalog(wiki_dir)
        pages = catalog.find_all_pages()

        assert len(pages) == 2
        assert Path(wiki_dir / "a.md") in pages
        assert Path(wiki_dir / "sub" / "b.md") in pages


def test_catalog_find_all_pages_empty():
    """WikiPageCatalog returns empty list for non-existent directory."""
    catalog = WikiPageCatalog(Path("/nonexistent"))
    pages = catalog.find_all_pages()
    assert pages == []


def test_catalog_with_exclude_patterns():
    """WikiPageCatalog can exclude patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        (wiki_dir / "a.md").write_text("A")
        (wiki_dir / "_index.md").write_text("Index")

        catalog = WikiPageCatalog(wiki_dir, exclude_patterns=["_index.md"])
        pages = catalog.find_all_pages()

        assert len(pages) == 1
        assert Path(wiki_dir / "a.md") in pages


def test_catalog_find_existing_slugs():
    """WikiPageCatalog finds all existing slugs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        (wiki_dir / "page-one.md").write_text("A")
        (wiki_dir / "page-two.md").write_text("B")

        catalog = WikiPageCatalog(wiki_dir)
        slugs = catalog.find_existing_slugs()

        assert "page-one" in slugs
        assert "page-two" in slugs