"""Helpers for constructing evaluator MethodBundle instances."""

from __future__ import annotations

from collections.abc import Mapping
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import TYPE_CHECKING
from typing import Any

from .paths import repo_root
from .workspace import bootstrap_method_workspace

if TYPE_CHECKING:
    from evaluator.types import MethodBundle, Stage1Method, Stage2Method, Stage3Method


def _load_evaluator_types_module() -> ModuleType:
    """Load evaluator.types without depending on evaluator.__init__ side effects."""
    try:
        import evaluator.types as evaluator_types

        return evaluator_types
    except ModuleNotFoundError:
        module_name = "_baseline_evaluator_types"
        cached = sys.modules.get(module_name)
        if cached is not None:
            return cached
        module_path = repo_root() / "evaluator" / "types.py"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load evaluator types from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


def _normalize_mapping(name: str, value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copied mapping or an empty dict for None."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping or None, got {type(value).__name__}")
    return dict(value)


def _inject_method_context(
    config: Mapping[str, Any] | None,
    *,
    method_name: str,
    workspace_root: Path,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge default/runtime config and force method workspace context fields."""
    merged = dict(defaults)
    if config is not None:
        if not isinstance(config, Mapping):
            raise TypeError(f"config must be a mapping or None, got {type(config).__name__}")
        merged.update(dict(config))
    merged["method_name"] = method_name
    merged["workspace_root"] = str(workspace_root)
    return merged


def build_bundle(
    *,
    name: str,
    description: str,
    stage1: Stage1Method,
    stage2: Stage2Method,
    stage3: Stage3Method,
    stage1_config: Mapping[str, Any] | None = None,
    stage2_config: Mapping[str, Any] | None = None,
    stage3_config: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> MethodBundle:
    """Build a MethodBundle with normalized metadata and injected workspace context."""
    method_bundle_type = _load_evaluator_types_module().MethodBundle
    workspace_root = bootstrap_method_workspace(name).resolve()
    stage1_defaults = _normalize_mapping("stage1_config", stage1_config)
    stage2_defaults = _normalize_mapping("stage2_config", stage2_config)
    stage3_defaults = _normalize_mapping("stage3_config", stage3_config)
    bundle_metadata = _normalize_mapping("metadata", metadata)
    bundle_metadata["method_name"] = name
    bundle_metadata["workspace_root"] = str(workspace_root)

    def _stage1(requirement: str, *, mbse_context, config):
        return stage1(
            requirement,
            mbse_context=mbse_context,
            config=_inject_method_context(
                config,
                method_name=name,
                workspace_root=workspace_root,
                defaults=stage1_defaults,
            ),
        )

    def _stage2(task_candidates, *, mbse_context, fmu_library, config):
        return stage2(
            task_candidates,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
            config=_inject_method_context(
                config,
                method_name=name,
                workspace_root=workspace_root,
                defaults=stage2_defaults,
            ),
        )

    def _stage3(matching_result, *, mbse_context, config):
        return stage3(
            matching_result,
            mbse_context=mbse_context,
            config=_inject_method_context(
                config,
                method_name=name,
                workspace_root=workspace_root,
                defaults=stage3_defaults,
            ),
        )

    return method_bundle_type(
        name=name,
        description=description,
        stage1=_stage1,
        stage2=_stage2,
        stage3=_stage3,
        metadata=bundle_metadata,
    )


__all__ = ["build_bundle"]
