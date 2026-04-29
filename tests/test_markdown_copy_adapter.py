import pytest
from pathlib import Path
from src.ingestion.markdown_copy_adapter import MarkdownCopyAdapter
from src.ingestion_result import IngestionResult


class FakeIndexer:
    def __init__(self):
        self.indexed = []

    def index_page(self, page_path: Path) -> None:
        self.indexed.append(page_path)


def test_copies_markdown_to_wiki_dir(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    source_dir = tmp_path / "sources" / "notes"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "my-notes.md"
    source_file.write_text("# My Notes\n\nContent here")

    fake_indexer = FakeIndexer()
    adapter = MarkdownCopyAdapter(source_path=source_file, wiki_dir=wiki_dir, indexer=fake_indexer)
    result = adapter.run()

    assert result.success is True
    expected = wiki_dir / "notes" / "my-notes.md"
    assert expected.exists()
    assert expected.read_text() == "# My Notes\n\nContent here"


def test_indexer_is_invoked(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    source_dir = tmp_path / "sources" / "notes"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "n.md"
    source_file.write_text("x")

    fake_indexer = FakeIndexer()
    adapter = MarkdownCopyAdapter(
        source_path=source_file,
        wiki_dir=wiki_dir,
        indexer=fake_indexer,
    )
    result = adapter.run()

    assert result.success is True
    assert len(fake_indexer.indexed) == 1
    assert fake_indexer.indexed[0] == wiki_dir / "notes" / "n.md"


def test_returns_failure_for_missing_source(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    nonexistent = tmp_path / "no-such-file.md"

    adapter = MarkdownCopyAdapter(source_path=nonexistent, wiki_dir=wiki_dir)
    result = adapter.run()

    assert result.success is False
    assert result.error is not None
