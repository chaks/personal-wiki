import importlib
import pytest
import ast
from pathlib import Path


def test_pipeline_stages_module_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.pipeline.stages")


def test_adapter_imports_pipeline_stages():
    """SourceAdapter now imports pipeline stage interfaces."""
    adapters_file = Path("src/ingestion/adapters.py")
    source = adapters_file.read_text()
    tree = ast.parse(source)

    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            imported_names.extend(names)

    # Check that we import the new stage interfaces
    assert "ExtractStage" in imported_names, "Should import ExtractStage"
    assert "WriteStage" in imported_names, "Should import WriteStage"
    assert "ResolveStage" in imported_names, "Should import ResolveStage"
    assert "IndexStage" in imported_names, "Should import IndexStage"
