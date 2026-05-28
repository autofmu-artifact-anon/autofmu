"""Shared helpers for baseline bundle construction."""

from .bundle_factory import build_bundle
from .current_stages import current_stage1, current_stage2, current_stage3
from .naming import METHOD_SPECS, MethodSpec, method_spec, workspace_readme_content
from .paths import (
    METHOD_NAMES,
    artifacts_root,
    baseline_root,
    bundles_path,
    common_module_path,
    dataset_root,
    evaluator_run_dir,
    evaluator_runs_root,
    find_repo_root,
    method_workspace,
    pipeline_root,
    repo_root,
    stage_module_path,
    tests_path,
    workspaces_root,
)
from .workspace import (
    ALLOWED_WORKSPACE_SUBDIRS,
    WorkspaceError,
    bootstrap_method_workspace,
    ensure_workspace_subdir,
    get_workspace_readme_content,
    list_workspace_files,
    safe_read,
    safe_write,
    validate_path_in_workspace,
    workspace_exists,
)

__all__ = [
    # bundle helpers
    "build_bundle",
    "current_stage1",
    "current_stage2",
    "current_stage3",
    # naming
    "METHOD_SPECS",
    "MethodSpec",
    "method_spec",
    "workspace_readme_content",
    # paths
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
    # workspace
    "ALLOWED_WORKSPACE_SUBDIRS",
    "WorkspaceError",
    "bootstrap_method_workspace",
    "ensure_workspace_subdir",
    "get_workspace_readme_content",
    "list_workspace_files",
    "safe_read",
    "safe_write",
    "validate_path_in_workspace",
    "workspace_exists",
]
