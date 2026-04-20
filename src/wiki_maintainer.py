# src/wiki_maintainer.py
"""LLM-powered wiki page maintenance."""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WikiPage:
    """Represents a wiki page."""

    title: str
    category: str
    content: str
    links: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None

    def to_markdown(self) -> str:
        """Render page as markdown with frontmatter."""
        frontmatter = f"""---
title: {self.title}
category: {self.category}
created_at: {self.created_at}
"""
        if self.updated_at:
            frontmatter += f"updated_at: {self.updated_at}\n"

        if self.links:
            frontmatter += f"links: {self.links}\n"

        frontmatter += "---\n\n"

        body = f"# {self.title}\n\n{self.content}"

        if self.links:
            body += "\n\n## See Also\n\n"
            for link in self.links:
                link_name = Path(link).stem
                body += f"- [[{link_name}]]\n"

        return frontmatter + body


class WikiMaintainer:
    """Manages wiki page creation and updates."""

    def __init__(self, wiki_dir: Path):
        self.wiki_dir = Path(wiki_dir)
        logger.debug(f"WikiMaintainer initialized: {wiki_dir}")

    def create_page(
        self,
        title: str,
        category: str,
        content: str,
        links: Optional[list[str]] = None,
    ) -> WikiPage:
        """Create a new wiki page."""
        logger.info(f"Creating wiki page: '{title}' in {category}")
        page = WikiPage(
            title=title,
            category=category,
            content=content,
            links=links or [],
        )
        file_path = self._save_page(page)
        logger.info(f"Created wiki page at {file_path}")
        return page

    def update_page(
        self,
        page: WikiPage,
        content: Optional[str] = None,
        links: Optional[list[str]] = None,
    ) -> WikiPage:
        """Update an existing wiki page."""
        logger.info(f"Updating wiki page: '{page.title}'")
        if content:
            page.content = content
            logger.debug(f"Updated content ({len(content)} chars)")
        if links:
            page.links = links
            logger.debug(f"Updated links: {links}")
        page.updated_at = datetime.now().isoformat()
        file_path = self._save_page(page)
        logger.info(f"Updated wiki page at {file_path}")
        return page

    def _save_page(self, page: WikiPage) -> Path:
        """Save page to disk."""
        category_dir = self.wiki_dir / page.category
        category_dir.mkdir(parents=True, exist_ok=True)

        filename = self._slugify(page.title) + ".md"
        file_path = category_dir / filename

        markdown = page.to_markdown()
        file_path.write_text(markdown)
        logger.debug(f"Saved {len(markdown)} chars to {file_path}")
        return file_path

    def _slugify(self, title: str) -> str:
        """Convert title to filename-safe slug."""
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")
