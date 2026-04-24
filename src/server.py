# src/server.py
"""FastAPI backend for Personal Wiki Chat."""
import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, Optional, Set

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.auth import APIKeyAuthMiddleware, load_api_keys_from_env
from src.services.llm_provider import LLMProvider, OllamaProvider
from src.services.vector_store import VectorStore, QdrantStore

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


def create_app(
    wiki_dir: Path,
    state_dir: Path,
    static_dir: Path,
    qdrant_url: str = "http://localhost:6333",
    llm_provider: Optional[LLMProvider] = None,
    vector_store: Optional[VectorStore] = None,
    api_keys: Optional[Set[str]] = None,
) -> FastAPI:
    """Create and configure FASTAPI application.

    Args:
        wiki_dir: Path to wiki content directory
        state_dir: Path to state directory
        static_dir: Path to static files directory
        qdrant_url: Qdrant server URL (used if vector_store not provided)
        llm_provider: LLM provider instance (creates default OllamaProvider if None)
        vector_store: Vector store instance (creates default QdrantStore if None)
        api_keys: Set of valid API keys for authentication (None = no auth)
    """
    from src.indexer import WikiIndexer
    from src.chat import ChatEngine

    app = FastAPI(title="Personal Wiki Chat")
    logger.info("Creating FastAPI application")

    # Security: restrict CORS to localhost only (no credentials allowed with wildcard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    # Add API key authentication middleware if configured
    if api_keys:
        app.add_middleware(APIKeyAuthMiddleware, api_keys=api_keys)
        logger.info("API key authentication middleware enabled")
    else:
        logger.warning("No API keys configured - authentication disabled")

    # Use injected services or create defaults
    if vector_store is None:
        vector_store = QdrantStore(url=qdrant_url)

    indexer = WikiIndexer(wiki_dir, vector_store=vector_store)
    chat_engine = ChatEngine(wiki_dir, indexer, llm_provider=llm_provider)
    logger.info("Initialized WikiIndexer and ChatEngine with injected services")

    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("Mounted static files at /static")

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        logger.debug("Health check requested")
        return HealthResponse(status="ok")

    @app.post("/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        logger.info(f"Chat request received: {request.message[:50]}...")
        return StreamingResponse(
            stream_chat_response(request.message, chat_engine),
            media_type="text/event-stream",
        )

    @app.get("/")
    async def serve_index():
        from fastapi.responses import FileResponse
        index_path = static_dir / "index.html"
        if not index_path.exists():
            logger.error(f"index.html not found at {index_path}")
            raise HTTPException(status_code=404, detail="index.html not found")
        logger.debug("Serving index.html")
        return FileResponse(index_path)

    logger.info("FastAPI application created successfully")
    return app


async def stream_chat_response(
    message: str,
    chat_engine,
) -> AsyncGenerator[str, None]:
    """Stream chat response as SSE events."""
    import html

    logger.debug(f"Searching wiki for: {message[:50]}...")
    start_time = time.time()
    context_pages = chat_engine.search(message)
    search_duration = time.time() - start_time

    logger.info(
        f"Search completed in {search_duration:.3f}s, found {len(context_pages)} pages"
    )

    context_text = "\n\n".join(
        f"=== {p['path']} ===\n{p['content']}" for p in context_pages
    )

    # Sanitize user input to prevent prompt injection attacks
    sanitized_message = html.escape(message.strip())

    prompt = f"""You are a helpful assistant answering questions based on a personal knowledge wiki.

Context from wiki:
{context_text}

Question: {sanitized_message}

Answer based on the context above. If the context doesn't contain relevant information, say so."""

    logger.debug(f"Sending prompt to LLM ({len(prompt)} chars)")
    stream = chat_engine.llm_provider.generate_stream(prompt)

    chunk_count = 0
    for response_text in stream:
        if response_text:
            chunk_count += 1
            yield f"data: {json.dumps({'text': response_text})}\n\n"

    logger.info(f"Streamed {chunk_count} chunks, sending [DONE]")
    yield "data: [DONE]\n\n"


def run_server(
    wiki_dir: Path,
    state_dir: Path,
    static_dir: Path,
    host: str = "0.0.0.0",
    port: int = 8000,
):
    """Run the server."""
    import uvicorn

    # Load API keys from environment
    api_keys = load_api_keys_from_env()
    if api_keys:
        logger.info(f"Loaded {len(api_keys)} API key(s) from environment")
    else:
        logger.warning(
            "WIKI_API_KEYS environment variable not set - server will run without authentication"
        )

    app = create_app(wiki_dir, state_dir, static_dir, api_keys=api_keys if api_keys else None)
    logger.info(f"Starting uvicorn server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    from pathlib import Path

    root = Path(__file__).parent.parent
    run_server(
        wiki_dir=root / "wiki",
        state_dir=root / "state",
        static_dir=root / "static",
    )
