# src/link_resolver.py
"""Link resolver for wikilinks extraction and placeholder creation."""
import logging
import re
from datetime import datetime
from pathlib import Path

from src.utils import slugify

logger = logging.getLogger(__name__)

_WIKILINK_PATTERN = r"\[\[([^\]]+)\]\]"


class LinkResolver:
    """Finds and resolves wikilinks, creating placeholder pages as needed."""

    def __init__(self, wiki_dir: Path):
        """Initialize the link resolver.

        Args:
            wiki_dir: Root directory for the wiki

        Raises:
            NotADirectoryError: If wiki_dir is not a directory
        """
        self.wiki_dir = Path(wiki_dir)
        if not self.wiki_dir.is_dir():
            raise NotADirectoryError(f"wiki_dir must be a directory: {wiki_dir}")
        self.entities_dir = self.wiki_dir / "entities"
        self.concepts_dir = self.wiki_dir / "concepts"

        logger.debug(f"LinkResolver initialized with wiki_dir: {wiki_dir}")

    def extract_links(self, content: str) -> list[str]:
        """Extract all wikilinks from content.

        Args:
            content: The markdown content to extract wikilinks from

        Returns:
            List of extracted wikilink titles
        """
        matches = re.findall(_WIKILINK_PATTERN, content)
        logger.debug(f"Extracted {len(matches)} wikilinks from content")
        return matches

    def page_exists(self, title: str) -> bool:
        """Check if a page exists for the given title.

        Searches both entities/ and concepts/ directories.

        Args:
            title: The title of the page to check

        Returns:
            True if page exists, False otherwise
        """
        slug = slugify(title)

        # Check entities directory
        entity_path = self.entities_dir / f"{slug}.md"
        if entity_path.exists():
            logger.debug(f"Found entity page: {entity_path}")
            return True

        # Check concepts directory
        concept_path = self.concepts_dir / f"{slug}.md"
        if concept_path.exists():
            logger.debug(f"Found concept page: {concept_path}")
            return True

        logger.debug(f"No page found for title: {title}")
        return False

    def create_placeholder(self, title: str) -> Path:
        """Create a placeholder page for a missing link.

        Creates a minimal page in the entities/ directory with frontmatter.

        Args:
            title: The title of the page to create

        Returns:
            Path to the created placeholder page
        """
        slug = slugify(title)
        placeholder_path = self.entities_dir / f"{slug}.md"

        # Ensure entities directory exists
        self.entities_dir.mkdir(parents=True, exist_ok=True)

        # Create frontmatter
        created_at = datetime.now().isoformat()
        frontmatter = [
            "---",
            f"title: {title}",
            "category: entity",
            f"created_at: {created_at}",
            "---",
        ]

        # Create body
        body = [
            "",
            f"# {title}",
            "",
            f"<!-- Placeholder page for [[{title}]] -->",
            "",
        ]

        content = "\n".join(frontmatter) + "\n" + "\n".join(body)

        try:
            placeholder_path.write_text(content)
            logger.info(f"Created placeholder page for '{title}' at {placeholder_path}")
            return placeholder_path
        except (IOError, OSError) as e:
            logger.error(f"Failed to create placeholder for '{title}': {e}")
            raise

    def find_missing_links(self, page_path: Path) -> list[str]:
        """Find wikilinks that don't have corresponding pages.

        Args:
            page_path: Path to the markdown file to scan

        Returns:
            List of wikilink titles that don't have corresponding pages
        """
        try:
            content = page_path.read_text()
        except (IOError, OSError) as e:
            logger.error(f"Failed to read page {page_path}: {e}")
            return []

        links = self.extract_links(content)
        missing_links = []

        for link in links:
            if not self.page_exists(link):
                missing_links.append(link)

        logger.debug(f"Found {len(missing_links)} missing links in {page_path}")
        return missing_links

    def resolve_all(self, page_path: Path) -> list[Path]:
        """Resolve all wikilinks in a page, creating placeholders.

        Args:
            page_path: Path to the markdown file to resolve links in

        Returns:
            List of paths to created placeholder pages
        """
        missing_links = self.find_missing_links(page_path)

        # Use set to avoid creating duplicate placeholders for same link
        unique_missing = list(dict.fromkeys(missing_links))

        created_paths = []
        for link_title in unique_missing:
            try:
                placeholder_path = self.create_placeholder(link_title)
                created_paths.append(placeholder_path)
            except (IOError, OSError) as e:
                logger.error(f"Failed to create placeholder for '{link_title}': {e}")

        logger.info(f"Resolved {len(created_paths)} missing links in {page_path}")
        return created_paths
