"""Tests for wiki browsing API routes."""
import pytest
import httpx
from pathlib import Path


@pytest.fixture
def test_dirs(tmp_path):
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
    }


def _create_wiki_structure(test_dirs, entities=None, concepts=None):
    """Create wiki directory structure with sample pages."""
    wiki = test_dirs["wiki"]
    entities_dir = wiki / "entities"
    concepts_dir = wiki / "concepts"
    entities_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)

    for name, content in (entities or []):
        slug = name.lower().replace(" ", "-")
        (entities_dir / f"{slug}.md").write_text(content)

    for name, content in (concepts or []):
        slug = name.lower().replace(" ", "-")
        (concepts_dir / f"{slug}.md").write_text(content)


@pytest.fixture
def wiki_with_pages(test_dirs):
    """Wiki with sample entities and concepts."""
    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    _create_wiki_structure(
        test_dirs,
        entities=[
            ("Python", "# Python\n\nA high-level programming language."),
            ("Django", "# Django\n\nA web framework for Python."),
        ],
        concepts=[
            ("Web Development", "# Web Development\n\nBuilding web applications."),
            ("Machine Learning", "# Machine Learning\n\nAlgorithms that learn from data."),
        ],
    )
    return test_dirs


@pytest.fixture
def empty_wiki(test_dirs):
    """Wiki with no entities or concepts."""
    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")
    test_dirs["wiki"].mkdir(parents=True)
    return test_dirs


@pytest.mark.asyncio
async def test_list_entities(wiki_with_pages):
    """GET /api/wiki/entities returns 200 with entities list."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/entities")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)
        assert len(data["entities"]) == 2
        # Entity names should be slugified from filenames
        entity_names = data["entities"]
        assert "python" in entity_names
        assert "django" in entity_names


@pytest.mark.asyncio
async def test_list_entities_empty(empty_wiki):
    """GET /api/wiki/entities returns empty list when no entities exist."""
    from src.server import create_app

    app = create_app(empty_wiki["wiki"], empty_wiki["state"], empty_wiki["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/entities")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert data["entities"] == []


@pytest.mark.asyncio
async def test_list_concepts(wiki_with_pages):
    """GET /api/wiki/concepts returns 200 with concepts list."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/concepts")
        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        assert isinstance(data["concepts"], list)
        assert len(data["concepts"]) == 2
        concept_names = data["concepts"]
        assert "web-development" in concept_names
        assert "machine-learning" in concept_names


@pytest.mark.asyncio
async def test_get_entity(wiki_with_pages):
    """GET /api/wiki/entities/{name} returns 200 with content."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/entities/python")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "content" in data
        assert data["name"] == "python"
        assert "programming language" in data["content"]


@pytest.mark.asyncio
async def test_get_entity_not_found(wiki_with_pages):
    """GET /api/wiki/entities/{name} returns 404 for missing entity."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/entities/nonexistent")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_concept(wiki_with_pages):
    """GET /api/wiki/concepts/{name} returns 200 with content."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/concepts/web-development")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "content" in data
        assert data["name"] == "web-development"
        assert "web applications" in data["content"]


@pytest.mark.asyncio
async def test_get_concept_not_found(wiki_with_pages):
    """GET /api/wiki/concepts/{name} returns 404 for missing concept."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/concepts/nonexistent")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_orphans(wiki_with_pages):
    """GET /api/wiki/orphans returns 200 with orphans list."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/orphans")
        assert response.status_code == 200
        data = response.json()
        assert "orphans" in data
        assert isinstance(data["orphans"], list)
        # With no cross-links, all pages should be orphans (4 pages)
        assert len(data["orphans"]) == 4


@pytest.mark.asyncio
async def test_get_orphan_content(wiki_with_pages):
    """GET /api/wiki/orphans/{name} returns 200 with orphan page content."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First list orphans to get a valid path
        response = await client.get("/api/wiki/orphans")
        assert response.status_code == 200
        orphan_paths = response.json()["orphans"]
        assert len(orphan_paths) > 0

        # Fetch content of the first orphan
        orphan_path = orphan_paths[0]  # e.g., "entities/python.md"
        response = await client.get(f"/api/wiki/orphans/{orphan_path}")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "content" in data
        assert data["name"] == orphan_path


@pytest.mark.asyncio
async def test_get_orphan_not_found(wiki_with_pages):
    """GET /api/wiki/orphans/{name} returns 404 for nonexistent path."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/orphans/nonexistent/path.md")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_orphan_path_traversal_rejected(wiki_with_pages):
    """GET /api/wiki/orphans/{name} returns 400 for traversal attempts."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/wiki/orphans/%2e%2e/%2e%2e/etc/passwd")
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_browse_routes_registered(wiki_with_pages):
    """Verify /api/wiki routes are in app."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    route_paths = [route.path for route in app.routes]
    assert "/api/wiki/entities" in route_paths
    assert "/api/wiki/concepts" in route_paths
    assert "/api/wiki/orphans" in route_paths


@pytest.mark.asyncio
async def test_path_traversal_rejected(wiki_with_pages):
    """GET /api/wiki/entities/{name} returns 400 for traversal attempts."""
    from src.server import create_app

    app = create_app(wiki_with_pages["wiki"], wiki_with_pages["state"], wiki_with_pages["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # URL-encoded .. reaches the handler and should be rejected
        response = await client.get("/api/wiki/entities/%2e%2e")
        assert response.status_code == 400

        # URL-encoded .. in nested path should also be rejected
        response = await client.get("/api/wiki/concepts/%2e%2e/python")
        assert response.status_code == 400

        # Absolute path attempt via double-slash
        response = await client.get("/api/wiki/entities//etc/passwd")
        assert response.status_code == 400
