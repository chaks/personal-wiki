"""Qdrant-based semantic indexing for wiki pages."""
import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from src.services.llm_provider import LLMProvider, OllamaProvider
from src.services.embedding_provider import EmbeddingProvider, OllamaEmbeddingProvider
from src.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 3000


class WikiIndexer:
    """Indexes wiki pages in Qdrant for semantic search."""

    COLLECTION_NAME = "personal_wiki"

    def __init__(
        self,
        wiki_dir: Path,
        vector_store: VectorStore,  # Required, not Optional
        embedding_provider: Optional[EmbeddingProvider] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.vector_store = vector_store  # Required
        self.embedding_provider = embedding_provider or OllamaEmbeddingProvider()
        self.llm_provider = llm_provider or OllamaProvider()
        logger.debug(f"WikiIndexer initialized: wiki_dir={wiki_dir}, vector_store={type(vector_store).__name__}")

    def _page_id(self, page_path: Path) -> str:
        """Generate unique UUID-style ID for page."""
        rel_path = page_path.relative_to(self.wiki_dir)
        hash_hex = hashlib.sha256(str(rel_path).encode()).hexdigest()
        page_id = f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
        logger.debug(f"Generated page ID {page_id} for {rel_path}")
        return page_id

    def _chunk_id(self, page_path: Path, chunk_index: int) -> str:
        """Generate unique ID for a page chunk."""
        rel_path = page_path.relative_to(self.wiki_dir)
        hash_hex = hashlib.sha256(f"{rel_path}:chunk:{chunk_index}".encode()).hexdigest()
        return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"

    def _split_into_chunks(self, content: str, title: str) -> list[str]:
        """Split markdown content into chunks by heading boundaries.

        Preserves section structure by splitting at ## headings.
        Falls back to fixed-size chunking if no headings found.

        Args:
            content: Markdown content
            title: Page title for metadata

        Returns:
            List of text chunks
        """
        sections = re.split(r'(?=^##\s)', content, flags=re.MULTILINE)
        sections = [s.strip() for s in sections if s.strip()]

        if len(sections) > 1:
            chunks = []
            current = ""
            for section in sections:
                if len(current) + len(section) <= _CHUNK_SIZE:
                    current += "\n" + section if current else section
                else:
                    if current:
                        chunks.append(current.strip())
                    if len(section) > _CHUNK_SIZE:
                        for i in range(0, len(section), _CHUNK_SIZE):
                            chunks.append(section[i:i + _CHUNK_SIZE])
                    else:
                        current = section
            if current:
                chunks.append(current.strip())
            return chunks

        chunks = []
        for i in range(0, len(content), _CHUNK_SIZE):
            chunks.append(content[i:i + _CHUNK_SIZE])
        return chunks

    async def index_page_async(self, page_path: Path) -> None:
        """Embed and index a wiki page asynchronously."""
        logger.info(f"Indexing page: {page_path}")
        content = page_path.read_text()
        logger.debug(f"Read {len(content)} chars from {page_path}")

        chunks = self._split_into_chunks(content, page_path.stem)
        page_id = self._page_id(page_path)
        rel_path = str(page_path.relative_to(self.wiki_dir))
        title = page_path.stem

        logger.info(f"Split {page_path.name} into {len(chunks)} chunk(s)")

        points = []
        for i, chunk in enumerate(chunks):
            chunk_embedding = await self.embedding_provider.embed_async(chunk)
            cid = self._chunk_id(page_path, i)
            point_id = page_id if len(chunks) == 1 else cid

            points.append({
                "id": point_id,
                "vector": chunk_embedding,
                "payload": {
                    "path": rel_path,
                    "content": chunk,
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            })

        await self.vector_store.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Successfully indexed {page_path.name} ({len(points)} points)")

    async def index_all_wiki_pages_async(self) -> int:
        """Index all markdown files in the wiki directory with concurrency limiting."""
        indexed = 0
        semaphore = asyncio.Semaphore(5)

        async def index_with_semaphore(page: Path) -> bool:
            async with semaphore:
                try:
                    await self.index_page_async(page)
                    return True
                except Exception as e:
                    logger.error(f"Failed to index {page}: {e}")
                    return False

        tasks = []
        for md_file in self.wiki_dir.rglob("*.md"):
            tasks.append(index_with_semaphore(md_file))

        results = await asyncio.gather(*tasks)
        indexed = sum(results)
        logger.info(f"Indexed {indexed} wiki pages")
        return indexed

    async def search_async(self, query: str, top_k: int = 10) -> list[dict]:
        """Asynchronously search for relevant wiki pages."""
        logger.info(f"Async searching wiki for: {query[:50]}... (top_k={top_k})")
        query_embedding = await self.embedding_provider.embed_async(query)

        # Fetch 3x to account for multi-chunk pages returning duplicate paths
        raw_results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k * 3
        )

        # Deduplicate by path, keeping the best score per document
        best = {}
        for hit in raw_results:
            path = hit.payload["path"]
            if path not in best or hit.score > best[path]["score"]:
                best[path] = {
                    "path": path,
                    "content": hit.payload["content"],
                    "score": hit.score,
                }

        result_dicts = sorted(best.values(), key=lambda r: r["score"], reverse=True)[:top_k]
        logger.info(f"Async search returned {len(result_dicts)} results")
        return result_dicts
