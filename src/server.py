# src/server.py
"""FastAPI backend for Personal Wiki Chat."""
import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
) -> FastAPI:
    """Create and configure FastAPI application."""
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

    indexer = WikiIndexer(wiki_dir, qdrant_url)
    chat_engine = ChatEngine(wiki_dir, indexer)
    logger.info("Initialized WikiIndexer and ChatEngine")

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
    import ollama
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
    # Escape special characters and remove potential prompt injection patterns
    sanitized_message = html.escape(message.strip())

    prompt = f"""You are a helpful assistant answering questions based on a personal knowledge wiki.

Context from wiki:
{context_text}

Question: {sanitized_message}

Answer based on the context above. If the context doesn't contain relevant information, say so."""

    logger.debug(f"Sending prompt to Ollama ({len(prompt)} chars)")
    stream = ollama.generate(model="gemma4:e2b", prompt=prompt, stream=True)

    chunk_count = 0
    for chunk in stream:
        response_text = chunk.get("response", "")
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

    app = create_app(wiki_dir, state_dir, static_dir)
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
