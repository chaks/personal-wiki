# tests/test_link_resolver.py
"""Tests for link_resolver module."""
import logging
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.link_resolver import LinkResolver


@pytest.fixture
def wiki_dir():
    """Create a temporary wiki directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def resolver(wiki_dir):
    """Create a LinkResolver instance."""
    return LinkResolver(wiki_dir)


@pytest.fixture
def setup_wiki_structure(wiki_dir):
    """Create a wiki directory structure with some existing pages."""
    entities_dir = wiki_dir / "entities"
    concepts_dir = wiki_dir / "concepts"
    entities_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # Create some existing pages
    (entities_dir / "existing-entity.md").write_text("---\ntitle: Existing Entity\n---\n# Existing Entity")
    (concepts_dir / "existing-concept.md").write_text("---\ntitle: Existing Concept\n---\n# Existing Concept")

    return wiki_dir


class TestLinkResolverInitialization:
    """Tests for LinkResolver initialization."""

    def test_resolver_sets_paths(self, wiki_dir):
        """LinkResolver sets correct paths."""
        resolver = LinkResolver(wiki_dir)
        assert resolver.wiki_dir == wiki_dir
        assert resolver.entities_dir == wiki_dir / "entities"
        assert resolver.concepts_dir == wiki_dir / "concepts"

    def test_resolver_raises_for_non_directory(self, wiki_dir):
        """LinkResolver raises NotADirectoryError when wiki_dir is not a directory."""
        non_dir_path = wiki_dir / "nonexistent" / "path"
        with pytest.raises(NotADirectoryError):
            LinkResolver(non_dir_path)

    def test_resolver_raises_for_file(self, wiki_dir):
        """LinkResolver raises NotADirectoryError when wiki_dir is a file."""
        test_file = wiki_dir / "test.txt"
        test_file.write_text("test content")
        with pytest.raises(NotADirectoryError):
            LinkResolver(test_file)


class TestExtractLinks:
    """Tests for extract_links method."""

    def test_extract_links_single_link(self, resolver):
        """extract_links extracts a single wikilink."""
        content = "This references [[Some Entity]] in the text."
        links = resolver.extract_links(content)
        assert links == ["Some Entity"]

    def test_extract_links_multiple_links(self, resolver):
        """extract_links extracts multiple wikilinks."""
        content = "See [[Entity One]] and [[Entity Two]] for more info."
        links = resolver.extract_links(content)
        assert links == ["Entity One", "Entity Two"]

    def test_extract_links_no_links(self, resolver):
        """extract_links returns empty list when no wikilinks present."""
        content = "This content has no wikilinks."
        links = resolver.extract_links(content)
        assert links == []

    def test_extract_links_duplicate_links(self, resolver):
        """extract_links returns all occurrences including duplicates."""
        content = "[[Test]] appears twice like [[Test]]."
        links = resolver.extract_links(content)
        assert links == ["Test", "Test"]

    def test_extract_links_with_hyphens(self, resolver):
        """extract_links handles links with hyphens."""
        content = "Check out [[Deep Learning]] and [[GPT-4]]."
        links = resolver.extract_links(content)
        assert links == ["Deep Learning", "GPT-4"]

    def test_extract_links_multiline_content(self, resolver):
        """extract_links works with multiline content."""
        content = """
        # Documentation

        This references [[Entity A]].

        Also see [[Entity B]] for details.
        """
        links = resolver.extract_links(content)
        assert links == ["Entity A", "Entity B"]


class TestPageExists:
    """Tests for page_exists method."""

    def test_page_exists_finds_entity_page(self, setup_wiki_structure):
        """page_exists returns True for existing entity page."""
        resolver = LinkResolver(setup_wiki_structure)
        assert resolver.page_exists("Existing Entity") is True

    def test_page_exists_finds_concept_page(self, setup_wiki_structure):
        """page_exists returns True for existing concept page."""
        resolver = LinkResolver(setup_wiki_structure)
        assert resolver.page_exists("Existing Concept") is True

    def test_page_exists_returns_false_for_missing_page(self, wiki_dir):
        """page_exists returns False when page doesn't exist."""
        resolver = LinkResolver(wiki_dir)
        # Create directories but no pages
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)
        (wiki_dir / "concepts").mkdir(parents=True, exist_ok=True)
        assert resolver.page_exists("Nonexistent Entity") is False

    def test_page_exists_case_insensitive_slug(self, setup_wiki_structure):
        """page_exists correctly slugifies regardless of case."""
        resolver = LinkResolver(setup_wiki_structure)
        # Should find "existing-entity.md" regardless of case
        assert resolver.page_exists("EXISTING ENTITY") is True
        assert resolver.page_exists("existing entity") is True


class TestCreatePlaceholder:
    """Tests for create_placeholder method."""

    def test_create_placeholder_creates_file(self, wiki_dir):
        """create_placeholder creates a markdown file in entities directory."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        output_path = resolver.create_placeholder("New Entity")

        assert output_path.exists()
        assert output_path.parent == wiki_dir / "entities"
        assert output_path.name == "new-entity.md"

    def test_create_placeholder_has_frontmatter(self, wiki_dir):
        """create_placeholder creates file with valid frontmatter."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        output_path = resolver.create_placeholder("Test Entity")
        content = output_path.read_text()

        assert content.startswith("---")
        assert "title: Test Entity" in content
        assert "category: entity" in content
        assert "created_at:" in content
        assert "---" in content

    def test_create_placeholder_has_body(self, wiki_dir):
        """create_placeholder creates file with body content."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        output_path = resolver.create_placeholder("Test Entity")
        content = output_path.read_text()

        assert "# Test Entity" in content

    def test_create_placeholder_returns_path(self, wiki_dir):
        """create_placeholder returns the Path to created file."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        output_path = resolver.create_placeholder("Test Entity")

        assert isinstance(output_path, Path)
        assert output_path.is_absolute()


class TestFindMissingLinks:
    """Tests for find_missing_links method."""

    def test_find_missing_links_identifies_missing(self, setup_wiki_structure):
        """find_missing_links returns links that don't have pages."""
        resolver = LinkResolver(setup_wiki_structure)

        # Create a page with links to existing and non-existing pages
        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Missing Entity]] and [[Existing Entity]].")

        missing = resolver.find_missing_links(test_page)

        assert "Missing Entity" in missing
        assert "Existing Entity" not in missing

    def test_find_missing_links_empty_when_all_exist(self, setup_wiki_structure):
        """find_missing_links returns empty list when all pages exist."""
        resolver = LinkResolver(setup_wiki_structure)

        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Existing Entity]].")

        missing = resolver.find_missing_links(test_page)

        assert missing == []

    def test_find_missing_links_reads_from_file(self, wiki_dir):
        """find_missing_links reads content from the given file path."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        test_page = wiki_dir / "entities" / "test.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nLinks to [[Some Entity]].")

        missing = resolver.find_missing_links(test_page)

        assert "Some Entity" in missing

    def test_find_missing_links_handles_read_failure(self, wiki_dir, caplog):
        """find_missing_links returns empty list when file read fails."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        # Use a path that doesn't exist and can't be read
        nonexistent_path = wiki_dir / "nonexistent" / "page.md"

        with caplog.at_level(logging.ERROR):
            missing = resolver.find_missing_links(nonexistent_path)

        assert missing == []
        assert "Failed to read page" in caplog.text


class TestResolveAll:
    """Tests for resolve_all method."""

    def test_resolve_all_creates_missing_pages(self, setup_wiki_structure):
        """resolve_all creates placeholder pages for missing links."""
        resolver = LinkResolver(setup_wiki_structure)

        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Missing Entity]].")

        created_paths = resolver.resolve_all(test_page)

        assert len(created_paths) == 1
        assert created_paths[0].exists()
        assert "missing-entity.md" in str(created_paths[0])

    def test_resolve_all_returns_list_of_paths(self, setup_wiki_structure):
        """resolve_all returns list of created placeholder paths."""
        resolver = LinkResolver(setup_wiki_structure)

        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Entity A]] and [[Entity B]].")

        created_paths = resolver.resolve_all(test_page)

        assert isinstance(created_paths, list)
        for path in created_paths:
            assert isinstance(path, Path)
            assert path.exists()

    def test_resolve_all_doesnt_recreate_existing(self, setup_wiki_structure):
        """resolve_all only creates placeholders for missing pages."""
        resolver = LinkResolver(setup_wiki_structure)

        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Existing Entity]] and [[New Entity]].")

        created_paths = resolver.resolve_all(test_page)

        # Should only create placeholder for New Entity
        assert len(created_paths) == 1
        assert "new-entity.md" in str(created_paths[0])

    def test_resolve_all_handles_duplicates(self, wiki_dir):
        """resolve_all handles duplicate links efficiently."""
        resolver = LinkResolver(wiki_dir)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)

        test_page = wiki_dir / "entities" / "test.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\n[[Duplicate Link]] appears [[Duplicate Link]] twice.")

        created_paths = resolver.resolve_all(test_page)

        # Should create only one placeholder despite duplicate
        assert len(created_paths) == 1


class TestLogging:
    """Tests for logging behavior."""

    def test_resolve_all_logs_creation(self, setup_wiki_structure, caplog):
        """resolve_all logs placeholder creation."""
        resolver = LinkResolver(setup_wiki_structure)

        test_page = setup_wiki_structure / "entities" / "test-page.md"
        test_page.write_text("---\ntitle: Test\n---\n# Test\n\nSee [[Missing Entity]].")

        with caplog.at_level(logging.INFO):
            resolver.resolve_all(test_page)

        assert "created placeholder" in caplog.text.lower() or "placeholder" in caplog.text.lower()
