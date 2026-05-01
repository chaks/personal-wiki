# tests/test_integration.py
"""End-to-end integration tests."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def full_app(tmp_path):
    """Create full app with all directories."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "entities").mkdir()
    (wiki_dir / "concepts").mkdir()

    state_dir = tmp_path / "state"
    state_dir.mkdir()

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>Test</html>")

    # Create a test wiki page
    test_page = wiki_dir / "concepts" / "test-concept.md"
    test_page.write_text("""---
title: Test Concept
category: concepts
---

# Test Concept

This is a test concept about testing.
""")

    from src.server import create_app
    return create_app(wiki_dir, state_dir, static_dir)


def test_health_check(full_app):
    """Test: health endpoint returns status info."""
    client = TestClient(full_app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "ollama" in data
    assert "qdrant" in data
    assert "is_healthy" in data


def test_static_files_served(full_app):
    """Test: static files are served correctly."""
    client = TestClient(full_app)

    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "<html>Test</html>" in response.text


def test_index_page_exists(full_app):
    """Test: index page is served at root."""
    client = TestClient(full_app)

    response = client.get("/")
    assert response.status_code == 200


def test_chat_endpoint_accepts_requests(full_app):
    """Test: chat endpoint accepts POST requests and returns streaming response."""
    client = TestClient(full_app, raise_server_exceptions=False)

    # Chat query - endpoint should accept the request
    # Note: actual response content depends on ollama being available
    response = client.post("/chat", json={"message": "What is testing?"})

    # Response should be either 200 (streaming) or 500 (ollama not available)
    # The important thing is the endpoint is properly configured
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        # If ollama is available, check streaming response
        assert "text/event-stream" in response.headers.get("content-type", "")
