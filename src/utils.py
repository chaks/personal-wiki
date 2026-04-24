"""Shared utilities for the Personal Wiki Chat application."""
import re


def slugify(name: str) -> str:
    """Convert name to safe filename.

    Args:
        name: The name to convert to a slug

    Returns:
        A slugified version of the name suitable for filenames
    """
    slug = name.lower().replace(" ", "-").replace("/", "-")
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    return slug
