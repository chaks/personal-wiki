# src/lint_checks/stale_claims.py
"""Stale claims checker for wiki pages."""
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.catalog import WikiPageCatalog

logger = logging.getLogger(__name__)


@dataclass
class StaleClaim:
    """Represents a potentially stale claim in a wiki page.

    Attributes:
        page: Path to the page containing the stale claim
        claim: The claim text
        date: The date found in the content
        age_days: Age of the claim in days
    """
    page: Path
    claim: str
    date: datetime
    age_days: int


class StaleClaimsChecker:
    """Checks for potentially stale claims based on dates in content.

    Finds dates in various formats and flags claims older than a
    configurable threshold.
    """

    # Date patterns to search for
    DATE_PATTERNS = [
        # YYYY-MM-DD (ISO format)
        (r"\b(\d{4})-(\d{2})-(\d{2})\b", "%Y-%m-%d"),
        # MM/DD/YYYY (US format)
        (r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", "%m/%d/%Y"),
        # DD-MM-YYYY (European format)
        (r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b", "%d-%m-%Y"),
        # "last updated: YYYY-MM-DD" or similar
        (r"(?:last\s+updated?|updated?|modified)\s*:\s*(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
        (r"(?:last\s+updated?|updated?|modified)\s*:\s*(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),
    ]

    def __init__(self, wiki_dir: Path, max_age_days: int = 365):
        """Initialize the stale claims checker.

        Args:
            wiki_dir: Root directory for the wiki
            max_age_days: Maximum age in days before a claim is considered stale
        """
        self.wiki_dir = Path(wiki_dir)
        self.max_age_days = max_age_days
        self.catalog = WikiPageCatalog(wiki_dir)

    def _find_all_wiki_pages(self) -> list[Path]:
        """Find all wiki pages using catalog."""
        return self.catalog.find_all_pages()

    def _extract_dates_from_content(
        self, content: str
    ) -> list[tuple[datetime, str, int]]:
        """Extract dates and surrounding context from content.

        Args:
            content: Page content

        Returns:
            List of tuples (date, claim_text, line_number)
        """
        dates_found: list[tuple[datetime, str, int]] = []
        seen_dates: set[tuple[str, int]] = set()  # Track (date_str, line_num) to avoid duplicates
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern, date_format in self.DATE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    try:
                        # Extract date components from groups
                        groups = match.groups()
                        if len(groups) == 3:
                            # Parse date based on format
                            if date_format == "%Y-%m-%d":
                                date_str = f"{groups[0]}-{groups[1]}-{groups[2]}"
                                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                            elif date_format == "%m/%d/%Y":
                                date_str = f"{groups[0]}/{groups[1]}/{groups[2]}"
                                parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                            elif date_format == "%d-%m-%Y":
                                date_str = f"{groups[0]}-{groups[1]}-{groups[2]}"
                                parsed_date = datetime.strptime(date_str, "%d-%m-%Y")
                            else:
                                continue

                            # Skip if we've already found this date on this line
                            date_key = (date_str, line_num)
                            if date_key in seen_dates:
                                continue
                            seen_dates.add(date_key)

                            # Get surrounding context as the "claim"
                            claim_context = line.strip()
                            dates_found.append((parsed_date, claim_context, line_num))
                    except ValueError:
                        # Invalid date (e.g., month > 12)
                        continue

        return dates_found

    def _is_valid_date(self, date: datetime) -> bool:
        """Check if a date is valid (not in the future, not too old).

        Args:
            date: Date to validate

        Returns:
            True if date is valid
        """
        now = datetime.now()
        # Don't flag dates in the future
        return date <= now

    def check(self) -> list[StaleClaim]:
        """Find all potentially stale claims in the wiki.

        Returns:
            List of StaleClaim objects
        """
        stale_claims: list[StaleClaim] = []
        now = datetime.now()

        if not self.wiki_dir.exists():
            return stale_claims

        for page in self._find_all_wiki_pages():
            try:
                content = page.read_text()
            except (IOError, OSError) as e:
                logger.warning(f"Failed to read {page}: {e}")
                continue

            dates = self._extract_dates_from_content(content)

            for date, claim, line_num in dates:
                if not self._is_valid_date(date):
                    continue

                age_days = (now - date).days

                if age_days > self.max_age_days:
                    stale_claims.append(
                        StaleClaim(
                            page=page,
                            claim=claim,
                            date=date,
                            age_days=age_days,
                        )
                    )

        logger.info(
            f"Found {len(stale_claims)} stale claims "
            f"(older than {self.max_age_days} days)"
        )
        return stale_claims
