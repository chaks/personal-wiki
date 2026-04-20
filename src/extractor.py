# src/extractor.py
"""LLM-based entity and concept extraction using Ollama."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import ollama
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an extracted entity."""
    name: str
    entity_type: str  # person, organization, product, technology, etc.
    description: str
    source_doc: Optional[str] = None


@dataclass
class Concept:
    """Represents an extracted concept."""
    name: str
    definition: str
    related_entities: list[str] = field(default_factory=list)
    source_doc: Optional[str] = None


class EntityExtractor:
    """LLM-based entity and concept extraction using Ollama."""

    DEFAULT_ENTITY_PROMPT = """Read the following document and extract key entities (concrete things like people, organizations, products, technologies). For each entity, provide:
- Name
- Type (person, organization, product, technology, etc.)
- Brief description

Format each entity as: ENTITY: name | type | description

Document:
{document}"""

    DEFAULT_CONCEPT_PROMPT = """Read the following document and extract key concepts (abstract ideas like theories, patterns, methodologies, principles). For each concept, provide:
- Name
- Definition
- Related entities (comma-separated)

Format each concept as: CONCEPT: name | definition | related_entities

Document:
{document}"""

    def __init__(self, model: str = "gemma4:e2b", schema_path: Optional[Path] = None):
        """Initialize the extractor.

        Args:
            model: Ollama model to use for extraction (default: gemma4:e2b)
            schema_path: Optional path to schema.yaml for custom prompts
        """
        self.model = model
        self.entity_prompt = self.DEFAULT_ENTITY_PROMPT
        self.concept_prompt = self.DEFAULT_CONCEPT_PROMPT

        if schema_path is not None:
            self._load_prompts(schema_path)
        else:
            # Try to load from default config location
            default_schema = Path(__file__).parent.parent / "config" / "schema.yaml"
            if default_schema.exists():
                self._load_prompts(default_schema)

        logger.debug(f"EntityExtractor initialized with model: {model}")

    def _load_prompts(self, schema_path: Path) -> None:
        """Load extraction prompts from schema file.

        Args:
            schema_path: Path to schema.yaml file
        """
        try:
            schema_content = yaml.safe_load(schema_path.read_text())
            prompts = schema_content.get("ingestion", {}).get("prompts", {})

            if "extract_entities" in prompts:
                self.entity_prompt = prompts["extract_entities"]
                logger.debug("Loaded custom entity extraction prompt from schema")

            if "extract_concepts" in prompts:
                self.concept_prompt = prompts["extract_concepts"]
                logger.debug("Loaded custom concept extraction prompt from schema")

        except Exception as e:
            logger.warning(f"Failed to load prompts from schema: {e}. Using defaults.")

    def extract(self, document: str, source_doc: Optional[str] = None) -> list[Entity]:
        """Extract entities from a document using LLM.

        Args:
            document: The document text to extract entities from
            source_doc: Optional source document reference

        Returns:
            List of extracted Entity objects
        """
        try:
            # Format prompt with document
            prompt = self.entity_prompt.format(document=document)

            # Call Ollama API
            response = ollama.chat(model=self.model, messages=[
                {"role": "user", "content": prompt}
            ])

            raw_text = response.message.content or ""

            # Parse entities from response
            entities = self._parse_entities(raw_text)

            # Add source document reference
            for entity in entities:
                entity.source_doc = source_doc

            logger.info(f"Extracted {len(entities)} entities from document")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def extract_concepts(
        self, document: str, source_doc: Optional[str] = None
    ) -> list[Concept]:
        """Extract concepts from a document using LLM.

        Args:
            document: The document text to extract concepts from
            source_doc: Optional source document reference

        Returns:
            List of extracted Concept objects
        """
        try:
            # Format prompt with document
            prompt = self.concept_prompt.format(document=document)

            # Call Ollama API
            response = ollama.chat(model=self.model, messages=[
                {"role": "user", "content": prompt}
            ])

            raw_text = response.message.content or ""

            # Parse concepts from response
            concepts = self._parse_concepts(raw_text)

            # Add source document reference
            for concept in concepts:
                concept.source_doc = source_doc

            logger.info(f"Extracted {len(concepts)} concepts from document")
            return concepts

        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return []

    def _parse_entities(self, raw_text: str) -> list[Entity]:
        """Parse entity lines from LLM response.

        Expected format: ENTITY: name | type | description

        Args:
            raw_text: Raw LLM response text

        Returns:
            List of parsed Entity objects
        """
        entities = []

        for line in raw_text.split("\n"):
            line = line.strip()
            if not line.startswith("ENTITY:"):
                continue

            # Remove ENTITY: prefix and split by pipe
            content = line.replace("ENTITY:", "").strip()
            parts = [p.strip() for p in content.split("|")]

            if len(parts) >= 3:
                entity = Entity(
                    name=parts[0],
                    entity_type=parts[1],
                    description=parts[2]
                )
                entities.append(entity)
            else:
                logger.debug(f"Skipping malformed entity line: {line}")

        return entities

    def _parse_concepts(self, raw_text: str) -> list[Concept]:
        """Parse concept lines from LLM response.

        Expected format: CONCEPT: name | definition | related_entities

        Args:
            raw_text: Raw LLM response text

        Returns:
            List of parsed Concept objects
        """
        concepts = []

        for line in raw_text.split("\n"):
            line = line.strip()
            if not line.startswith("CONCEPT:"):
                continue

            # Remove CONCEPT: prefix and split by pipe
            content = line.replace("CONCEPT:", "").strip()
            parts = [p.strip() for p in content.split("|")]

            if len(parts) >= 2:
                name = parts[0]
                definition = parts[1]

                # Parse related entities (comma-separated)
                related_entities = []
                if len(parts) >= 3 and parts[2]:
                    related_entities = [
                        e.strip() for e in parts[2].split(",") if e.strip()
                    ]

                concept = Concept(
                    name=name,
                    definition=definition,
                    related_entities=related_entities
                )
                concepts.append(concept)
            else:
                logger.debug(f"Skipping malformed concept line: {line}")

        return concepts
