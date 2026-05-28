"""Evaluator-compatible wrappers around the current pipeline stage entrypoints."""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.stage1_decomposition import decompose
from pipeline.stage2_matching import match
from pipeline.stage3_composition import compose


def _config_dict(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a shallow copy of config so callers are never mutated."""
    return {} if config is None else dict(config)


def _config_bool(config: Mapping[str, Any], key: str, default: bool) -> bool:
    """Coerce evaluator config values into booleans."""
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def current_stage1(requirement: str, *, mbse_context, config: Mapping[str, Any] | None):
    """Wrap the current stage-1 implementation using evaluator defaults."""
    stage_config = _config_dict(config)
    return decompose(
        requirement,
        mbse_context=mbse_context,
        confidence=float(stage_config.get("confidence", 0.9)),
        max_candidates=int(stage_config.get("max_candidates", 6)),
    )


def current_stage2(task_candidates, *, mbse_context, fmu_library, config: Mapping[str, Any] | None):
    """Wrap the current stage-2 implementation using evaluator defaults."""
    stage_config = _config_dict(config)
    return match(
        list(task_candidates),
        mbse_context=mbse_context,
        fmu_library=list(fmu_library),
        max_revisions=int(stage_config.get("max_revisions", 6)),
        top_m_per_task=int(stage_config.get("top_m_per_task", 5)),
        max_port_candidates=int(stage_config.get("max_port_candidates", 8)),
        enable_benchmark_single_fmu_fallback=_config_bool(
            stage_config,
            "enable_benchmark_single_fmu_fallback",
            True,
        ),
        enable_mbse_component_cover_fallback=_config_bool(
            stage_config,
            "enable_mbse_component_cover_fallback",
            True,
        ),
    )


def current_stage3(matching_result, *, mbse_context, config: Mapping[str, Any] | None):
    """Wrap the current stage-3 implementation using evaluator behavior."""
    stage_config = _config_dict(config)
    scenario_window = (
        stage_config.get("scenario_window")
        if isinstance(stage_config.get("scenario_window"), dict)
        else None
    )
    return compose(
        matching_result,
        mbse_context=mbse_context,
        scenario_window=scenario_window,
    )


__all__ = ["current_stage1", "current_stage2", "current_stage3"]
