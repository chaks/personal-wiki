"""Wiki browsing API routes."""
from fastapi import APIRouter, HTTPException, Request
from pathlib import Path

from src.lint import WikiLinter
from src.registry import list_entities as registry_list_entities
from src.registry import list_concepts as registry_list_concepts


router = APIRouter(prefix="/api/wiki", tags=["wiki"])


def _get_wiki_dir(request: Request) -> Path:
    """Get the wiki directory from app state."""
    return Path(request.app.state.wiki_dir)


def _validate_name(name: str) -> None:
    """Validate that a wiki page name does not contain traversal attempts.

    Rejects '..' components and absolute paths to prevent directory traversal.
    """
    if ".." in name:
        raise HTTPException(status_code=400, detail="Name must not contain '..'")
    if name.startswith("/"):
        raise HTTPException(status_code=400, detail="Name must not be absolute")


@router.get("/entities")
async def list_entities(request: Request):
    """List all entity pages in the wiki."""
    wiki_dir = _get_wiki_dir(request)
    entities = registry_list_entities(wiki_dir)
    return {"entities": entities}


@router.get("/concepts")
async def list_concepts(request: Request):
    """List all concept pages in the wiki."""
    wiki_dir = _get_wiki_dir(request)
    concepts = registry_list_concepts(wiki_dir)
    return {"concepts": concepts}


@router.get("/entities/{name:path}")
async def get_entity(name: str, request: Request):
    """Get a specific entity by name."""
    _validate_name(name)
    wiki_dir = _get_wiki_dir(request)
    entities_dir = wiki_dir / "entities"
    entity_path = entities_dir / f"{name}.md"

    # Resolve the real path and ensure it stays within entities_dir
    entity_path_resolved = entity_path.resolve()
    entities_dir_resolved = entities_dir.resolve()
    if not entity_path_resolved.is_relative_to(entities_dir_resolved):
        raise HTTPException(status_code=400, detail="Invalid entity name")

    if not entity_path.exists():
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found")

    return {"name": name, "content": entity_path.read_text()}


@router.get("/concepts/{name:path}")
async def get_concept(name: str, request: Request):
    """Get a specific concept by name."""
    _validate_name(name)
    wiki_dir = _get_wiki_dir(request)
    concepts_dir = wiki_dir / "concepts"
    concept_path = concepts_dir / f"{name}.md"

    # Resolve the real path and ensure it stays within concepts_dir
    concept_path_resolved = concept_path.resolve()
    concepts_dir_resolved = concepts_dir.resolve()
    if not concept_path_resolved.is_relative_to(concepts_dir_resolved):
        raise HTTPException(status_code=400, detail="Invalid concept name")

    if not concept_path.exists():
        raise HTTPException(status_code=404, detail=f"Concept '{name}' not found")

    return {"name": name, "content": concept_path.read_text()}


@router.get("/orphans")
async def list_orphans(request: Request):
    """List orphan pages (pages with no incoming links)."""
    wiki_dir = _get_wiki_dir(request)
    linter = WikiLinter(wiki_dir)
    orphans = linter.check_orphans()

    # Return relative paths as strings
    orphan_paths = [str(orph.relative_to(wiki_dir)) for orph in orphans]
    return {"orphans": orphan_paths}
