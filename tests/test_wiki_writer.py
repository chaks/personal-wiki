# tests/test_wiki_writer.py
"""Tests for WikiPageWriter class."""
import logging
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.wiki_writer import WikiPageWriter
from src.extractor import Entity, Concept


@pytest.fixture
def wiki_dir():
    """Create a temporary wiki directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def writer(wiki_dir):
    """Create a WikiPageWriter instance."""
    return WikiPageWriter(wiki_dir)


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return Entity(
        name="Andrej Karpathy",
        entity_type="person",
        description="Computer scientist who worked at OpenAI and Tesla on deep learning and autonomous driving",
        source_doc="karpathy_bio.md"
    )


@pytest.fixture
def sample_concept():
    """Create a sample concept for testing."""
    return Concept(
        name="Transformer Architecture",
        definition="Neural network architecture based on attention mechanisms",
        related_entities=["Google", "OpenAI"],
        source_doc="llm_research.md"
    )


class TestWikiPageWriterInitialization:
    """Tests for WikiPageWriter initialization."""

    def test_writer_creates_directories(self, wiki_dir):
        """WikiPageWriter creates required directories."""
        writer = WikiPageWriter(wiki_dir)
        assert writer.entities_dir.exists()
        assert writer.concepts_dir.exists()
        assert writer.documents_dir.exists()

    def test_writer_sets_paths(self, wiki_dir):
        """WikiPageWriter sets correct paths."""
        writer = WikiPageWriter(wiki_dir)
        assert writer.wiki_dir == wiki_dir
        assert writer.entities_dir == wiki_dir / "entities"
        assert writer.concepts_dir == wiki_dir / "concepts"
        assert writer.documents_dir == wiki_dir / "documents"


class TestSlugify:
    """Tests for _slugify method."""

    def test_slugify_simple_name(self, writer):
        """Slugify converts simple name to slug."""
        assert writer._slugify("Andrej Karpathy") == "andrej-karpathy"

    def test_slugify_lowercase(self, writer):
        """Slugify converts to lowercase."""
        assert writer._slugify("TEST") == "test"

    def test_slugify_spaces(self, writer):
        """Slugify replaces spaces with hyphens."""
        assert writer._slugify("Deep Learning") == "deep-learning"

    def test_slugify_special_characters(self, writer):
        """Slugify removes special characters."""
        assert writer._slugify("C++") == "c"
        assert writer._slugify("Test/Path") == "test-path"

    def test_slugify_preserves_alphanumeric(self, writer):
        """Slugify preserves alphanumeric characters and hyphens."""
        assert writer._slugify("GPT-4") == "gpt-4"
        assert writer._slugify("Python_3") == "python_3"


class TestWriteEntityPage:
    """Tests for write_entity method."""

    def test_write_entity_page(self, writer, sample_entity):
        """Entity page is created with correct content."""
        output_path = writer.write_entity(sample_entity)

        assert output_path.exists()
        assert output_path.parent == writer.entities_dir
        assert output_path.name == "andrej-karpathy.md"

        content = output_path.read_text()

        # Check frontmatter
        assert "---" in content
        assert "title: Andrej Karpathy" in content
        assert "category: entity" in content
        assert "entity_type: person" in content
        assert "source: karpathy_bio.md" in content
        assert "created_at:" in content

        # Check body
        assert "# Andrej Karpathy" in content
        assert "Computer scientist" in content

    def test_write_entity_page_returns_path(self, writer, sample_entity):
        """write_entity returns the output path."""
        output_path = writer.write_entity(sample_entity)
        assert isinstance(output_path, Path)
        assert output_path.exists()

    def test_write_entity_page_with_see_also(self, writer):
        """Entity page includes See Also section with correct structure."""
        entity = Entity(
            name="Tesla",
            entity_type="organization",
            description="Electric vehicle company",
            source_doc="tesla.md"
        )
        output_path = writer.write_entity(entity)
        content = output_path.read_text()

        # Verify the See Also section exists with proper heading
        assert "## See Also" in content

        # Verify the section has content (even if it's a placeholder comment)
        lines = content.split("\n")
        see_also_idx = None
        for i, line in enumerate(lines):
            if line == "## See Also":
                see_also_idx = i
                break

        assert see_also_idx is not None
        # Verify there's content after the See Also heading
        assert see_also_idx + 1 < len(lines)


class TestWriteConceptPage:
    """Tests for write_concept method."""

    def test_write_concept_page(self, writer, sample_concept):
        """Concept page is created with correct content."""
        output_path = writer.write_concept(sample_concept)

        assert output_path.exists()
        assert output_path.parent == writer.concepts_dir
        assert output_path.name == "transformer-architecture.md"

        content = output_path.read_text()

        # Check frontmatter
        assert "---" in content
        assert "title: Transformer Architecture" in content
        assert "category: concept" in content
        assert "source: llm_research.md" in content
        assert "created_at:" in content

        # Check body
        assert "# Transformer Architecture" in content
        assert "Neural network architecture" in content

    def test_write_concept_page_returns_path(self, writer, sample_concept):
        """write_concept returns the output path."""
        output_path = writer.write_concept(sample_concept)
        assert isinstance(output_path, Path)
        assert output_path.exists()

    def test_write_concept_page_with_wikilinks(self, writer, sample_concept):
        """Concept page includes Related Entities with wikilinks like [[Quarkus]]."""
        output_path = writer.write_concept(sample_concept)
        content = output_path.read_text()

        assert "## Related Entities" in content
        assert "[[Google]]" in content
        assert "[[OpenAI]]" in content

    def test_write_concept_page_no_related_entities(self, writer):
        """Concept page handles empty related entities."""
        concept = Concept(
            name="Deep Learning",
            definition="Subset of machine learning",
            related_entities=[]
        )
        output_path = writer.write_concept(concept)
        content = output_path.read_text()

        assert output_path.exists()


class TestEntityPageFormat:
    """Tests for entity page formatting details."""

    def test_entity_page_frontmatter_fields(self, writer, sample_entity):
        """Entity page frontmatter includes all required fields."""
        output_path = writer.write_entity(sample_entity)
        content = output_path.read_text()

        # Extract frontmatter
        lines = content.split("\n")
        frontmatter_started = False
        frontmatter_ended = False
        frontmatter_lines = []

        for line in lines:
            if line == "---" and not frontmatter_started:
                frontmatter_started = True
            elif line == "---" and frontmatter_started:
                frontmatter_ended = True
                break
            elif frontmatter_started and not frontmatter_ended:
                frontmatter_lines.append(line)

        frontmatter = "\n".join(frontmatter_lines)

        assert "title:" in frontmatter
        assert "category:" in frontmatter
        assert "entity_type:" in frontmatter
        assert "created_at:" in frontmatter
        assert "source:" in frontmatter

    def test_entity_page_body_structure(self, writer, sample_entity):
        """Entity page body has correct structure."""
        output_path = writer.write_entity(sample_entity)
        content = output_path.read_text()

        # Should have heading
        assert "# Andrej Karpathy" in content

        # Should have description
        assert "Computer scientist" in content


class TestConceptPageFormat:
    """Tests for concept page formatting details."""

    def test_concept_page_frontmatter_fields(self, writer, sample_concept):
        """Concept page frontmatter includes all required fields."""
        output_path = writer.write_concept(sample_concept)
        content = output_path.read_text()

        # Extract frontmatter
        lines = content.split("\n")
        frontmatter_started = False
        frontmatter_ended = False
        frontmatter_lines = []

        for line in lines:
            if line == "---" and not frontmatter_started:
                frontmatter_started = True
            elif line == "---" and frontmatter_started:
                frontmatter_ended = True
                break
            elif frontmatter_started and not frontmatter_ended:
                frontmatter_lines.append(line)

        frontmatter = "\n".join(frontmatter_lines)

        assert "title:" in frontmatter
        assert "category:" in frontmatter
        assert "created_at:" in frontmatter
        assert "source:" in frontmatter

    def test_concept_page_body_structure(self, writer, sample_concept):
        """Concept page body has correct structure."""
        output_path = writer.write_concept(sample_concept)
        content = output_path.read_text()

        # Should have heading
        assert "# Transformer Architecture" in content

        # Should have definition
        assert "Neural network architecture" in content

        # Should have Related Entities section
        assert "## Related Entities" in content


class TestLogging:
    """Tests for logging behavior."""

    def test_write_entity_logs_success(self, writer, sample_entity, caplog):
        """write_entity logs info message on success."""
        with caplog.at_level(logging.INFO):
            writer.write_entity(sample_entity)

        assert "wrote entity page" in caplog.text.lower()

    def test_write_concept_logs_success(self, writer, sample_concept, caplog):
        """write_concept logs info message on success."""
        with caplog.at_level(logging.INFO):
            writer.write_concept(sample_concept)

        assert "wrote concept page" in caplog.text.lower()
