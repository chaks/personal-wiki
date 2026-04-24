"""Wiki browsing API routes."""
from fastapi import APIRouter, HTTPException, Request
from pathlib import Path

from src.lint import WikiLinter


router = APIRouter(prefix="/api/wiki", tags=["wiki"])


def _get_wiki_dir(request: Request) -> Path:
    """Get the wiki directory from app state."""
    return Path(request.app.state.wiki_dir)


@router.get("/entities")
async def list_entities(request: Request):
    """List all entity pages in the wiki."""
    wiki_dir = _get_wiki_dir(request)
    entities_dir = wiki_dir / "entities"

    entities = []
    if entities_dir.exists():
        for entity_file in entities_dir.glob("*.md"):
            entities.append(entity_file.stem)

    return {"entities": sorted(entities)}


@router.get("/concepts")
async def list_concepts(request: Request):
    """List all concept pages in the wiki."""
    wiki_dir = _get_wiki_dir(request)
    concepts_dir = wiki_dir / "concepts"

    concepts = []
    if concepts_dir.exists():
        for concept_file in concepts_dir.glob("*.md"):
            concepts.append(concept_file.stem)

    return {"concepts": sorted(concepts)}


@router.get("/entities/{name:path}")
async def get_entity(name: str, request: Request):
    """Get a specific entity by name."""
    wiki_dir = _get_wiki_dir(request)
    entities_dir = wiki_dir / "entities"
    entity_path = entities_dir / f"{name}.md"

    if not entity_path.exists():
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found")

    return {"name": name, "content": entity_path.read_text()}


@router.get("/concepts/{name:path}")
async def get_concept(name: str, request: Request):
    """Get a specific concept by name."""
    wiki_dir = _get_wiki_dir(request)
    concepts_dir = wiki_dir / "concepts"
    concept_path = concepts_dir / f"{name}.md"

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
