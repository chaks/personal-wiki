"""Path traversal protection for route handlers."""
from pathlib import Path

from fastapi import HTTPException


def validate_path_segment(path: str) -> None:
    """Validate that a path does not contain traversal attempts.

    Rejects '..' components and absolute paths.

    Raises:
        HTTPException: 400 if path is unsafe
    """
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path must not contain '..'")
    if path.startswith("/"):
        raise HTTPException(status_code=400, detail="Path must not be absolute")


def resolve_within(base: Path, target: Path) -> Path:
    """Resolve target and verify it stays within base directory.

    Use after `pathlib.Path.resolve()` to guard against symlink escapes.

    Args:
        base: The allowed parent directory (must already be resolved)
        target: The resolved target path to check

    Returns:
        target (unchanged) if safe

    Raises:
        HTTPException: 400 if target escapes base
    """
    target_resolved = target.resolve()
    base_resolved = base.resolve()
    if not target_resolved.is_relative_to(base_resolved):
        raise HTTPException(status_code=400, detail="Invalid path: escapes allowed directory")
    return target_resolved
