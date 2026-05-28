"""Path helpers for baseline bundle construction.

This module provides repo-root-relative path helpers, per-method workspace
resolution, and official artifact path helpers. All paths are resolved relative
to the experiments repository root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from .naming import METHOD_NAMES


def find_repo_root() -> Path:
    """Find the experiments repository root.

    Walks up from the current working directory until it finds a directory
    containing 'baseline' and 'evaluator' subdirectories, which uniquely
    identifies the experiments repo root.

    Returns:
        Path to the repository root.

    Raises:
        RuntimeError: If the repo root cannot be located.
    """
    cwd = Path.cwd()
    for path in [cwd] + list(cwd.parents):
        if (path / "baseline").is_dir() and (path / "evaluator").is_dir():
            return path
    # Fallback: assume we're in the baseline/ directory or a subdirectory
    # and use a known path structure
    fallback = Path(__file__).resolve().parent.parent.parent
    if (fallback / "baseline").is_dir() and (fallback / "evaluator").is_dir():
        return fallback
    raise RuntimeError(
        f"Cannot locate experiments repository root from {cwd}. "
        "Expected to find 'baseline' and 'evaluator' directories."
    )


# Cached repo root
_repo_root: Path | None = None


def repo_root() -> Path:
    """Get the cached repository root path.

    Returns:
        Path to the experiments repository root.
    """
    global _repo_root
    if _repo_root is None:
        _repo_root = find_repo_root()
    return _repo_root


def baseline_root() -> Path:
    """Get the baseline directory path.

    Returns:
        Path to baseline/ under the repo root.
    """
    return repo_root() / "baseline"


def workspaces_root() -> Path:
    """Get the baseline workspaces directory path.

    Returns:
        Path to baseline/workspaces/ under the repo root.
    """
    return baseline_root() / "workspaces"


def artifacts_root() -> Path:
    """Get the baseline artifacts directory path.

    Returns:
        Path to baseline/artifacts/ under the repo root.
    """
    return baseline_root() / "artifacts"


def method_workspace(method_name: str) -> Path:
    """Get the workspace root path for a specific method.

    Args:
        method_name: Name of the method bundle (e.g., 'baseline_b1_rule_sequential').

    Returns:
        Path to the method's workspace directory under baseline/workspaces/.

    Raises:
        ValueError: If the method name is not recognized.
    """
    if method_name not in METHOD_NAMES:
        raise ValueError(
            f"Unknown method name {method_name!r}. "
            f"Valid names: {', '.join(sorted(METHOD_NAMES))}"
        )
    return workspaces_root() / method_name


def evaluator_runs_root() -> Path:
    """Get the official evaluator runs directory path.

    Official evaluation outputs must be written here.

    Returns:
        Path to evaluator/runs/ under the repo root.
    """
    return repo_root() / "evaluator" / "runs"


def evaluator_run_dir(bundle_name: str, run_id: str) -> Path:
    """Get the path for a specific evaluator run.

    Args:
        bundle_name: Name of the bundle being evaluated.
        run_id: Unique identifier for this run (typically timestamp-based).

    Returns:
        Path to the run directory under evaluator/runs/.
    """
    return evaluator_runs_root() / f"{bundle_name}_{run_id}"


def common_module_path() -> Path:
    """Get the path to the baseline/common module.

    Returns:
        Path to baseline/common/ under the repo root.
    """
    return baseline_root() / "common"


def stage_module_path(stage: int) -> Path:
    """Get the path to a stage module directory.

    Args:
        stage: Stage number (1, 2, or 3).

    Returns:
        Path to baseline/stage{N}/ under the repo root.

    Raises:
        ValueError: If stage is not 1, 2, or 3.
    """
    if stage not in (1, 2, 3):
        raise ValueError(f"Stage must be 1, 2, or 3, got {stage}")
    return baseline_root() / f"stage{stage}"


def bundles_path() -> Path:
    """Get the path to the bundles directory.

    Returns:
        Path to baseline/bundles/ under the repo root.
    """
    return baseline_root() / "bundles"


def tests_path() -> Path:
    """Get the path to the baseline tests directory.

    Returns:
        Path to baseline/tests/ under the repo root.
    """
    return baseline_root() / "tests"


def pipeline_root() -> Path:
    """Get the pipeline directory path.

    Returns:
        Path to pipeline/ under the repo root.
    """
    return repo_root() / "pipeline"


def dataset_root() -> Path:
    """Get the dataset directory path.

    Returns:
        Path to dataset/ under the repo root.
    """
    return repo_root() / "dataset"


__all__: Final = (
    "METHOD_NAMES",
    "artifacts_root",
    "baseline_root",
    "bundles_path",
    "common_module_path",
    "dataset_root",
    "evaluator_run_dir",
    "evaluator_runs_root",
    "find_repo_root",
    "method_workspace",
    "pipeline_root",
    "repo_root",
    "stage_module_path",
    "tests_path",
    "workspaces_root",
)
