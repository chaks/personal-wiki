import importlib
import pytest


def test_wiki_maintainer_module_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.wiki_maintainer")


def test_contradiction_checker_module_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.lint_checks.contradictions")
