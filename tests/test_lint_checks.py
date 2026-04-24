# tests/test_lint_checks.py
"""Tests for lint check modules."""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta

from src.lint_checks.broken_links import BrokenLinksChecker, BrokenLink
from src.lint_checks.duplicates import DuplicateContentChecker, DuplicatePair
from src.lint_checks.stale_claims import StaleClaimsChecker, StaleClaim
from src.lint_checks.contradictions import ContradictionChecker
from src.lint import WikiLinter


@pytest.fixture
def wiki_dir():
    """Create a temporary wiki directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestBrokenLinksChecker:
    """Tests for BrokenLinksChecker."""

    def test_no_broken_links_when_all_linked(self, wiki_dir):
        """No broken links when all wikilinks point to existing pages."""
        # Create pages that link to each other
        page_a = wiki_dir / "page-a.md"
        page_a.write_text("# Page A\n\nSee [[Page B]].\n")

        page_b = wiki_dir / "page-b.md"
        page_b.write_text("# Page B\n\nSee [[Page A]].\n")

        checker = BrokenLinksChecker(wiki_dir)
        broken = checker.check()

        assert len(broken) == 0

    def test_detects_broken_links(self, wiki_dir):
        """Detects links to non-existent pages."""
        # Create a page with a broken link
        page = wiki_dir / "page.md"
        page.write_text("# Page\n\nSee [[Nonexistent Page]].\n")

        checker = BrokenLinksChecker(wiki_dir)
        broken = checker.check()

        assert len(broken) == 1
        assert broken[0].page == page
        assert broken[0].link == "nonexistent-page"
        assert broken[0].line_number == 3

    def test_detects_multiple_broken_links(self, wiki_dir):
        """Detects multiple broken links in the same page."""
        page = wiki_dir / "page.md"
        page.write_text(
            "# Page\n\n"
            "See [[Missing A]] and [[Missing B]].\n"
            "Also [[Missing A]] again.\n"
        )

        checker = BrokenLinksChecker(wiki_dir)
        broken = checker.check()

        # Should find 3 broken link occurrences
        assert len(broken) == 3

    def test_mixed_links(self, wiki_dir):
        """Correctly handles mix of valid and broken links."""
        # Create one existing page
        existing = wiki_dir / "existing.md"
        existing.write_text("# Existing Page\n")

        # Create page with mixed links
        page = wiki_dir / "page.md"
        page.write_text("# Page\n\nSee [[Existing]] and [[Missing]].\n")

        checker = BrokenLinksChecker(wiki_dir)
        broken = checker.check()

        assert len(broken) == 1
        assert broken[0].link == "missing"

    def test_empty_wiki(self, wiki_dir):
        """Returns empty list for empty wiki."""
        checker = BrokenLinksChecker(wiki_dir)
        broken = checker.check()
        assert len(broken) == 0


class TestDuplicateContentChecker:
    """Tests for DuplicateContentChecker."""

    def test_no_duplicates(self, wiki_dir):
        """No duplicates when pages have different content."""
        page_a = wiki_dir / "page-a.md"
        page_a.write_text("# Page A\n\nUnique content for page A.\n")

        page_b = wiki_dir / "page-b.md"
        page_b.write_text("# Page B\n\nCompletely different content here.\n")

        checker = DuplicateContentChecker(wiki_dir)
        duplicates = checker.check()

        assert len(duplicates) == 0

    def test_exact_duplicates(self, wiki_dir):
        """Detects exact duplicate content."""
        content = "# Page\n\nThis is some content.\n"

        page_a = wiki_dir / "page-a.md"
        page_a.write_text(content)

        page_b = wiki_dir / "page-b.md"
        page_b.write_text(content)

        checker = DuplicateContentChecker(wiki_dir)
        duplicates = checker.check()

        assert len(duplicates) == 1
        assert duplicates[0].match_type == "exact"
        assert duplicates[0].similarity == 1.0

    def test_near_duplicates(self, wiki_dir):
        """Detects near-duplicate content using Jaccard similarity."""
        # Create pages with similar but not identical content
        page_a = wiki_dir / "page-a.md"
        page_a.write_text(
            "# Introduction\n\n"
            "Machine learning is a subset of artificial intelligence.\n"
            "It enables computers to learn from data.\n"
        )

        page_b = wiki_dir / "page-b.md"
        page_b.write_text(
            "# Intro\n\n"
            "Machine learning is a subset of artificial intelligence.\n"
            "It allows systems to learn from data patterns.\n"
        )

        checker = DuplicateContentChecker(wiki_dir, similarity_threshold=0.5)
        duplicates = checker.check()

        # Should find near-duplicate
        near_duplicates = [d for d in duplicates if d.match_type == "near"]
        assert len(near_duplicates) > 0

    def test_frontmatter_excluded_from_hash(self, wiki_dir):
        """Frontmatter is excluded from duplicate detection."""
        content_body = "# Page\n\nThis is the content.\n"

        page_a = wiki_dir / "page-a.md"
        page_a.write_text(f"---\ntitle: Page A\ncreated: 2024-01-01\n---\n\n{content_body}")

        page_b = wiki_dir / "page-b.md"
        page_b.write_text(f"---\ntitle: Page B\ncreated: 2024-06-01\n---\n\n{content_body}")

        checker = DuplicateContentChecker(wiki_dir)
        duplicates = checker.check()

        assert len(duplicates) == 1
        assert duplicates[0].match_type == "exact"

    def test_empty_wiki(self, wiki_dir):
        """Returns empty list for empty wiki."""
        checker = DuplicateContentChecker(wiki_dir)
        duplicates = checker.check()
        assert len(duplicates) == 0

    def test_single_page(self, wiki_dir):
        """Returns empty list when only one page exists."""
        page = wiki_dir / "page.md"
        page.write_text("# Page\n\nContent.\n")

        checker = DuplicateContentChecker(wiki_dir)
        duplicates = checker.check()
        assert len(duplicates) == 0


class TestStaleClaimsChecker:
    """Tests for StaleClaimsChecker."""

    def test_no_stale_claims_when_recent(self, wiki_dir):
        """No stale claims when dates are recent."""
        recent_date = datetime.now() - timedelta(days=30)
        date_str = recent_date.strftime("%Y-%m-%d")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nLast updated: {date_str}\n\nRecent content.\n")

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 0

    def test_detects_stale_claims_iso_format(self, wiki_dir):
        """Detects stale claims with YYYY-MM-DD format."""
        old_date = datetime.now() - timedelta(days=400)
        date_str = old_date.strftime("%Y-%m-%d")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nLast updated: {date_str}\n\nOld content.\n")

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 1
        assert stale[0].page == page
        assert stale[0].age_days > 365

    def test_detects_stale_claims_us_format(self, wiki_dir):
        """Detects stale claims with MM/DD/YYYY format."""
        old_date = datetime.now() - timedelta(days=400)
        date_str = old_date.strftime("%m/%d/%Y")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nUpdated: {date_str}\n\nOld content.\n")

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 1

    def test_detects_stale_claims_european_format(self, wiki_dir):
        """Detects stale claims with DD-MM-YYYY format."""
        old_date = datetime.now() - timedelta(days=400)
        date_str = old_date.strftime("%d-%m-%Y")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nModified: {date_str}\n\nOld content.\n")

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 1

    def test_multiple_stale_claims(self, wiki_dir):
        """Detects multiple stale claims in same page."""
        old_date1 = datetime.now() - timedelta(days=400)
        old_date2 = datetime.now() - timedelta(days=500)

        page = wiki_dir / "page.md"
        page.write_text(
            f"# Page\n\n"
            f"First update: {old_date1.strftime('%Y-%m-%d')}\n"
            f"Second update: {old_date2.strftime('%Y-%m-%d')}\n"
        )

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 2

    def test_mixed_dates_stale_and_fresh(self, wiki_dir):
        """Only flags stale dates, not recent ones."""
        old_date = datetime.now() - timedelta(days=400)
        recent_date = datetime.now() - timedelta(days=30)

        page = wiki_dir / "page.md"
        page.write_text(
            f"# Page\n\n"
            f"Old: {old_date.strftime('%Y-%m-%d')}\n"
            f"Recent: {recent_date.strftime('%Y-%m-%d')}\n"
        )

        checker = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale = checker.check()

        assert len(stale) == 1

    def test_empty_wiki(self, wiki_dir):
        """Returns empty list for empty wiki."""
        checker = StaleClaimsChecker(wiki_dir)
        stale = checker.check()
        assert len(stale) == 0

    def test_custom_max_age(self, wiki_dir):
        """Respects custom max_age_days setting."""
        # Date that is 100 days old
        old_date = datetime.now() - timedelta(days=100)
        date_str = old_date.strftime("%Y-%m-%d")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nUpdated: {date_str}\n")

        # With 365 day threshold, should not be stale
        checker_365 = StaleClaimsChecker(wiki_dir, max_age_days=365)
        stale_365 = checker_365.check()
        assert len(stale_365) == 0

        # With 30 day threshold, should be stale
        checker_30 = StaleClaimsChecker(wiki_dir, max_age_days=30)
        stale_30 = checker_30.check()
        assert len(stale_30) == 1


class TestContradictionChecker:
    """Tests for ContradictionChecker."""

    def test_returns_empty_list(self, wiki_dir):
        """ContradictionChecker returns empty list (NLP not implemented)."""
        page_a = wiki_dir / "page-a.md"
        page_a.write_text("# Page A\n\nX is true.\n")

        page_b = wiki_dir / "page-b.md"
        page_b.write_text("# Page B\n\nX is false.\n")

        checker = ContradictionChecker(wiki_dir)
        contradictions = checker.check()

        # TODO: When NLP implementation is added, this should detect contradictions
        assert len(contradictions) == 0

    def test_empty_wiki(self, wiki_dir):
        """Returns empty list for empty wiki."""
        checker = ContradictionChecker(wiki_dir)
        contradictions = checker.check()
        assert len(contradictions) == 0


class TestLintIntegration:
    """Tests for integration of lint checks with WikiLinter."""

    def test_run_all_checks_integrates_all_checkers(self, wiki_dir):
        """run_all_checks runs all checkers and returns combined results."""
        # Create a page with a broken link
        page = wiki_dir / "page.md"
        page.write_text("# Page\n\nSee [[Nonexistent]].\n")

        linter = WikiLinter(wiki_dir)
        results = linter.run_all_checks()

        assert "orphans" in results
        assert "broken_links" in results
        assert "duplicates" in results
        assert "stale_claims" in results
        assert "contradictions" in results

        # Should find the broken link
        assert len(results["broken_links"]) == 1

    def test_run_all_checks_with_stale_claims(self, wiki_dir):
        """run_all_checks detects stale claims."""
        old_date = datetime.now() - timedelta(days=400)
        date_str = old_date.strftime("%Y-%m-%d")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nLast updated: {date_str}\n")

        linter = WikiLinter(wiki_dir)
        results = linter.run_all_checks()

        assert len(results["stale_claims"]) == 1

    def test_run_all_checks_with_duplicates(self, wiki_dir):
        """run_all_checks detects duplicate content."""
        content = "# Page\n\nDuplicate content.\n"

        page_a = wiki_dir / "page-a.md"
        page_a.write_text(content)

        page_b = wiki_dir / "page-b.md"
        page_b.write_text(content)

        linter = WikiLinter(wiki_dir)
        results = linter.run_all_checks()

        assert len(results["duplicates"]) == 1
        assert results["duplicates"][0].match_type == "exact"

    def test_run_all_checks_accepts_parameters(self, wiki_dir):
        """run_all_checks passes parameters to checkers."""
        # Create a page with a date that is 200 days old
        old_date = datetime.now() - timedelta(days=200)
        date_str = old_date.strftime("%Y-%m-%d")

        page = wiki_dir / "page.md"
        page.write_text(f"# Page\n\nUpdated: {date_str}\n")

        linter = WikiLinter(wiki_dir)

        # With 365 day threshold, should not find stale claims
        results_365 = linter.run_all_checks(max_age_days=365)
        assert len(results_365["stale_claims"]) == 0

        # With 30 day threshold, should find stale claims
        results_30 = linter.run_all_checks(max_age_days=30)
        assert len(results_30["stale_claims"]) == 1
