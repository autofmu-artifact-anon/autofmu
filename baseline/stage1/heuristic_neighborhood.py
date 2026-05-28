"""Heuristic neighborhood Stage-1 wrapper for graph-aware baseline bundles.

Ablation: Heuristic neighborhood — expand MBSE neighborhoods based on token
anchor scores.  Uses a simple local tokenizer and token-overlap scoring
instead of ``pipeline.llm_guidance.tokenize``.  All decomposer logic is
re-implemented locally without any ``pipeline.*`` algorithmic imports.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from pipeline.types import (
    AcceptanceCriterion,
    MBSEComponent,
    MBSEContext,
    OperatingRegime,
    TaskSet,
    VerificationTask,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage1_heuristic_neighborhood",
        "baseline_b3_graph_aware",
    }
)

_CALIBRATION_META_KEYS = frozenset(
    {
        "accepted",
        "accepted_by",
        "calibrated_member",
        "calibration_artifact_path",
        "calibration_artifact_version",
        "calibration_confidence_levels",
        "calibration_score_summary",
        "calibration_size",
        "candidate_status",
        "confidence",
        "engineering_fallback",
        "fallback_retained",
        "forced_fallback",
        "nonconformity",
        "p_value_threshold",
        "selection_semantics",
    }
)

# ---------------------------------------------------------------------------
# Local tokenizer (replaces pipeline.llm_guidance.tokenize)
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Split on non-alphanumeric boundaries, lowercase, drop single chars."""
    return [t for t in re.findall(r"[a-z][a-z0-9]*", text.lower()) if len(t) > 1]


# ---------------------------------------------------------------------------
# Local re-implementations of helpers formerly from pipeline internals
# ---------------------------------------------------------------------------

_CRITERION_RE = re.compile(
    r"([\w\s/]+?)\s*(<=?|>=?|==?|!=|≤|≥|<|>)\s*"
    r"([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*(\w*)"
)
_TIME_RE = re.compile(
    r"(?:from|between|during|over|at|after)\s+t\s*=?\s*"
    r"([+-]?[\d.]+)\s*(?:s|sec|seconds?)?"
    r"(?:\s*(?:to|and|\.\.\.?|-)\s*([+-]?[\d.]+)\s*(?:s|sec|seconds?)?)?",
    re.IGNORECASE,
)
_WITHIN_RE = re.compile(
    r"within\s*\[?\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)\s*\]?",
    re.IGNORECASE,
)


def _component_is_mentioned(name: str, component_type: str, requirement: str) -> bool:
    lowered = requirement.lower()
    if name.lower() in lowered:
        return True
    if component_type and component_type.lower() in lowered:
        return True
    name_tokens = set(re.findall(r"[a-z][a-z0-9]*", name.lower()))
    if len(name_tokens) >= 2 and name_tokens <= set(re.findall(r"[a-z][a-z0-9]*", lowered)):
        return True
    return False


def _extract_acceptance_criteria(requirement: str) -> list[AcceptanceCriterion]:
    criteria: list[AcceptanceCriterion] = []
    for match in _CRITERION_RE.finditer(requirement):
        metric, operator, value_str, unit = match.groups()
        try:
            value: Any = float(value_str)
        except ValueError:
            value = value_str
        criteria.append(
            AcceptanceCriterion(
                metric=metric.strip(),
                operator=operator.strip(),
                value=value,
                unit=unit.strip(),
            )
        )
    for match in _WITHIN_RE.finditer(requirement):
        lo, hi = match.groups()
        criteria.append(
            AcceptanceCriterion(
                metric="range_constraint",
                operator="within",
                value=[float(lo), float(hi)],
            )
        )
    return criteria


def _extract_operating_regime(requirement: str) -> OperatingRegime | None:
    match = _TIME_RE.search(requirement)
    if match:
        start = float(match.group(1))
        end = float(match.group(2)) if match.group(2) else None
        return OperatingRegime(start_time=start, end_time=end)
    return None


def _global_objective(requirement: str) -> str:
    text = requirement.strip()
    return text[:197] + "..." if len(text) > 200 else text


# ---------------------------------------------------------------------------
# Config / workspace helpers
# ---------------------------------------------------------------------------


def _config_dict(config: Mapping[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise TypeError(f"config must be a mapping or None, got {type(config).__name__}")
    return dict(config)


def _validate_workspace_context(stage_config: Mapping[str, Any]) -> tuple[str, Path]:
    method_name = str(stage_config.get("method_name") or "").strip()
    if method_name not in _ALLOWED_METHOD_NAMES:
        raise ValueError(
            "heuristic_neighborhood_stage1 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("heuristic_neighborhood_stage1 requires config['workspace_root']")

    try:
        candidate = Path(workspace_value)
    except TypeError as exc:
        raise TypeError(
            f"config['workspace_root'] must be path-like, got {type(workspace_value).__name__}"
        ) from exc

    expected = method_workspace(method_name).resolve()
    try:
        resolved = validate_path_in_workspace(method_name, candidate)
    except WorkspaceError as exc:
        raise WorkspaceError(
            f"workspace_root for {method_name!r} must stay within {expected}, got {candidate}"
        ) from exc
    if resolved != expected:
        raise WorkspaceError(
            f"workspace_root for {method_name!r} must resolve to {expected}, got {resolved}"
        )
    return method_name, expected


def _strip_calibration_extras(taskset: TaskSet) -> TaskSet:
    meta = {
        key: value
        for key, value in dict(taskset.meta).items()
        if key not in _CALIBRATION_META_KEYS
    }
    return replace(taskset, p_value=0.0, conformal_info={}, meta=meta)


# ---------------------------------------------------------------------------
# Local grounding & scoring
# ---------------------------------------------------------------------------


def _ground_and_score(
    raw_taskset: TaskSet,
    requirement: str,
    mbse_context: MBSEContext,
) -> TaskSet:
    valid_components = {c.name for c in mbse_context.components}
    component_type_map = {c.name: c.component_type for c in mbse_context.components}
    port_set = {p.name for c in mbse_context.components for p in c.ports}

    grounded_tasks: list[VerificationTask] = []
    total_component_hits = 0
    total_port_hits = 0
    total_components = 0
    total_ports = 0

    for task in raw_taskset.tasks:
        gc = [n for n in task.grounded_components if n in valid_components]
        gct = [component_type_map.get(n, "") for n in gc]
        gp = [p for p in task.grounded_ports if p in port_set]
        total_component_hits += len(gc)
        total_port_hits += len(gp)
        total_components += max(len(task.grounded_components), 1)
        total_ports += max(len(task.grounded_ports), 1)
        grounded_tasks.append(
            replace(
                task,
                grounded_components=gc,
                grounded_component_types=gct,
                grounded_ports=gp,
            )
        )

    comp_ratio = total_component_hits / total_components if total_components else 0.0
    port_ratio = total_port_hits / total_ports if total_ports else 0.0
    has_criteria = any(t.acceptance_criteria for t in grounded_tasks)
    criteria_bonus = 0.15 if has_criteria else 0.0
    score = round(0.5 * comp_ratio + 0.35 * port_ratio + criteria_bonus, 4)
    grounding_valid = comp_ratio > 0.0

    source = raw_taskset.generation_source or "heuristic_neighborhood_raw"
    status = "grounded" if grounding_valid else "partially_grounded"

    return replace(
        raw_taskset,
        tasks=grounded_tasks,
        task_set_id="taskset_0",
        generation_source=source,
        grounding_status=status,
        score=score,
        score_breakdown={
            "component_ratio": comp_ratio,
            "port_ratio": port_ratio,
            "criteria_bonus": criteria_bonus,
            "final_score": score,
        },
        meta={
            **dict(raw_taskset.meta),
            "generation_family": "heuristic",
            "grounding_valid": grounding_valid,
        },
    )


# ---------------------------------------------------------------------------
# Neighborhood expansion logic
# ---------------------------------------------------------------------------


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _component_anchor_score(
    component: MBSEComponent,
    requirement: str,
    criterion_tokens: set[str],
) -> tuple[float, list[str]]:
    requirement_tokens = set(_tokenize(requirement))
    component_tokens = set(_tokenize(component.name)) | set(_tokenize(component.component_type))
    port_tokens = {t for port in component.ports for t in _tokenize(port.name)}

    score = 0.0
    reasons: list[str] = []

    if _component_is_mentioned(component.name, component.component_type, requirement):
        score += 2.0
        reasons.append("component_mentioned")
    shared_component_tokens = requirement_tokens & component_tokens
    if shared_component_tokens:
        score += 1.0 + (0.25 * len(shared_component_tokens))
        reasons.append(f"component_token_overlap={len(shared_component_tokens)}")
    shared_port_tokens = requirement_tokens & port_tokens
    if shared_port_tokens:
        score += 0.75 + (0.2 * len(shared_port_tokens))
        reasons.append(f"port_token_overlap={len(shared_port_tokens)}")
    shared_criteria_tokens = criterion_tokens & port_tokens
    if shared_criteria_tokens:
        score += 0.5 + (0.1 * len(shared_criteria_tokens))
        reasons.append(f"criteria_token_overlap={len(shared_criteria_tokens)}")

    return score, reasons


def _seed_component_names(
    requirement: str,
    mbse_context: MBSEContext,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    criterion_tokens = {
        t
        for criterion in _extract_acceptance_criteria(requirement)
        for t in _tokenize(criterion.metric)
    }
    scored: list[tuple[float, str, list[str]]] = []
    trace: dict[str, dict[str, Any]] = {}
    for component in mbse_context.components:
        s, reasons = _component_anchor_score(component, requirement, criterion_tokens)
        trace[component.name] = {"score": s, "reasons": reasons}
        if s > 0.0:
            scored.append((s, component.name, reasons))
    if not scored and mbse_context.components:
        first = mbse_context.components[0]
        trace[first.name]["reasons"] = list(trace[first.name]["reasons"]) + ["fallback_first_component"]
        return [first.name], trace
    if not scored:
        return [], trace
    scored.sort(key=lambda item: (-item[0], item[1]))
    top_score = scored[0][0]
    return [name for s, name, _ in scored if s == top_score], trace


def _expand_component_names(seed_names: list[str], mbse_context: MBSEContext) -> list[str]:
    expanded = list(seed_names)
    for seed in seed_names:
        expanded.extend(sorted(mbse_context.adjacency.get(seed, [])))
        for conn in mbse_context.connections:
            if conn.source_component == seed:
                expanded.append(conn.target_component)
            if conn.target_component == seed:
                expanded.append(conn.source_component)
    return _unique(expanded)


def _component_signals(
    component: MBSEComponent,
    requirement: str,
    mbse_context: MBSEContext,
) -> list[str]:
    requirement_tokens = set(_tokenize(requirement))
    mentioned = [
        port.name
        for port in component.ports
        if requirement_tokens & set(_tokenize(port.name))
    ]
    connection_signals = [
        signal
        for conn in mbse_context.connections
        for signal in (conn.source_signal, conn.target_signal)
        if conn.source_component == component.name or conn.target_component == component.name
    ]
    return _unique(mentioned or connection_signals or [p.name for p in component.ports])


# ---------------------------------------------------------------------------
# Task set construction
# ---------------------------------------------------------------------------


def _heuristic_fallback_taskset(requirement: str, *, mbse_context: MBSEContext) -> TaskSet:
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)
    component = mbse_context.components[0] if mbse_context.components else None
    required_signals = [
        p.name for p in (component.ports[:2] if component is not None else []) if p.name
    ]
    return TaskSet(
        tasks=[
            VerificationTask(
                task_id="task_heuristic_fallback_0",
                objective=f"Verify fallback neighborhood around {_global_objective(requirement)}",
                required_signals=list(required_signals),
                acceptance_criteria=list(criteria),
                operating_regime=regime,
                grounded_components=[component.name] if component is not None else [],
                grounded_component_types=[component.component_type] if component is not None else [],
                grounded_ports=list(required_signals),
                diagnostics={
                    "generation_source": "heuristic_neighborhood_fallback",
                    "generation_family": "heuristic",
                    "heuristic_neighborhood_fallback": True,
                    "seed_component": component is not None,
                },
            )
        ],
        rationale="heuristic neighborhood fallback raw task set",
        task_set_id="",
        generation_source="heuristic_neighborhood_fallback",
        grounding_status="raw",
        score=0.0,
        p_value=0.0,
        conformal_info={},
        score_breakdown={},
        meta={
            "generation_source": "heuristic_neighborhood_fallback",
            "generation_family": "heuristic",
            "heuristic_neighborhood_fallback": True,
            "seed_components": [component.name] if component is not None else [],
            "expanded_components": [component.name] if component is not None else [],
        },
    )


def _build_raw_taskset(requirement: str, *, mbse_context: MBSEContext) -> TaskSet:
    seed_names, anchor_trace = _seed_component_names(requirement, mbse_context)
    expanded_names = _expand_component_names(seed_names, mbse_context)
    if not expanded_names:
        return _heuristic_fallback_taskset(requirement, mbse_context=mbse_context)

    component_index = {c.name: c for c in mbse_context.components}
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)
    tasks: list[VerificationTask] = []

    for idx, component_name in enumerate(expanded_names):
        component = component_index.get(component_name)
        if component is None:
            continue
        required_signals = _component_signals(component, requirement, mbse_context)
        tasks.append(
            VerificationTask(
                task_id=f"task_neighborhood_{idx}",
                objective=(
                    f"Verify neighborhood behavior around {component.name}: "
                    f"{_global_objective(requirement)}"
                ),
                required_signals=required_signals,
                acceptance_criteria=list(criteria),
                operating_regime=regime,
                grounded_components=[component.name],
                grounded_component_types=[component.component_type],
                grounded_ports=required_signals,
                diagnostics={
                    "generation_source": "heuristic_neighborhood_raw",
                    "generation_family": "heuristic",
                    "seed_component": component.name in seed_names,
                    "anchor_score": float(
                        anchor_trace.get(component.name, {}).get("score", 0.0)
                    ),
                    "anchor_reasons": list(
                        anchor_trace.get(component.name, {}).get("reasons", [])
                    ),
                },
            )
        )

    if not tasks:
        return _heuristic_fallback_taskset(requirement, mbse_context=mbse_context)

    return TaskSet(
        tasks=tasks,
        rationale="heuristic neighborhood raw task set",
        generation_source="heuristic_neighborhood_raw",
        grounding_status="raw",
        meta={
            "generation_source": "heuristic_neighborhood_raw",
            "generation_family": "heuristic",
            "seed_components": list(seed_names),
            "expanded_components": list(expanded_names),
            "anchor_trace": anchor_trace,
        },
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def heuristic_neighborhood_stage1(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> list[TaskSet]:
    """Produce exactly one evaluator-compatible heuristic neighborhood candidate."""
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)

    req = (requirement or "").strip()
    raw_taskset = _build_raw_taskset(req, mbse_context=mbse_context)
    candidate = _ground_and_score(raw_taskset, req, mbse_context)
    candidate = replace(
        candidate,
        meta={
            **dict(candidate.meta),
            "generation_family": "heuristic",
            "selection_mode": "single_heuristic_neighborhood",
        },
    )
    return [_strip_calibration_extras(candidate)]


__all__ = ["heuristic_neighborhood_stage1"]
