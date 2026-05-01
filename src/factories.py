"""Factory functions for wiring production adapters."""
import logging
from pathlib import Path
from typing import Optional

from src.config import AppSettings
from src.services.llm_provider import OllamaProvider
from src.services.embedding_provider import OllamaEmbeddingProvider
from src.services.vector_store import QdrantStore
from src.indexer import WikiIndexer
from src.services.pipeline_stages import (
    EntityExtractorStage,
    WikiPageWriterStage,
    LinkResolverStage,
    WikiIndexerStage,
)

logger = logging.getLogger(__name__)


def create_default_vector_store(config: Optional[AppSettings] = None) -> QdrantStore:
    """Create QdrantStore with configured URL.

    Args:
        config: AppSettings (loads defaults if None)

    Returns:
        QdrantStore instance
    """
    if config is None:
        config = AppSettings()
    return QdrantStore(url=config.qdrant_url)


def create_default_indexer(
    wiki_dir: Path,
    config: Optional[AppSettings] = None,
) -> WikiIndexer:
    """Create WikiIndexer with production adapters.

    Args:
        wiki_dir: Wiki directory path
        config: AppSettings (loads defaults if None)

    Returns:
        WikiIndexer with QdrantStore and OllamaEmbeddingProvider
    """
    if config is None:
        config = AppSettings()
    vector_store = create_default_vector_store(config)
    embedding_provider = OllamaEmbeddingProvider(model=config.embedding_model)
    return WikiIndexer(
        wiki_dir=wiki_dir,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )


def create_default_pipeline_stages(
    wiki_dir: Path,
    config: Optional[AppSettings] = None,
) -> dict:
    """Create all pipeline stages with production adapters.

    Args:
        wiki_dir: Wiki directory path
        config: AppSettings (loads defaults if None)

    Returns:
        Dict with keys: extract, write, resolve, index
    """
    if config is None:
        config = AppSettings()

    llm_provider = OllamaProvider(model=config.llm_model)
    vector_store = create_default_vector_store(config)
    embedding_provider = OllamaEmbeddingProvider(model=config.embedding_model)

    return {
        "extract": EntityExtractorStage(llm_provider),
        "write": WikiPageWriterStage(wiki_dir),
        "resolve": LinkResolverStage(wiki_dir),
        "index": WikiIndexerStage(wiki_dir, vector_store, embedding_provider),
    }