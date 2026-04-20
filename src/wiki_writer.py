# src/wiki_writer.py
"""Wiki page writer for entities and concepts."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.extractor import Entity, Concept

logger = logging.getLogger(__name__)


class WikiPageWriter:
    """Writes entity and concept pages to wiki directories."""

    def __init__(self, wiki_dir: Path):
        """Initialize the wiki page writer.

        Args:
            wiki_dir: Root directory for the wiki
        """
        self.wiki_dir = Path(wiki_dir)
        self.entities_dir = self.wiki_dir / "entities"
        self.concepts_dir = self.wiki_dir / "concepts"
        self.documents_dir = self.wiki_dir / "documents"

        # Ensure directories exist
        self.entities_dir.mkdir(parents=True, exist_ok=True)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"WikiPageWriter initialized with wiki_dir: {wiki_dir}")

    def _slugify(self, name: str) -> str:
        """Convert name to safe filename.

        Args:
            name: The name to convert to a slug

        Returns:
            A slugified version of the name suitable for filenames
        """
        slug = name.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c in "-_")
        return slug

    def write_entity(self, entity: Entity) -> Optional[Path]:
        """Write an entity page.

        Args:
            entity: The Entity to write

        Returns:
            Path to the written file, or None if writing failed
        """
        slug = self._slugify(entity.name)
        output_path = self.entities_dir / f"{slug}.md"

        # Path validation: ensure the output path stays within the intended directory
        try:
            resolved_path = output_path.resolve()
            resolved_entities = self.entities_dir.resolve()
            if not resolved_path.is_relative_to(resolved_entities):
                logger.error(f"Path traversal detected: {output_path} is not within {self.entities_dir}")
                return None
        except (ValueError, OSError) as e:
            logger.error(f"Failed to resolve path for entity '{entity.name}': {e}")
            return None

        content = self._format_entity_page(entity)

        try:
            output_path.write_text(content)
            logger.info(f"Wrote entity page for '{entity.name}' to {output_path}")
            return output_path
        except (IOError, OSError) as e:
            logger.error(f"Failed to write entity page for '{entity.name}': {e}")
            return None

    def write_concept(self, concept: Concept) -> Optional[Path]:
        """Write a concept page.

        Args:
            concept: The Concept to write

        Returns:
            Path to the written file, or None if writing failed
        """
        slug = self._slugify(concept.name)
        output_path = self.concepts_dir / f"{slug}.md"

        # Path validation: ensure the output path stays within the intended directory
        try:
            resolved_path = output_path.resolve()
            resolved_concepts = self.concepts_dir.resolve()
            if not resolved_path.is_relative_to(resolved_concepts):
                logger.error(f"Path traversal detected: {output_path} is not within {self.concepts_dir}")
                return None
        except (ValueError, OSError) as e:
            logger.error(f"Failed to resolve path for concept '{concept.name}': {e}")
            return None

        content = self._format_concept_page(concept)

        try:
            output_path.write_text(content)
            logger.info(f"Wrote concept page for '{concept.name}' to {output_path}")
            return output_path
        except (IOError, OSError) as e:
            logger.error(f"Failed to write concept page for '{concept.name}': {e}")
            return None

    def _format_entity_page(self, entity: Entity) -> str:
        """Format entity as wiki page with frontmatter.

        Args:
            entity: The Entity to format

        Returns:
            Formatted markdown content with frontmatter
        """
        created_at = datetime.now().isoformat()

        # Build frontmatter
        frontmatter = [
            "---",
            f"title: {entity.name}",
            "category: entity",
            f"entity_type: {entity.entity_type}",
            f"created_at: {created_at}",
        ]

        if entity.source_doc:
            frontmatter.append(f"source: {entity.source_doc}")

        frontmatter.append("---")

        # Build body
        body_lines = [
            "",
            f"# {entity.name}",
            "",
            f"{entity.description}",
            "",
        ]

        # Add See Also section if there are related entities in description
        # For now, we'll add a placeholder or extract wikilinks from description
        body_lines.append("## See Also")
        body_lines.append("")
        body_lines.append("<!-- Add related entity wikilinks here -->")
        body_lines.append("")

        return "\n".join(frontmatter) + "\n" + "\n".join(body_lines)

    def _format_concept_page(self, concept: Concept) -> str:
        """Format concept as wiki page with frontmatter.

        Args:
            concept: The Concept to format

        Returns:
            Formatted markdown content with frontmatter
        """
        created_at = datetime.now().isoformat()

        # Build frontmatter
        frontmatter = [
            "---",
            f"title: {concept.name}",
            "category: concept",
            f"created_at: {created_at}",
        ]

        if concept.source_doc:
            frontmatter.append(f"source: {concept.source_doc}")

        frontmatter.append("---")

        # Build body
        body_lines = [
            "",
            f"# {concept.name}",
            "",
            f"{concept.definition}",
            "",
        ]

        # Add Related Entities section with wikilinks
        if concept.related_entities:
            body_lines.append("## Related Entities")
            body_lines.append("")
            for related_entity in concept.related_entities:
                body_lines.append(f"- [[{related_entity}]]")
            body_lines.append("")

        return "\n".join(frontmatter) + "\n" + "\n".join(body_lines)
