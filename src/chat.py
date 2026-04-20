# src/chat.py
"""Chat query handling with RAG."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChatEngine:
    """Handles chat queries with wiki retrieval."""

    def __init__(self, wiki_dir: Path, indexer):
        self.wiki_dir = Path(wiki_dir)
        self.indexer = indexer
        logger.debug(f"ChatEngine initialized with wiki_dir={wiki_dir}")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search wiki for relevant context."""
        logger.info(f"Search request: query='{query[:50]}...', top_k={top_k}")
        try:
            results = self.indexer.search(query, top_k)
            if results:
                logger.info(f"Vector search found {len(results)} results")
            else:
                logger.debug("Vector search returned no results")
            return results
        except Exception as e:
            logger.warning(f"Vector search failed: {e}, falling back to keyword search")
            # Fallback: keyword search over wiki files
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Simple keyword search as fallback."""
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
