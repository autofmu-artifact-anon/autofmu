"""Workspace management helpers for baseline bundles.

This module provides workspace bootstrap helpers, safe subdir creation,
and method workspace guard checks. It ensures all method writes stay
within their designated workspace boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from .naming import workspace_readme_content
from .paths import method_workspace


# Allowed subdirectories within a method workspace
ALLOWED_WORKSPACE_SUBDIRS: Final = frozenset({
    "prompts",
    "runs",
    "cache",
    "fixtures",
})


class WorkspaceError(Exception):
    """Raised when workspace operations violate policy."""
    pass


def _resolve_workspace_path(method_name: str, path: Path | str) -> tuple[Path, Path]:
    """Resolve a path against a method workspace and block escapes.

    Relative paths are resolved from the method workspace root rather than the
    current working directory. Absolute paths are allowed only when they remain
    within the same workspace after resolution.
    """
    workspace = method_workspace(method_name).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    target = candidate.resolve()

    try:
        target.relative_to(workspace)
    except ValueError:
        raise WorkspaceError(
            f"Resolved path {target} escapes workspace {workspace}. "
            f"Path was: {path!s}"
        ) from None

    return workspace, target


def bootstrap_method_workspace(method_name: str, *, create_subdirs: bool = False) -> Path:
    """Bootstrap a method workspace directory.

    Creates the workspace root if it doesn't exist. Optionally creates
    the standard subdirectories (prompts/, runs/, cache/, fixtures/).

    Args:
        method_name: Name of the method bundle.
        create_subdirs: If True, create the standard subdirectories.

    Returns:
        Path to the method workspace root.

    Raises:
        ValueError: If the method name is not recognized.
        WorkspaceError: If directory creation fails.
    """
    workspace = method_workspace(method_name)
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(
            f"Failed to create workspace root for method {method_name!r}: {workspace}"
        ) from exc

    if create_subdirs:
        for subdir in ALLOWED_WORKSPACE_SUBDIRS:
            (workspace / subdir).mkdir(exist_ok=True)

    return workspace


def ensure_workspace_subdir(method_name: str, subdir: str) -> Path:
    """Ensure a workspace subdirectory exists.

    Args:
        method_name: Name of the method bundle.
        subdir: Name of the subdirectory (must be one of prompts, runs, cache, fixtures).

    Returns:
        Path to the subdirectory.

    Raises:
        ValueError: If the method name or subdir name is not recognized.
    """
    if subdir not in ALLOWED_WORKSPACE_SUBDIRS:
        raise ValueError(
            f"Invalid workspace subdir {subdir!r}. "
            f"Allowed: {', '.join(sorted(ALLOWED_WORKSPACE_SUBDIRS))}"
        )

    workspace = method_workspace(method_name)
    subdir_path = workspace / subdir
    subdir_path.mkdir(parents=True, exist_ok=True)
    return subdir_path


def validate_path_in_workspace(method_name: str, path: Path | str) -> Path:
    """Validate that a path is within the method's workspace.

    Args:
        method_name: Name of the method bundle.
        path: Path to validate, resolved relative to the method workspace when
            provided as a relative path.

    Returns:
        The resolved absolute path.

    Raises:
        WorkspaceError: If the path is outside the method's workspace.
        ValueError: If the method name is not recognized.
    """
    _, target = _resolve_workspace_path(method_name, path)
    return target


def safe_write(method_name: str, relative_path: str, content: str | bytes) -> Path:
    """Safely write content to a file within the method's workspace.

    Validates that the target path is within the workspace and creates
    parent directories as needed.

    Args:
        method_name: Name of the method bundle.
        relative_path: Path relative to the method workspace root.
        content: Content to write (string or bytes).

    Returns:
        Path to the written file.

    Raises:
        WorkspaceError: If the resulting path would be outside the workspace.
        ValueError: If the method name is not recognized.
    """
    _, target = _resolve_workspace_path(method_name, relative_path)

    # Create parent directories
    target.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")

    return target


def safe_read(method_name: str, relative_path: str) -> str:
    """Safely read a file within the method's workspace.

    Args:
        method_name: Name of the method bundle.
        relative_path: Path relative to the method workspace root.

    Returns:
        File contents as string.

    Raises:
        WorkspaceError: If the path is outside the workspace.
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the method name is not recognized.
    """
    _, target = _resolve_workspace_path(method_name, relative_path)
    return target.read_text(encoding="utf-8")


def list_workspace_files(method_name: str, subdir: str | None = None) -> list[Path]:
    """List files in a method workspace or subdirectory.

    Args:
        method_name: Name of the method bundle.
        subdir: Optional subdirectory name (prompts, runs, cache, or fixtures).

    Returns:
        List of file paths within the workspace.

    Raises:
        ValueError: If the method name or subdir name is not recognized.
    """
    workspace = method_workspace(method_name)

    if subdir is not None:
        if subdir not in ALLOWED_WORKSPACE_SUBDIRS:
            raise ValueError(
                f"Invalid workspace subdir {subdir!r}. "
                f"Allowed: {', '.join(sorted(ALLOWED_WORKSPACE_SUBDIRS))}"
            )
        workspace = workspace / subdir

    if not workspace.exists():
        return []

    return [p for p in workspace.rglob("*") if p.is_file()]


def workspace_exists(method_name: str) -> bool:
    """Check if a method workspace exists.

    Args:
        method_name: Name of the method bundle.

    Returns:
        True if the workspace directory exists, False otherwise.
    """
    return method_workspace(method_name).exists()


def get_workspace_readme_content(method_name: str) -> str:
    """Generate README content for a method workspace.

    Args:
        method_name: Name of the method bundle.

    Returns:
        README.md content for the workspace.
    """
    return workspace_readme_content(method_name)
