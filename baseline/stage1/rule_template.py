"""Deterministic rule-template Stage-1 wrapper for baseline bundles.

Ablation: Rule template decomposition — use predefined rules and keyword /
regex matching to build task sets.  No LLM calls.  All logic that formerly
lived in ``pipeline.stage1_decomposition`` is re-implemented locally.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from pipeline.types import (
    AcceptanceCriterion,
    MBSEContext,
    OperatingRegime,
    TaskSet,
    VerificationTask,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage1_rule_template",
        "baseline_b1_rule_sequential",
    }
)

_RULE_SOURCE_PRIORITY = {
    "rules_component": 0,
    "rules_connection": 1,
    "rules_monolithic": 2,
}

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
            f"rule_template_stage1 only supports {', '.join(sorted(_ALLOWED_METHOD_NAMES))}; "
            f"got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("rule_template_stage1 requires config['workspace_root']")

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

    source = raw_taskset.generation_source or "rules_component"
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
            "generation_family": "rules",
            "grounding_valid": grounding_valid,
        },
    )


# ---------------------------------------------------------------------------
# Rule-based task set generation (replaces _generate_raw_tasksets_via_rules)
# ---------------------------------------------------------------------------


def _generate_rule_tasksets(requirement: str, mbse_context: MBSEContext) -> list[TaskSet]:
    """Generate task sets by matching components mentioned in the requirement."""
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)

    mentioned = [
        c
        for c in mbse_context.components
        if _component_is_mentioned(c.name, c.component_type, requirement)
    ]
    mentioned_names = {c.name for c in mentioned}
    component_type_map = {c.name: c.component_type for c in mbse_context.components}
    tasksets: list[TaskSet] = []

    # Strategy 1: per-component tasks for each mentioned component
    if mentioned:
        tasks: list[VerificationTask] = []
        for idx, comp in enumerate(mentioned):
            signals = [p.name for p in comp.ports if p.name]
            tasks.append(
                VerificationTask(
                    task_id=f"task_rule_comp_{idx}",
                    objective=f"Verify {comp.name}: {_global_objective(requirement)}",
                    required_signals=signals,
                    acceptance_criteria=list(criteria),
                    operating_regime=regime,
                    grounded_components=[comp.name],
                    grounded_component_types=[comp.component_type],
                    grounded_ports=signals,
                    diagnostics={
                        "generation_source": "rules_component",
                        "generation_family": "rules",
                    },
                )
            )
        tasksets.append(
            TaskSet(
                tasks=tasks,
                rationale="rule_template component-match task set",
                task_set_id="",
                generation_source="rules_component",
                grounding_status="raw",
                meta={
                    "generation_source": "rules_component",
                    "generation_family": "rules",
                },
            )
        )

    # Strategy 2: connection-based tasks involving mentioned components
    conn_tasks: list[VerificationTask] = []
    for idx, conn in enumerate(mbse_context.connections):
        if conn.source_component in mentioned_names or conn.target_component in mentioned_names:
            signals = [s for s in [conn.source_signal, conn.target_signal] if s]
            comps = [n for n in [conn.source_component, conn.target_component] if n]
            conn_tasks.append(
                VerificationTask(
                    task_id=f"task_rule_conn_{idx}",
                    objective=(
                        f"Verify connection {conn.source_component}->"
                        f"{conn.target_component}: {_global_objective(requirement)}"
                    ),
                    required_signals=signals,
                    acceptance_criteria=list(criteria),
                    operating_regime=regime,
                    grounded_components=comps,
                    grounded_component_types=[component_type_map.get(n, "") for n in comps],
                    grounded_ports=signals,
                    diagnostics={
                        "generation_source": "rules_connection",
                        "generation_family": "rules",
                    },
                )
            )
    if conn_tasks:
        tasksets.append(
            TaskSet(
                tasks=conn_tasks,
                rationale="rule_template connection-match task set",
                task_set_id="",
                generation_source="rules_connection",
                grounding_status="raw",
                meta={
                    "generation_source": "rules_connection",
                    "generation_family": "rules",
                },
            )
        )

    # Strategy 3: monolithic fallback covering all components
    if not tasksets and mbse_context.components:
        all_signals = [p.name for c in mbse_context.components for p in c.ports if p.name]
        tasksets.append(
            TaskSet(
                tasks=[
                    VerificationTask(
                        task_id="task_rule_mono_0",
                        objective=f"Verify system-wide: {_global_objective(requirement)}",
                        required_signals=all_signals[:10],
                        acceptance_criteria=list(criteria),
                        operating_regime=regime,
                        grounded_components=[c.name for c in mbse_context.components],
                        grounded_component_types=[c.component_type for c in mbse_context.components],
                        grounded_ports=all_signals[:10],
                        diagnostics={
                            "generation_source": "rules_monolithic",
                            "generation_family": "rules",
                        },
                    )
                ],
                rationale="rule_template monolithic fallback task set",
                task_set_id="",
                generation_source="rules_monolithic",
                grounding_status="raw",
                meta={
                    "generation_source": "rules_monolithic",
                    "generation_family": "rules",
                },
            )
        )

    return tasksets


def _rule_fallback_taskset(requirement: str, *, mbse_context: MBSEContext) -> TaskSet:
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)
    relevant_components = [
        c
        for c in mbse_context.components
        if _component_is_mentioned(c.name, c.component_type, requirement)
    ]
    component_pool = relevant_components or list(mbse_context.components[:1])
    grounded_components = [c.name for c in component_pool]
    grounded_component_types = [c.component_type for c in component_pool]
    grounded_ports = [
        p.name for c in component_pool for p in c.ports[:2] if p.name
    ]
    return TaskSet(
        tasks=[
            VerificationTask(
                task_id="task_rule_fallback_0",
                objective=f"Verify fallback rule coverage for {_global_objective(requirement)}",
                required_signals=list(grounded_ports),
                acceptance_criteria=list(criteria),
                operating_regime=regime,
                grounded_components=list(grounded_components),
                grounded_component_types=list(grounded_component_types),
                grounded_ports=list(grounded_ports),
                diagnostics={
                    "generation_source": "rules_fallback",
                    "generation_family": "rules",
                    "rule_template_fallback": True,
                },
            )
        ],
        rationale="rule_template fallback raw task set",
        task_set_id="",
        generation_source="rules_fallback",
        grounding_status="raw",
        score=0.0,
        p_value=0.0,
        conformal_info={},
        score_breakdown={},
        meta={
            "generation_source": "rules_fallback",
            "generation_family": "rules",
            "rule_template_fallback": True,
            "fallback_component_count": len(component_pool),
        },
    )


def _select_rule_template_candidate(candidates: Sequence[TaskSet]) -> TaskSet:
    return max(
        candidates,
        key=lambda candidate: (
            float(candidate.score),
            -int(_RULE_SOURCE_PRIORITY.get(candidate.generation_source or "", 99)),
            len(candidate.tasks),
            str(candidate.generation_source or ""),
            str(candidate.rationale or ""),
        ),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def rule_template_stage1(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> list[TaskSet]:
    """Produce exactly one evaluator-compatible rule-template Stage-1 candidate."""
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)

    req = (requirement or "").strip()
    raw_candidates = _generate_rule_tasksets(req, mbse_context)
    if not raw_candidates:
        raw_candidates = [_rule_fallback_taskset(req, mbse_context=mbse_context)]

    scored_candidates = [
        _ground_and_score(raw, req, mbse_context) for raw in raw_candidates
    ]
    selected = _select_rule_template_candidate(scored_candidates)
    selected = replace(
        selected,
        meta={
            **dict(selected.meta),
            "generation_source": selected.generation_source or "rules_component",
            "generation_family": "rules",
            "selection_mode": "single_best_rule_template",
            "candidate_count": len(scored_candidates),
        },
    )
    return [_strip_calibration_extras(selected)]


__all__ = ["rule_template_stage1"]
