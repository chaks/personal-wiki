# src/lint.py
"""Wiki health checker: finds orphans, contradictions, stale claims, etc."""
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WikiLinter:
    """Checks wiki health: orphans, contradictions, stale claims, etc."""

    WIKILINK_PATTERN = r"\[\[([^\]]+)\]\]"

    def __init__(self, wiki_dir: Path):
        """Initialize the wiki linter.

        Args:
            wiki_dir: Root directory for the wiki
        """
        self.wiki_dir = Path(wiki_dir)

    def _slugify(self, name: str) -> str:
        """Convert name to slug (same as WikiPageWriter).

        Args:
            name: The name to convert to a slug

        Returns:
            A slugified version of the name suitable for filenames
        """
        slug = name.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c in "-_")
        return slug

    def _find_all_wiki_pages(self) -> list[Path]:
        """Find all wiki pages in the wiki directory.

        Returns:
            List of paths to all .md files in the wiki
        """
        pages = []
        if self.wiki_dir.exists():
            for pattern in ["**/*.md"]:
                pages.extend(self.wiki_dir.glob(pattern))
        return pages

    def _extract_wikilinks(self, page_path: Path) -> set[str]:
        """Extract all wikilink titles from a page.

        Args:
            page_path: Path to the wiki page

        Returns:
            Set of linked page titles (slugified)
        """
        try:
            content = page_path.read_text()
        except (IOError, OSError) as e:
            logger.warning(f"Failed to read {page_path}: {e}")
            return set()

        linked_titles = set()
        for match in re.finditer(self.WIKILINK_PATTERN, content):
            title = match.group(1)
            # Slugify the linked title for comparison
            linked_titles.add(self._slugify(title))

        return linked_titles

    def _get_page_slug(self, page_path: Path) -> str:
        """Get the slug for a page from its filename.

        Args:
            page_path: Path to the wiki page

        Returns:
            The slug (filename without .md extension)
        """
        return page_path.stem

    def check_orphans(self) -> list[Path]:
        """Find pages with no incoming wikilinks.

        A page is considered an orphan if no other page in the wiki
        contains a wikilink pointing to it.

        Returns:
            List of orphan page paths
        """
        # Find all wiki pages
        all_pages = self._find_all_wiki_pages()

        if not all_pages:
            return []

        # Build set of all linked slugs from all pages
        all_linked_slugs: set[str] = set()
        for page in all_pages:
            linked_slugs = self._extract_wikilinks(page)
            all_linked_slugs.update(linked_slugs)

        # Find pages whose slug doesn't appear in any linked set
        orphans = []
        for page in all_pages:
            page_slug = self._get_page_slug(page)
            if page_slug not in all_linked_slugs:
                orphans.append(page)

        logger.info(f"Found {len(orphans)} orphan pages out of {len(all_pages)} total pages")
        return orphans

    def run_all_checks(self) -> dict:
        """Run all lint checks and return results.

        Returns:
            Dictionary with results for each check category
        """
        return {
            "orphans": self.check_orphans(),
            "contradictions": [],  # TODO: implement
            "stale_claims": [],    # TODO: implement
            "broken_links": [],    # TODO: implement
            "duplicates": [],      # TODO: implement
        }
