"""Tests for code ingestion pipeline."""
import pytest
from pathlib import Path
import tempfile
from src.ingestion.code_ingestor import CodeIngestor, IngestionResult


def test_code_ingestor_processes_python_files():
    """CodeIngestor processes .py files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()

        # Create a test Python file
        test_file = code_dir / "example.py"
        test_file.write_text('''"""Example module."""
def hello():
    """Say hello."""
    print("Hello, World!")
''')

        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = ingestor.ingest()

        assert result.success is True
        assert result.output_path.exists()
        content = result.output_path.read_text()
        assert "example.py" in content


def test_code_ingestor_handles_empty_directory():
    """CodeIngestor handles empty code directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()

        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        result = ingestor.ingest()

        # Should succeed but produce no output file
        assert result.success is True
        assert result.output_path is None


def test_code_ingestor_extracts_docstring():
    """CodeIngestor extracts module docstrings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()

        test_file = code_dir / "module.py"
        test_file.write_text('''"""This is a module docstring."""
def func():
    pass
''')

        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        docstring = ingestor._extract_docstring(test_file)

        assert "module docstring" in docstring


def test_code_ingestor_generates_markdown():
    """CodeIngestor generates markdown for code files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir) / "code"
        code_dir.mkdir()

        test_file = code_dir / "test.py"
        test_file.write_text("print('hello')")

        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        ingestor = CodeIngestor(code_dir=code_dir, wiki_dir=wiki_dir, language="python")
        md = ingestor._generate_markdown(test_file)

        assert "# test.py" in md
        assert "```python" in md
        assert "print('hello')" in md


def test_ingestion_result_defaults():
    """IngestionResult has default values."""
    result = IngestionResult(success=True, output_path=Path("/test.md"))

    assert result.entity_pages == []
    assert result.concept_pages == []
    assert result.error is None
