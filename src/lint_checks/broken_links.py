# src/lint_checks/broken_links.py
"""Broken links checker for wiki pages."""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils import slugify

logger = logging.getLogger(__name__)


@dataclass
class BrokenLink:
    """Represents a broken wiki link.

    Attributes:
        page: Path to the page containing the broken link
        link: The linked page title/slug that doesn't exist
        line_number: Line number where the broken link appears
    """
    page: Path
    link: str
    line_number: int


class BrokenLinksChecker:
    """Checks for broken wikilinks in wiki pages.

    A broken link is a wikilink that points to a page that doesn't exist
    in the wiki.
    """

    WIKILINK_PATTERN = r"\[\[([^\]]+)\]\]"

    def __init__(self, wiki_dir: Path):
        """Initialize the broken links checker.

        Args:
            wiki_dir: Root directory for the wiki
        """
        self.wiki_dir = Path(wiki_dir)

    def _find_all_wiki_pages(self) -> set[str]:
        """Find all existing wiki page slugs.

        Returns:
            Set of all existing page slugs
        """
        existing_slugs: set[str] = set()
        if self.wiki_dir.exists():
            for md_file in self.wiki_dir.glob("**/*.md"):
                existing_slugs.add(md_file.stem)
        return existing_slugs

    def _extract_wikilinks_with_positions(
        self, page_path: Path
    ) -> list[tuple[str, int]]:
        """Extract wikilinks with their line numbers from a page.

        Args:
            page_path: Path to the wiki page

        Returns:
            List of tuples (link_title, line_number)
        """
        try:
            content = page_path.read_text()
        except (IOError, OSError) as e:
            logger.warning(f"Failed to read {page_path}: {e}")
            return []

        links: list[tuple[str, int]] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for match in re.finditer(self.WIKILINK_PATTERN, line):
                link_title = match.group(1)
                # Slugify the linked title for comparison
                slugified_link = slugify(link_title)
                links.append((slugified_link, line_num))

        return links

    def check(self) -> list[BrokenLink]:
        """Find all broken wikilinks in the wiki.

        Returns:
            List of BrokenLink objects for each broken link found
        """
        existing_slugs = self._find_all_wiki_pages()
        broken_links: list[BrokenLink] = []

        if not self.wiki_dir.exists():
            return broken_links

        for md_file in self.wiki_dir.glob("**/*.md"):
            links = self._extract_wikilinks_with_positions(md_file)
            for link_slug, line_num in links:
                if link_slug not in existing_slugs:
                    broken_links.append(
                        BrokenLink(
                            page=md_file,
                            link=link_slug,
                            line_number=line_num,
                        )
                    )

        logger.info(
            f"Found {len(broken_links)} broken links "
            f"(checked against {len(existing_slugs)} existing pages)"
        )
        return broken_links
