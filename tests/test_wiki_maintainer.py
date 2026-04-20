# tests/test_wiki_maintainer.py
import pytest
from pathlib import Path
from src.wiki_maintainer import WikiMaintainer, WikiPage


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


def test_wiki_page_creation(wiki_dir):
    """WikiMaintainer creates wiki pages."""
    maintainer = WikiMaintainer(wiki_dir)
    page = maintainer.create_page(
        title="Test Concept",
        category="concepts",
        content="This is a test concept.",
        links=["entities/RelatedEntity.md"],
    )
    assert page.title == "Test Concept"
    assert page.category == "concepts"
    wiki_file = wiki_dir / "concepts" / "test-concept.md"
    assert wiki_file.exists()


def test_wiki_page_has_frontmatter(wiki_dir):
    """Wiki pages include YAML frontmatter."""
    maintainer = WikiMaintainer(wiki_dir)
    page = maintainer.create_page(
        title="Test Entity",
        category="entities",
        content="Test content",
    )
    content = page.to_markdown()
    assert "---" in content
    assert "title: Test Entity" in content
    assert "category: entities" in content


def test_wiki_link_formatting(wiki_dir):
    """Wiki pages format links correctly."""
    maintainer = WikiMaintainer(wiki_dir)
    page = maintainer.create_page(
        title="Test Page",
        category="entities",
        content="Test content",
        links=["concepts/RelatedConcept.md", "entities/OtherEntity.md"],
    )
    content = page.to_markdown()
    assert "[[concepts/RelatedConcept]]" in content or "[[RelatedConcept]]" in content
