"""Wiki page catalog — centralized page discovery."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WikiPageCatalog:
    """Centralized wiki page discovery.

    Replaces scattered glob patterns across lint checks with
    a single module that owns page discovery.
    """

    def __init__(
        self,
        wiki_dir: Path,
        exclude_patterns: Optional[list[str]] = None,
    ):
        """Initialize catalog.

        Args:
            wiki_dir: Root wiki directory
            exclude_patterns: Filename patterns to exclude (e.g., ["_index.md"])
        """
        self.wiki_dir = Path(wiki_dir)
        self.exclude_patterns = exclude_patterns or []

    def find_all_pages(self) -> list[Path]:
        """Find all wiki pages.

        Returns:
            Sorted list of all .md file paths
        """
        pages: list[Path] = []
        if not self.wiki_dir.exists():
            return pages

        for md_file in self.wiki_dir.glob("**/*.md"):
            if self._should_include(md_file):
                pages.append(md_file)

        return sorted(pages)

    def find_existing_slugs(self) -> set[str]:
        """Find all existing page slugs (filenames without .md).

        Returns:
            Set of slug strings
        """
        slugs: set[str] = set()
        for page in self.find_all_pages():
            slugs.add(page.stem)
        return slugs

    def _should_include(self, page_path: Path) -> bool:
        """Check if page should be included (not excluded).

        Args:
            page_path: Path to check

        Returns:
            True if page should be included
        """
        filename = page_path.name
        for pattern in self.exclude_patterns:
            if filename == pattern or filename.startswith(pattern):
                return False
        return True