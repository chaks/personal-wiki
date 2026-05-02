from __future__ import annotations
"""LLM-based entity and concept extraction using Ollama."""
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.services.llm_provider import LLMProvider, OllamaProvider

logger = logging.getLogger(__name__)

# Max characters sent to LLM for extraction — longer docs cause looping
_EXTRACT_CHUNK_SIZE = 4000


@dataclass
class Entity:
    """Represents an extracted entity."""
    name: str
    entity_type: str  # person, organization, product, technology, etc.
    description: str
    source_doc: str | None = None


@dataclass
class Concept:
    """Represents an extracted concept."""
    name: str
    definition: str
    related_entities: list[str] = field(default_factory=list)
    source_doc: str | None = None


class EntityExtractor:
    """LLM-based entity and concept extraction using Ollama."""

    ENTITY_SYSTEM = (
        "You are a strict entity extraction system. "
        "Extract key entities from the provided document. "
        "Output ONLY lines starting with 'ENTITY:' — no other text whatsoever. "
        "Format: ENTITY: <name>|<type>|<one-line description> "
        "Types: person, organization, product, technology, framework, protocol, "
        "pattern, methodology, book, company, principle, quality, concept."
    )

    CONCEPT_SYSTEM = (
        "You are a strict concept extraction system. "
        "Extract key concepts from the provided document. "
        "Output ONLY lines starting with 'CONCEPT:' — no other text whatsoever. "
        "Format: CONCEPT: <name>|<one-sentence definition>|<comma-separated related entity names or N/A>"
    )

    ENTITY_PROMPT = """<document>
{document}
</document>

Extract 10-20 key entities mentioned in this document.
Format each as exactly one line:
ENTITY: <name>|<type>|<description>

Rules:
- Start EVERY line with ENTITY:
- Use pipe | as separator — no spaces around pipes
- Only mention things ACTUALLY discussed in the document
- ONLY ENTITY: lines — no intro, no outro, no blank lines"""

    CONCEPT_PROMPT = """<document>
{document}
</document>

Extract 8-15 key concepts from this document.
Format each as exactly one line:
CONCEPT: <name>|<definition>|<related_entities>

Rules:
- Start EVERY line with CONCEPT:
- Use pipe | as separator — no spaces around pipes
- Keep definitions to 1 sentence
- related_entities: comma-separated names from document, or N/A
- Only mention things ACTUALLY discussed in the document
- ONLY CONCEPT: lines — no intro, no outro, no blank lines"""

    def __init__(
        self,
        model: str = "gemma4:e2b",
        schema_path: Path | None = None,
        llm_provider: LLMProvider | None = None,
    ):
        """Initialize the extractor.

        Args:
            model: Ollama model to use for extraction (default: gemma4:e2b)
            schema_path: Optional path to schema.yaml for custom prompts
            llm_provider: Optional LLM provider instance (creates default if None)
        """
        self.llm_provider = llm_provider or OllamaProvider(model=model)
        self.entity_prompt = self.ENTITY_PROMPT
        self.concept_prompt = self.CONCEPT_PROMPT

        if schema_path is not None:
            self._load_prompts(schema_path)
        else:
            default_schema = Path(__file__).parent.parent / "config" / "schema.yaml"
            if default_schema.exists():
                self._load_prompts(default_schema)

        logger.debug(f"EntityExtractor initialized with provider: {type(self.llm_provider).__name__}")

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

    def _get_document_chunk(self, document: str) -> str:
        """Get a representative chunk of the document for extraction.

        Long documents cause the LLM to loop. Use the first chunk that is
        within the extraction window.

        Args:
            document: Full document text

        Returns:
            Document chunk suitable for LLM extraction
        """
        if len(document) <= _EXTRACT_CHUNK_SIZE:
            return document
        # Include first chunk + a later chunk for coverage
        first = document[:_EXTRACT_CHUNK_SIZE // 2]
        mid_start = len(document) // 3
        second = document[mid_start:mid_start + _EXTRACT_CHUNK_SIZE // 2]
        return first + "\n...\n" + second

    async def extract(self, document: str, source_doc: str | None = None) -> list[Entity]:
        """Extract entities from a document using LLM (async).

        Args:
            document: The document text to extract entities from
            source_doc: Optional source document reference

        Returns:
            List of extracted Entity objects
        """
        try:
            chunk = self._get_document_chunk(document)
            prompt = self.entity_prompt.format(document=chunk)

            raw_text = await self.llm_provider.generate_async(
                prompt, system=self.ENTITY_SYSTEM
            )

            entities = self._parse_entities(raw_text)

            # Deduplicate by name (case-insensitive)
            seen = set()
            unique = []
            for e in entities:
                key = e.name.lower().strip()
                if key not in seen:
                    seen.add(key)
                    e.source_doc = source_doc
                    unique.append(e)

            logger.info(f"Extracted {len(unique)} unique entities from document")
            return unique

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    async def extract_concepts(
        self, document: str, source_doc: str | None = None
    ) -> list[Concept]:
        """Extract concepts from a document using LLM (async).

        Args:
            document: The document text to extract concepts from
            source_doc: Optional source document reference

        Returns:
            List of extracted Concept objects
        """
        try:
            chunk = self._get_document_chunk(document)
            prompt = self.concept_prompt.format(document=chunk)

            raw_text = await self.llm_provider.generate_async(
                prompt, system=self.CONCEPT_SYSTEM
            )

            concepts = self._parse_concepts(raw_text)

            # Deduplicate by name (case-insensitive)
            seen = set()
            unique = []
            for c in concepts:
                key = c.name.lower().strip()
                if key not in seen:
                    seen.add(key)
                    c.source_doc = source_doc
                    unique.append(c)

            logger.info(f"Extracted {len(unique)} unique concepts from document")
            return unique

        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return []

    def _parse_lines(
        self,
        raw_text: str,
        prefix: str,
        min_parts: int,
        builder,
    ) -> list:
        """Parse pipe-delimited lines with a given prefix from LLM response.

        Args:
            raw_text: Raw LLM response text.
            prefix: Expected line prefix (e.g. "ENTITY" or "CONCEPT").
            min_parts: Minimum number of pipe-delimited parts required.
            builder: Callable receiving (*parts) returning a dataclass instance.

        Returns:
            List of built items, deduplicated by name (case-insensitive).
        """
        items: list = []
        seen: set[str] = set()

        for line in raw_text.splitlines():
            line = line.strip()
            if not line.startswith(f"{prefix}:"):
                continue

            content = line.replace(f"{prefix}:", "").strip()
            parts = [p.strip() for p in content.split("|")]

            if len(parts) < min_parts:
                logger.debug(f"Skipping malformed line: {line}")
                continue

            key = parts[0].lower()
            if key in seen:
                continue
            seen.add(key)

            items.append(builder(*parts))

        return items

    def _parse_entities(self, raw_text: str) -> list[Entity]:
        """Parse entity lines from LLM response."""
        return self._parse_lines(
            raw_text,
            "ENTITY",
            3,
            lambda name, etype, desc: Entity(name=name, entity_type=etype, description=desc),
        )

    def _parse_concepts(self, raw_text: str) -> list[Concept]:
        """Parse concept lines from LLM response."""
        def build(name: str, definition: str, *related: str) -> Concept:
            rel = (
                [e.strip() for e in related[0].split(",") if e.strip()]
                if related and related[0]
                else []
            )
            return Concept(name=name, definition=definition, related_entities=rel)

        return self._parse_lines(raw_text, "CONCEPT", 2, build)
