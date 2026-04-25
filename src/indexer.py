# src/indexer.py
"""Qdrant-based semantic indexing for wiki pages."""
import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

import ollama

from src.services.vector_store import VectorStore, QdrantStore, SearchPoint

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
# nomic-embed-text context window is ~8192 tokens; ~4 chars/token ~= 32000 chars
# Use 3000 chars to be safe and leave room for metadata
_CHUNK_SIZE = 3000


class WikiIndexer:
    """Indexes wiki pages in Qdrant for semantic search."""

    COLLECTION_NAME = "personal_wiki"

    def __init__(
        self,
        wiki_dir: Path,
        qdrant_url: str = "http://localhost:6333",
        vector_store: Optional[VectorStore] = None,
    ):
        self.wiki_dir = Path(wiki_dir)
        self.qdrant_url = qdrant_url
        self.vector_store = vector_store
        self._client = None
        logger.debug(f"WikiIndexer initialized: wiki_dir={wiki_dir}, vector_store={type(vector_store).__name__ if vector_store else 'QdrantStore'}")

    @property
    def client(self):
        """Lazy-init Qdrant client for backward compatibility."""
        if self._client is None:
            if self.vector_store is None:
                self.vector_store = QdrantStore(url=self.qdrant_url)
            logger.info(f"Initialized vector store: {type(self.vector_store).__name__}")
        return self.vector_store

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using Ollama."""
        logger.debug(f"Generating embedding for {len(text)} chars")
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        embedding = response["embedding"]
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding

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
        # Try splitting by ## headings first
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
                        # Section itself is too long, split by fixed size
                        for i in range(0, len(section), _CHUNK_SIZE):
                            chunks.append(section[i:i + _CHUNK_SIZE])
                    else:
                        current = section
            if current:
                chunks.append(current.strip())
            return chunks

        # Fall back to fixed-size chunking
        chunks = []
        for i in range(0, len(content), _CHUNK_SIZE):
            chunks.append(content[i:i + _CHUNK_SIZE])
        return chunks

    def index_page(self, page_path: Path) -> None:
        """Embed and index a wiki page, chunking if needed."""
        logger.info(f"Indexing page: {page_path}")
        content = page_path.read_text()
        logger.debug(f"Read {len(content)} chars from {page_path}")

        chunks = self._split_into_chunks(content, page_path.stem)
        page_id = self._page_id(page_path)
        rel_path = str(page_path.relative_to(self.wiki_dir))
        title = page_path.stem

        logger.info(f"Split {page_path.name} into {len(chunks)} chunk(s)")

        # Index each chunk as a separate point
        points = []
        for i, chunk in enumerate(chunks):
            chunk_embedding = self._get_embedding(chunk)
            cid = self._chunk_id(page_path, i)

            # For single-chunk pages, use page_id; otherwise use chunk_id
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

        # Also upsert a page-level point with concatenated summary
        # (first 2000 chars as the "overview" embedding)
        if len(chunks) > 1:
            overview = content[:2000]
            overview_embedding = self._get_embedding(overview)
            points.append({
                "id": page_id,
                "vector": overview_embedding,
                "payload": {
                    "path": rel_path,
                    "content": overview,
                    "title": title,
                    "chunk_index": -1,  # marks page-level point
                    "total_chunks": len(chunks),
                },
            })

        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Successfully indexed {page_path.name} ({len(points)} points)")

    def index_all_wiki_pages(self) -> int:
        """Index all markdown files in the wiki directory."""
        indexed = 0
        for md_file in self.wiki_dir.rglob("*.md"):
            try:
                self.index_page(md_file)
                indexed += 1
            except Exception as e:
                logger.error(f"Failed to index {md_file}: {e}")
        logger.info(f"Indexed {indexed} wiki pages")
        return indexed

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for relevant wiki pages."""
        logger.info(f"Searching wiki for: {query[:50]}... (top_k={top_k})")
        query_embedding = self._get_embedding(query)

        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k
        )

        result_dicts = [
            {
                "path": hit.payload["path"],
                "content": hit.payload["content"],
                "score": hit.score,
            }
            for hit in results
        ]
        logger.info(f"Search returned {len(result_dicts)} results")
        return result_dicts

    async def _get_embedding_async(self, text: str) -> list[float]:
        """Get embedding for text using Ollama asynchronously."""
        logger.debug(f"Generating embedding for {len(text)} chars")
        response = await asyncio.to_thread(
            ollama.embeddings, model="nomic-embed-text", prompt=text
        )
        embedding = response["embedding"]
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding

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
            chunk_embedding = await self._get_embedding_async(chunk)
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

        if len(chunks) > 1:
            overview = content[:2000]
            overview_embedding = await self._get_embedding_async(overview)
            points.append({
                "id": page_id,
                "vector": overview_embedding,
                "payload": {
                    "path": rel_path,
                    "content": overview,
                    "title": title,
                    "chunk_index": -1,
                    "total_chunks": len(chunks),
                },
            })

        await self.client.upsert_async(
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

    async def search_async(self, query: str, top_k: int = 5) -> list[dict]:
        """Asynchronously search for relevant wiki pages."""
        logger.info(f"Async searching wiki for: {query[:50]}... (top_k={top_k})")
        query_embedding = await self._get_embedding_async(query)

        results = await self.client.search_async(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k
        )

        result_dicts = [
            {
                "path": hit.payload["path"],
                "content": hit.payload["content"],
                "score": hit.score,
            }
            for hit in results
        ]
        logger.info(f"Async search returned {len(result_dicts)} results")
        return result_dicts
