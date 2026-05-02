from __future__ import annotations
"""Centralized configuration management using Pydantic."""
import logging
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """Application settings loaded from YAML."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service settings
    llm_model: str = "gemma4:e2b"
    embedding_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "personal_wiki"

    # Wiki settings
    wiki_categories: list[str] = ["entities", "concepts", "events", "documents"]
    wiki_frontmatter_required: list[str] = ["title", "category"]
    wiki_frontmatter_optional: list[str] = ["created_at", "updated_at", "links", "source_refs"]

    # Ingestion settings
    ingestion_output_dir: str = "generated"
    ingestion_enable_entity_extraction: bool = True
    ingestion_enable_concept_extraction: bool = True

    @classmethod
    def from_yaml(cls, config_path: Path) -> "AppSettings":
        """Load settings from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            AppSettings instance
        """
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        try:
            config_content = yaml.safe_load(config_path.read_text())

            if not config_content:
                logger.warning(f"Empty config file: {config_path}, using defaults")
                return cls()

            # Flatten nested config structure
            flat_config = {}

            # Service settings
            services = config_content.get("services", {})
            llm = services.get("llm", {})
            vector = services.get("vector_store", {})

            flat_config["llm_model"] = llm.get("model", cls.model_fields["llm_model"].default)
            flat_config["embedding_model"] = llm.get("embedding_model", cls.model_fields["embedding_model"].default)
            flat_config["qdrant_url"] = vector.get("url", cls.model_fields["qdrant_url"].default)
            flat_config["qdrant_collection"] = vector.get("collection", cls.model_fields["qdrant_collection"].default)

            # Wiki settings
            wiki = config_content.get("wiki", {})
            flat_config["wiki_categories"] = wiki.get("categories", cls.model_fields["wiki_categories"].default)

            frontmatter = wiki.get("frontmatter", {})
            flat_config["wiki_frontmatter_required"] = frontmatter.get("required", cls.model_fields["wiki_frontmatter_required"].default)
            flat_config["wiki_frontmatter_optional"] = frontmatter.get("optional", cls.model_fields["wiki_frontmatter_optional"].default)

            # Ingestion settings
            ingestion = config_content.get("ingestion", {})
            flat_config["ingestion_output_dir"] = ingestion.get("output_dir", cls.model_fields["ingestion_output_dir"].default)
            flat_config["ingestion_enable_entity_extraction"] = ingestion.get("enable_entity_extraction", cls.model_fields["ingestion_enable_entity_extraction"].default)
            flat_config["ingestion_enable_concept_extraction"] = ingestion.get("enable_concept_extraction", cls.model_fields["ingestion_enable_concept_extraction"].default)

            logger.info(f"Loaded configuration from {config_path}")
            return cls(**flat_config)

        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return cls()

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "services": {
                "llm": {
                    "model": self.llm_model,
                    "embedding_model": self.embedding_model,
                },
                "vector_store": {
                    "url": self.qdrant_url,
                    "collection": self.qdrant_collection,
                },
            },
            "wiki": {
                "categories": self.wiki_categories,
                "frontmatter": {
                    "required": self.wiki_frontmatter_required,
                    "optional": self.wiki_frontmatter_optional,
                },
            },
            "ingestion": {
                "output_dir": self.ingestion_output_dir,
                "enable_entity_extraction": self.ingestion_enable_entity_extraction,
                "enable_concept_extraction": self.ingestion_enable_concept_extraction,
            },
        }
