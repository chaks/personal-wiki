# tests/test_ingest.py
"""Tests for the ingest.py CLI entry point.

These tests verify the config flag parsing for the markdown `full_pipeline`
flag via the load_sources() function from src.ingest.
"""
import pytest


class TestLoadSourcesRealFunction:
    """Tests that call load_sources from src.ingest."""

    def test_load_sources_with_full_pipeline_true(
        self, tmp_path
    ):
        """load_sources correctly loads a config with full_pipeline=True."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text(f"""sources:
  - type: markdown
    path: /test/notes.md
    full_pipeline: true
    tags: [test]
""")

        sources = load_sources(config_path)
        assert len(sources) == 1
        assert sources[0].get("type") == "markdown"
        assert sources[0].get("full_pipeline", False) is True
        assert sources[0].get("tags") == ["test"]

    def test_load_sources_with_full_pipeline_false(
        self, tmp_path
    ):
        """load_sources correctly loads a config with full_pipeline=False."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text(f"""sources:
  - type: markdown
    path: /test/notes.md
    full_pipeline: false
    tags: [test]
""")

        sources = load_sources(config_path)
        assert len(sources) == 1
        assert sources[0].get("full_pipeline", False) is False

    def test_load_sources_with_missing_full_pipeline(
        self, tmp_path
    ):
        """load_sources correctly handles missing full_pipeline flag (defaults to False)."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text(f"""sources:
  - type: markdown
    path: /test/notes.md
    tags: [test]
""")

        sources = load_sources(config_path)
        assert len(sources) == 1
        assert sources[0].get("full_pipeline", False) is False

    def test_load_sources_with_mixed_sources(
        self, tmp_path
    ):
        """load_sources correctly loads a config with mixed source types and flags."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text("""sources:
  - type: markdown
    path: /test/notes1.md
    full_pipeline: true
    tags: [pipeline]
  - type: markdown
    path: /test/notes2.md
    full_pipeline: false
    tags: [copy]
  - type: markdown
    path: /test/notes3.md
    tags: [default]
  - type: pdf
    path: /test/doc.pdf
    tags: [document]
""")

        sources = load_sources(config_path)
        assert len(sources) == 4

        assert sources[0].get("type") == "markdown"
        assert sources[0].get("full_pipeline", False) is True
        assert sources[0].get("tags") == ["pipeline"]

        assert sources[1].get("type") == "markdown"
        assert sources[1].get("full_pipeline", False) is False
        assert sources[1].get("tags") == ["copy"]

        assert sources[2].get("type") == "markdown"
        assert sources[2].get("full_pipeline", False) is False
        assert sources[2].get("tags") == ["default"]

        assert sources[3].get("type") == "pdf"
        assert sources[3].get("tags") == ["document"]

    def test_load_sources_empty_sources_list(self, tmp_path):
        """load_sources returns empty list when sources is empty."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text("sources: []\n")

        sources = load_sources(config_path)
        assert sources == []

    def test_load_sources_no_sources_key(self, tmp_path):
        """load_sources returns empty list when sources key is missing."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text("other_key: value\n")

        sources = load_sources(config_path)
        assert sources == []

    def test_load_sources_sources_key_is_none(self, tmp_path):
        """load_sources returns empty list when sources key is None."""
        from src.ingest import load_sources

        config_path = tmp_path / "config" / "sources.yaml"
        config_path.parent.mkdir()
        config_path.write_text("sources: null\n")

        sources = load_sources(config_path)
        assert sources == []
