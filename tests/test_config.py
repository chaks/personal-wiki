"""Tests for centralized configuration."""
import pytest
from pathlib import Path
import tempfile
from src.config import AppSettings


def test_app_settings_loads_from_yaml():
    """AppSettings loads from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        config_file.write_text("""
services:
  llm:
    model: "test-model"
  vector_store:
    url: "http://test:6333"
wiki:
  categories:
    - test_category
""")

        settings = AppSettings.from_yaml(config_file)

        assert settings.llm_model == "test-model"
        assert settings.qdrant_url == "http://test:6333"
        assert "test_category" in settings.wiki_categories


def test_app_settings_uses_defaults():
    """AppSettings uses defaults when config is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "missing.yaml"

        settings = AppSettings.from_yaml(config_file)

        # Should use defaults
        assert settings.llm_model == "gemma4:e2b"
        assert settings.qdrant_url == "http://localhost:6333"


def test_app_settings_to_dict():
    """AppSettings can convert to dictionary."""
    settings = AppSettings()
    config_dict = settings.to_dict()

    assert "services" in config_dict
    assert "wiki" in config_dict
    assert "ingestion" in config_dict
    assert config_dict["services"]["llm"]["model"] == "gemma4:e2b"


def test_app_settings_empty_config_uses_defaults():
    """AppSettings uses defaults when config file is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "empty.yaml"
        config_file.write_text("")

        settings = AppSettings.from_yaml(config_file)

        assert settings.llm_model == "gemma4:e2b"
        assert settings.qdrant_url == "http://localhost:6333"
