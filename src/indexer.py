# src/indexer.py
"""Qdrant-based semantic indexing for wiki pages."""
import hashlib
import logging
from pathlib import Path

import ollama
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768


class WikiIndexer:
    """Indexes wiki pages in Qdrant for semantic search."""

    COLLECTION_NAME = "personal_wiki"

    def __init__(self, wiki_dir: Path, qdrant_url: str = "http://localhost:6333"):
        self.wiki_dir = Path(wiki_dir)
        self.qdrant_url = qdrant_url
        self._client = None
        logger.debug(f"WikiIndexer initialized: wiki_dir={wiki_dir}, qdrant_url={qdrant_url}")

    @property
    def client(self):
        """Lazy-init Qdrant client."""
        if self._client is None:
            logger.info(f"Initializing Qdrant client: {self.qdrant_url}")
            self._client = QdrantClient(url=self.qdrant_url)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        """Create collection if not exists."""
        try:
            from qdrant_client.http.models import Distance, VectorParams

            collections = self._client.get_collections().collections
            if not any(c.name == self.COLLECTION_NAME for c in collections):
                logger.info(f"Creating collection: {self.COLLECTION_NAME}")
                self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Collection {self.COLLECTION_NAME} created successfully")
            else:
                logger.debug(f"Collection {self.COLLECTION_NAME} already exists")
        except Exception as e:
            logger.warning(f"Failed to ensure collection exists: {e}")

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using Ollama."""
        logger.debug(f"Generating embedding for {len(text)} chars")
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        embedding = response["embedding"]
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding

    def _page_id(self, page_path: Path) -> str:
        """Generate unique ID for page."""
        rel_path = page_path.relative_to(self.wiki_dir)
        page_id = hashlib.sha256(str(rel_path).encode()).hexdigest()[:16]
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

        logger.debug(f"Upserting page {page_id} to Qdrant")
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
            limit=top_k,
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
