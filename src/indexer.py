# src/indexer.py
"""Qdrant-based semantic indexing for wiki pages."""
import hashlib
import logging
from pathlib import Path
from typing import Optional

import ollama

from src.services.vector_store import VectorStore, QdrantStore, SearchPoint

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768


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
        # Generate a UUID v5-like string from the path hash
        hash_hex = hashlib.sha256(str(rel_path).encode()).hexdigest()
        # Format as UUID: 8-4-4-4-12 characters
        page_id = f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
        logger.debug(f"Generated page ID {page_id} for {rel_path}")
        return page_id

    def index_page(self, page_path: Path) -> None:
        """Embed and index a wiki page."""
        logger.info(f"Indexing page: {page_path}")
        content = page_path.read_text()
        logger.debug(f"Read {len(content)} chars from {page_path}")

        embedding = self._get_embedding(content)
        page_id = self._page_id(page_path)
        rel_path = str(page_path.relative_to(self.wiki_dir))

        logger.debug(f"Upserting page {page_id} to vector store")
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[{
                "id": page_id,
                "vector": embedding,
                "payload": {
                    "path": rel_path,
                    "content": content,
                    "title": page_path.stem,
                },
            }],
        )
        logger.info(f"Successfully indexed {page_path.name}")

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
