from __future__ import annotations
# src/chat.py
"""Chat query handling with RAG."""
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.services.llm_provider import LLMProvider, OllamaProvider

if TYPE_CHECKING:
    from src.indexer import WikiIndexer

logger = logging.getLogger(__name__)


class ChatEngine:
    """Handles chat queries with wiki retrieval."""

    def __init__(
        self,
        wiki_dir: Path,
        indexer: "WikiIndexer",
        llm_provider: "LLMProvider | None" = None,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.indexer = indexer
        self.llm_provider = llm_provider or OllamaProvider()
        logger.debug(f"ChatEngine initialized with wiki_dir={wiki_dir}, llm_provider={type(self.llm_provider).__name__}")

    def _keyword_search_sync(self, query: str, top_k: int) -> list[dict]:
        """Simple keyword search as fallback (sync, runs in thread)."""
        logger.debug(f"Starting keyword search for: {query[:50]}...")
        results = []
        query_lower = query.lower()

        for md_file in self.wiki_dir.rglob("*.md"):
            content = md_file.read_text()
            if query_lower in content.lower():
                results.append({
                    "path": str(md_file.relative_to(self.wiki_dir)),
                    "content": content[:2000],
                    "score": 1.0,
                })
                logger.debug(f"Keyword match: {md_file}")

        logger.info(f"Keyword search returned {len(results)} results")
        return results[:top_k]

    async def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Async wrapper for keyword search fallback."""
        return await asyncio.to_thread(self._keyword_search_sync, query, top_k)

    async def search_async(self, query: str, top_k: int = 5) -> list[dict]:
        """Asynchronously search wiki for relevant context."""
        logger.info(f"Async search request: query='{query[:50]}...', top_k={top_k}")
        try:
            results = await self.indexer.search_async(query, top_k)
            if results:
                logger.info(f"Async vector search found {len(results)} results")
            else:
                logger.debug("Async vector search returned no results")
            return results
        except Exception as e:
            logger.warning(f"Async vector search failed: {e}, falling back to keyword search")
            # Fallback: keyword search over wiki files
            return await self._keyword_search(query, top_k)

    async def query_async(self, query: str, top_k: int = 5) -> tuple[str, list[dict]]:
        """Asynchronously query the wiki and get an answer.

        Args:
            query: The user's question
            top_k: Number of context pages to retrieve

        Returns:
            Tuple of (answer, context_pages)
        """
        logger.info(f"Async query request: {query[:50]}...")

        # Search for relevant context
        try:
            context_pages = await self.search_async(query, top_k)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            context_pages = []

        from src.prompt import build_rag_prompt

        system, user_prompt = build_rag_prompt(context_pages, query)

        logger.debug(f"Sending prompt to LLM ({len(user_prompt)} chars)")
        answer = await self.llm_provider.generate_async(user_prompt, system=system)
        logger.info(f"Received answer from LLM ({len(answer)} chars)")

        return answer, context_pages
