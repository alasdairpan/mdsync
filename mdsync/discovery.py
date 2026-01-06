"""File discovery utilities for mdsync.

This module handles discovering and organizing markdown files in the filesystem.
"""

from pathlib import Path
from typing import Any


def discover_markdown_files(path: Path) -> list[Path]:
    """Discover all markdown files in the given path.

    Args:
        path: Path to a file or directory

    Returns:
        List of markdown file paths, sorted alphabetically
    """
    if path.is_file():
        if path.suffix.lower() in [".md", ".markdown"]:
            return [path]
        else:
            return []

    # Directory - find all .md files recursively
    md_files = sorted(path.rglob("*.md"))
    markdown_files = sorted(path.rglob("*.markdown"))

    all_files = sorted(set(md_files + markdown_files))

    return all_files


def build_file_tree(files: list[Path], base_path: Path) -> dict[str, Any]:
    """Build a hierarchical structure of files and directories.

    Args:
        files: List of markdown file paths
        base_path: Base directory path

    Returns:
        Dictionary representing file tree structure with relative paths
    """
    tree_structure: dict[str, Any] = {}

    for file_path in files:
        try:
            relative_path = file_path.relative_to(base_path)
        except ValueError:
            # File is not relative to base_path (single file case)
            relative_path = file_path

        parts = relative_path.parts
        current = tree_structure

        # Navigate/create directory structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add file
        current[parts[-1]] = file_path

    return tree_structure
