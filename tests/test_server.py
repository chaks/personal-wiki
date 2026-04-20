# tests/test_server.py
import pytest
import httpx
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def test_dirs(tmp_path):
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
    }


@pytest.mark.asyncio
async def test_server_health_endpoint(test_dirs):
    """Server responds to health check."""
    from src.server import create_app

    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_endpoint_accepts_post(test_dirs):
    """Chat endpoint accepts POST requests."""
    from src.server import create_app

    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

    # Mock ollama.generate to return a simple stream
    def mock_generate(*args, **kwargs):
        yield {"response": "Hello"}
        yield {"response": " there"}

    with patch("ollama.generate", mock_generate):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "Hello"})
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
