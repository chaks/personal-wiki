import importlib
import pytest
import ast
from pathlib import Path


def test_pipeline_stages_module_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.pipeline.stages")


def test_adapter_has_no_stage_dependencies():
    """SourceAdapter subclasses no longer import PipelineStage or PipelineContext."""
    adapters_file = Path("src/ingestion/adapters.py")
    source = adapters_file.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            assert "PipelineStage" not in names, "Still imports PipelineStage"
            assert "PipelineContext" not in names, "Still imports PipelineContext"
            assert "stages" not in module, f"Still imports from stages module: {module}"
