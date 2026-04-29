import pytest
import httpx
import httpx
from pathlib import Path
from unittest.mock import patch, AsyncMock


@pytest.fixture
def test_dirs(tmp_path):
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
    }


@pytest.mark.asyncio
async def test_chat_async_endpoint_removed(test_dirs):
    """The /chat/async endpoint no longer exists."""
    from src.server import create_app

    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/chat/async", json={"message": "Hello"})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_endpoint_streams(test_dirs):
    """The /chat endpoint streams SSE responses via async methods."""
    from src.server import create_app

    test_dirs["static"].mkdir(parents=True)
    (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

    app = create_app(test_dirs["wiki"], test_dirs["state"], test_dirs["static"])

    async def mock_stream(*args, **kwargs):
        yield "Hello"
        yield " there"

    with patch("ollama.chat") as mock_chat:
        mock_chat.return_value = iter([
            {"message": {"content": "Hello"}},
            {"message": {"content": " there"}},
        ])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "Hi"})
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
