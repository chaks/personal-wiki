"""Tests for source management API routes."""
import pytest
import httpx
from pathlib import Path


@pytest.fixture
def test_dirs(tmp_path):
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
        "config": tmp_path / "config",
    }


@pytest.fixture
def sample_sources_file(test_dirs):
    """Create a sources.yaml with sample entries."""
    test_dirs["config"].mkdir(parents=True)
    sources_file = test_dirs["config"] / "sources.yaml"
    sources_file.write_text(
        "sources:\n"
        "  - type: pdf\n"
        "    path: sources/pdfs/doc.pdf\n"
        "    tags: [docs]\n"
        "  - type: markdown\n"
        "    path: sources/markdown/notes.md\n"
        "    tags: [notes]\n"
    )
    return sources_file


@pytest.mark.asyncio
async def test_list_sources(sample_sources_file, test_dirs):
    """GET /api/sources returns 200 with sources list."""
    import src.routes.manage as manage_module

    original = manage_module.SOURCES_FILE
    manage_module.SOURCES_FILE = str(sample_sources_file)

    try:
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/sources")
            assert response.status_code == 200
            data = response.json()
            assert "sources" in data
            assert len(data["sources"]) == 2
            assert data["sources"][0]["type"] == "pdf"
            assert data["sources"][1]["type"] == "markdown"
    finally:
        manage_module.SOURCES_FILE = original


@pytest.mark.asyncio
async def test_add_source(sample_sources_file, test_dirs):
    """POST /api/sources returns 201 and adds a source."""
    import src.routes.manage as manage_module

    original = manage_module.SOURCES_FILE
    manage_module.SOURCES_FILE = str(sample_sources_file)

    try:
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/sources",
                json={"type": "url", "url": "https://example.com/article", "tags": ["web"]},
            )
            assert response.status_code == 201
            data = response.json()
            assert "message" in data
            assert "Source added" in data["message"]

            # Verify source was actually added
            resp = await client.get("/api/sources")
            sources = resp.json()["sources"]
            assert len(sources) == 3
            assert sources[-1]["type"] == "url"
    finally:
        manage_module.SOURCES_FILE = original


@pytest.mark.asyncio
async def test_delete_source(sample_sources_file, test_dirs):
    """DELETE /api/sources/path/... returns 200 or 404."""
    import src.routes.manage as manage_module

    original = manage_module.SOURCES_FILE
    manage_module.SOURCES_FILE = str(sample_sources_file)

    try:
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # Delete existing source
            response = await client.delete("/api/sources/path/sources/pdfs/doc.pdf")
            assert response.status_code == 200
            data = response.json()
            assert "deleted" in data["message"].lower() or "source" in data["message"].lower()

            # Verify it was deleted
            resp = await client.get("/api/sources")
            sources = resp.json()["sources"]
            assert len(sources) == 1

            # Try deleting a non-existent source
            response = await client.delete("/api/sources/path/nonexistent/file.txt")
            assert response.status_code == 404
    finally:
        manage_module.SOURCES_FILE = original


@pytest.mark.asyncio
async def test_manage_routes_registered(test_dirs):
    """Verify /api/sources is in app routes."""
    from src.server import create_app

    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

    route_paths = [route.path for route in app.routes]
    assert "/api/sources" in route_paths


@pytest.mark.asyncio
async def test_add_source_validates_url(test_dirs):
    """POST /api/sources rejects invalid URLs."""
    test_dirs["config"].mkdir(parents=True)
    sources_file = test_dirs["config"] / "sources.yaml"

    import src.routes.manage as manage_module

    original = manage_module.SOURCES_FILE
    manage_module.SOURCES_FILE = str(sources_file)

    try:
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # Invalid URL should be rejected
            response = await client.post(
                "/api/sources",
                json={"type": "url", "url": "not-a-valid-url", "tags": ["web"]},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Invalid URL" in data["detail"]

            # Missing scheme should be rejected
            response = await client.post(
                "/api/sources",
                json={"type": "url", "url": "ftp://example.com", "tags": ["web"]},
            )
            assert response.status_code == 400

            # Valid URL should be accepted
            response = await client.post(
                "/api/sources",
                json={"type": "url", "url": "https://example.com/article", "tags": ["web"]},
            )
            assert response.status_code == 201
    finally:
        manage_module.SOURCES_FILE = original
