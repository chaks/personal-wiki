# src/lint_checks/duplicates.py
"""Duplicate content checker for wiki pages."""
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.catalog import WikiPageCatalog

logger = logging.getLogger(__name__)


@dataclass
class DuplicatePair:
    """Represents a pair of duplicate or similar pages.

    Attributes:
        page_a: Path to the first page
        page_b: Path to the second page
        similarity: Similarity score (1.0 for exact, <1.0 for near-duplicates)
        match_type: 'exact' or 'near'
    """
    page_a: Path
    page_b: Path
    similarity: float
    match_type: str


class DuplicateContentChecker:
    """Checks for duplicate or near-duplicate content in wiki pages.

    Uses content hashing for exact duplicates and Jaccard similarity
    for near-duplicates.
    """

    def __init__(self, wiki_dir: Path, similarity_threshold: float = 0.7):
        """Initialize the duplicate content checker.

        Args:
            wiki_dir: Root directory for the wiki
            similarity_threshold: Minimum Jaccard similarity to flag as near-duplicate
        """
        self.wiki_dir = Path(wiki_dir)
        self.similarity_threshold = similarity_threshold
        self.catalog = WikiPageCatalog(wiki_dir)

    def _find_all_wiki_pages(self) -> list[Path]:
        """Find all wiki pages using catalog."""
        return self.catalog.find_all_pages()

    def _get_content_hash(self, page_path: Path) -> Optional[str]:
        """Get SHA256 hash of page content (excluding frontmatter).

        Args:
            page_path: Path to the wiki page

        Returns:
            SHA256 hash of content, or None if read fails
        """
        try:
            content = page_path.read_text()
        except (IOError, OSError) as e:
            logger.warning(f"Failed to read {page_path}: {e}")
            return None

        # Remove YAML frontmatter for hashing
        content_without_frontmatter = self._strip_frontmatter(content)

        return hashlib.sha256(content_without_frontmatter.encode()).hexdigest()

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content.

        Args:
            content: Page content with possible frontmatter

        Returns:
            Content without frontmatter
        """
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content.strip()

    def _tokenize_content(self, page_path: Path) -> Optional[set[str]]:
        """Tokenize page content into a set of words.

        Args:
            page_path: Path to the wiki page

        Returns:
            Set of lowercase tokens, or None if read fails
        """
        try:
            content = page_path.read_text()
        except (IOError, OSError) as e:
            logger.warning(f"Failed to read {page_path}: {e}")
            return None

        # Strip frontmatter
        content = self._strip_frontmatter(content)

        # Tokenize: lowercase, split on whitespace and punctuation
        tokens = set(re.findall(r"\b\w+\b", content.lower()))
        return tokens

    def _jaccard_similarity(self, set_a: set[str], set_b: set[str]) -> float:
        """Calculate Jaccard similarity between two sets.

        Args:
            set_a: First set of tokens
            set_b: Second set of tokens

        Returns:
            Jaccard similarity score (0.0 to 1.0)
        """
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def check(self) -> list[DuplicatePair]:
        """Find all duplicate and near-duplicate pages.

        Returns:
            List of DuplicatePair objects
        """
        pages = self._find_all_wiki_pages()
        duplicates: list[DuplicatePair] = []

        if len(pages) < 2:
            return duplicates

        # Step 1: Find exact duplicates using content hashes
        hash_to_pages: dict[str, list[Path]] = {}
        for page in pages:
            content_hash = self._get_content_hash(page)
            if content_hash:
                hash_to_pages.setdefault(content_hash, []).append(page)

        # Add exact duplicates
        for hash_val, page_list in hash_to_pages.items():
            if len(page_list) > 1:
                # Create pairs for all combinations
                for i in range(len(page_list)):
                    for j in range(i + 1, len(page_list)):
                        duplicates.append(
                            DuplicatePair(
                                page_a=page_list[i],
                                page_b=page_list[j],
                                similarity=1.0,
                                match_type="exact",
                            )
                        )

        # Step 2: Find near-duplicates using Jaccard similarity
        # Only compare pages that aren't exact duplicates
        page_tokens: dict[Path, set[str]] = {}
        for page in pages:
            tokens = self._tokenize_content(page)
            if tokens:
                page_tokens[page] = tokens

        # Compare all pairs (avoiding already-found exact duplicates)
        exact_duplicate_pairs = {(d.page_a, d.page_b) for d in duplicates}
        pages_list = list(page_tokens.keys())

        for i in range(len(pages_list)):
            for j in range(i + 1, len(pages_list)):
                page_a = pages_list[i]
                page_b = pages_list[j]

                # Skip if already found as exact duplicate
                if (page_a, page_b) in exact_duplicate_pairs:
                    continue
                if (page_b, page_a) in exact_duplicate_pairs:
                    continue

                similarity = self._jaccard_similarity(
                    page_tokens[page_a], page_tokens[page_b]
                )

                if similarity >= self.similarity_threshold and similarity < 1.0:
                    duplicates.append(
                        DuplicatePair(
                            page_a=page_a,
                            page_b=page_b,
                            similarity=similarity,
                            match_type="near",
                        )
                    )

        logger.info(
            f"Found {len(duplicates)} duplicate/similar page pairs "
            f"out of {len(pages)} pages"
        )
        return duplicates
