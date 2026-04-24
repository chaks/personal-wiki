"""Source management API routes."""
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/sources", tags=["sources"])

# Path to sources.yaml config file
SOURCES_FILE = "config/sources.yaml"


class SourceInput(BaseModel):
    """Input model for adding a source."""
    type: str = Field(..., description="Source type (pdf, url, markdown, code)")
    path: Optional[str] = Field(None, description="Path for file-based sources")
    url: Optional[str] = Field(None, description="URL for web sources")
    language: Optional[str] = Field(None, description="Language for code sources")
    tags: List[str] = Field(default_factory=list, description="Tags for the source")


def _validate_path(path: str) -> None:
    """Validate that a path does not contain traversal attempts."""
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path must not contain '..'")
    if path.startswith("/"):
        raise HTTPException(status_code=400, detail="Path must not be absolute (must not start with '/')")


def _resolve_sources_file() -> str:
    """Resolve the sources.yaml file path, checking multiple locations."""
    import os
    from pathlib import Path

    # Try relative to current working directory first
    sources_path = Path(SOURCES_FILE)
    if sources_path.exists():
        return str(sources_path)

    # Try relative to project root (parent of src/)
    script_dir = Path(__file__).parent.parent.parent
    sources_path = script_dir / SOURCES_FILE
    if sources_path.exists():
        return str(sources_path)

    # Return the original path (may not exist yet)
    return SOURCES_FILE


@router.get("")
async def list_sources():
    """List all configured sources."""
    sources_file = _resolve_sources_file()

    try:
        with open(sources_file, "r") as f:
            config = yaml.safe_load(f) or {}
        sources = config.get("sources", [])
        return {"sources": sources}
    except FileNotFoundError:
        return {"sources": []}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Error reading sources file: {str(e)}")


@router.post("", status_code=201)
async def add_source(source: SourceInput):
    """Add a new source to the configuration."""
    sources_file = _resolve_sources_file()

    # Build the source dict from the input
    source_dict = {"type": source.type, "tags": source.tags}

    if source.path:
        _validate_path(source.path)
        source_dict["path"] = source.path
    if source.url:
        source_dict["url"] = source.url
    if source.language:
        source_dict["language"] = source.language

    try:
        # Read existing config
        with open(sources_file, "r") as f:
            config = yaml.safe_load(f) or {}

        # Initialize sources list if needed
        if "sources" not in config:
            config["sources"] = []

        # Add new source
        config["sources"].append(source_dict)

        # Write back to file
        with open(sources_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return {"message": "Source added successfully"}
    except FileNotFoundError:
        # Create new file with just this source
        config = {"sources": [source_dict]}
        with open(sources_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return {"message": "Source added successfully"}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Error reading sources file: {str(e)}")


@router.delete("/path/{path:path}")
async def delete_source(path: str):
    """Delete a source by its path."""
    _validate_path(path)
    sources_file = _resolve_sources_file()

    try:
        with open(sources_file, "r") as f:
            config = yaml.safe_load(f) or {}

        sources = config.get("sources", [])

        # Find and remove the source with matching path
        original_count = len(sources)
        sources = [s for s in sources if s.get("path") != path and s.get("url") != path]

        if len(sources) == original_count:
            raise HTTPException(status_code=404, detail=f"Source with path '{path}' not found")

        # Write updated config
        config["sources"] = sources
        with open(sources_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return {"message": f"Source '{path}' deleted successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sources file not found")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Error reading sources file: {str(e)}")
