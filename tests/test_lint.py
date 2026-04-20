# tests/test_lint.py
"""Tests for WikiLinter class."""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.lint import WikiLinter


@pytest.fixture
def wiki_dir():
    """Create a temporary wiki directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def linter(wiki_dir):
    """Create a WikiLinter instance."""
    return WikiLinter(wiki_dir)


class TestWikiLinterInitialization:
    """Tests for WikiLinter initialization."""

    def test_linter_stores_wiki_dir(self, wiki_dir):
        """WikiLinter stores the wiki directory."""
        linter = WikiLinter(wiki_dir)
        assert linter.wiki_dir == wiki_dir


class TestSlugify:
    """Tests for _slugify method."""

    def test_slugify_simple_name(self, linter):
        """Slugify converts simple name to slug."""
        assert linter._slugify("Andrej Karpathy") == "andrej-karpathy"

    def test_slugify_lowercase(self, linter):
        """Slugify converts to lowercase."""
        assert linter._slugify("TEST") == "test"

    def test_slugify_spaces(self, linter):
        """Slugify replaces spaces with hyphens."""
        assert linter._slugify("Deep Learning") == "deep-learning"

    def test_slugify_special_characters(self, linter):
        """Slugify removes special characters."""
        assert linter._slugify("C++") == "c"
        assert linter._slugify("Test/Path") == "test-path"

    def test_slugify_preserves_alphanumeric(self, linter):
        """Slugify preserves alphanumeric characters and hyphens."""
        assert linter._slugify("GPT-4") == "gpt-4"
        assert linter._slugify("Python_3") == "python_3"


class TestOrphanDetection:
    """Tests for orphan page detection."""

    def test_detect_orphan_pages(self, linter, wiki_dir):
        """Verify orphan detection works - pages with no incoming wikilinks are orphans."""
        # Create entities directory
        entities_dir = wiki_dir / "entities"
        entities_dir.mkdir()

        # Create two pages: one linked, one orphan
        linked_page = entities_dir / "linked-page.md"
        linked_page.write_text("---\ntitle: Linked Page\n---\n# Linked Page\n\nContent here.\n")

        orphan_page = entities_dir / "orphan-page.md"
        orphan_page.write_text("---\ntitle: Orphan Page\n---\n# Orphan Page\n\nNo links to this.\n")

        # Create a page that links to linked-page
        linker_page = entities_dir / "linker-page.md"
        linker_page.write_text("---\ntitle: Linker Page\n---\n# Linker Page\n\nSee [[Linked Page]] for more.\n")

        orphans = linter.check_orphans()

        # orphan-page.md should be detected as orphan (no incoming links)
        orphan_paths = [p.name for p in orphans]
        assert "orphan-page.md" in orphan_paths
        # linked-page.md should NOT be an orphan (it's linked from linker-page)
        assert "linked-page.md" not in orphan_paths
        # linker-page.md should NOT be an orphan (even if nothing links to it, it's not the test case)

    def test_no_orphans_when_all_linked(self, linter, wiki_dir):
        """Verify no false positives - when all pages are linked, no orphans detected."""
        # Create entities directory
        entities_dir = wiki_dir / "entities"
        entities_dir.mkdir()

        # Create pages that all link to each other
        page_a = entities_dir / "page-a.md"
        page_a.write_text("---\ntitle: Page A\n---\n# Page A\n\nSee [[Page B]].\n")

        page_b = entities_dir / "page-b.md"
        page_b.write_text("---\ntitle: Page B\n---\n# Page B\n\nSee [[Page A]].\n")

        orphans = linter.check_orphans()

        # No orphans should be detected
        assert len(orphans) == 0

    def test_all_pages_orphan_when_no_links(self, linter, wiki_dir):
        """When no pages have wikilinks, all pages are orphans."""
        # Create entities directory
        entities_dir = wiki_dir / "entities"
        entities_dir.mkdir()

        # Create pages with no wikilinks
        page_a = entities_dir / "page-a.md"
        page_a.write_text("---\ntitle: Page A\n---\n# Page A\n\nNo links here.\n")

        page_b = entities_dir / "page-b.md"
        page_b.write_text("---\ntitle: Page B\n---\n# Page B\n\nAlso no links.\n")

        orphans = linter.check_orphans()

        # All pages should be orphans
        assert len(orphans) == 2
        orphan_names = [p.name for p in orphans]
        assert "page-a.md" in orphan_names
        assert "page-b.md" in orphan_names


class TestRunAllChecks:
    """Tests for run_all_checks method."""

    def test_run_all_checks_returns_dict(self, linter):
        """run_all_checks returns a dictionary with all check categories."""
        results = linter.run_all_checks()

        assert isinstance(results, dict)
        assert "orphans" in results
        assert "contradictions" in results
        assert "stale_claims" in results
        assert "broken_links" in results
        assert "duplicates" in results

    def test_run_all_checks_stub_returns_empty_lists(self, linter):
        """Non-orphan checks return empty lists as stubs."""
        results = linter.run_all_checks()

        # These are stubs that should return empty lists
        assert results["contradictions"] == []
        assert results["stale_claims"] == []
        assert results["broken_links"] == []
        assert results["duplicates"] == []
