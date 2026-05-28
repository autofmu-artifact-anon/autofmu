"""Deterministic structure-first Stage-2 matcher for baseline bundles.

Ablation: graph match only — no semantic guidance.
All logic is self-contained; the only pipeline import is ``pipeline.types``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from pipeline.types import (
    FMU,
    MBSEContext,
    MatchingResult,
    OrchestrationGraph,
    PortBinding,
    PortMeta,
    TaskAssignment,
    TaskSet,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage2_graph_match_only",
        "baseline_b1_rule_sequential",
    }
)


# ---------------------------------------------------------------------------
# Local helpers (replace pipeline.stage2_matching.* dependencies)
# ---------------------------------------------------------------------------

def _input_ports(fmu: FMU) -> list[PortMeta]:
    """Return ports with ``causality == "input"``."""
    return [p for p in fmu.ports if p.causality == "input"]


def _output_ports(fmu: FMU) -> list[PortMeta]:
    """Return ports with ``causality == "output"``."""
    return [p for p in fmu.ports if p.causality == "output"]


def _tokenize(text: str) -> set[str]:
    """Split *text* on non-alphanumeric boundaries into lowercase tokens."""
    return {tok.lower() for tok in re.split(r"[^a-zA-Z0-9]+", text) if tok}


def _fmu_aliases(fmu: FMU) -> list[str]:
    """Derive normalized alias strings from *fmu* identity fields."""
    raw: list[str] = []
    for val in (fmu.uid, fmu.name):
        compact = "".join(ch for ch in str(val or "").lower() if ch.isalnum())
        if compact:
            raw.append(compact)
    if fmu.meta:
        for key in ("alias", "aliases", "display_name", "model_name"):
            meta_val = fmu.meta.get(key)
            if meta_val is None:
                continue
            if isinstance(meta_val, str):
                compact = "".join(ch for ch in meta_val.lower() if ch.isalnum())
                if compact:
                    raw.append(compact)
            elif isinstance(meta_val, (list, tuple)):
                for item in meta_val:
                    compact = "".join(ch for ch in str(item).lower() if ch.isalnum())
                    if compact:
                        raw.append(compact)
    seen: set[str] = set()
    result: list[str] = []
    for alias in raw:
        if alias not in seen:
            seen.add(alias)
            result.append(alias)
    return result


def _build_simple_port_graph(
    task_set: TaskSet,
    assignments: Sequence[TaskAssignment],
    fmu_by_uid: Mapping[str, FMU],
) -> OrchestrationGraph:
    """Build a simplified port graph by matching output→input port names."""
    selected_uids: list[str] = []
    seen_uids: set[str] = set()
    for a in assignments:
        if a.fmu_uid not in seen_uids:
            seen_uids.add(a.fmu_uid)
            selected_uids.append(a.fmu_uid)

    nodes = list(selected_uids)
    port_nodes: list[str] = []
    for uid in selected_uids:
        fmu = fmu_by_uid.get(uid)
        if fmu:
            for p in fmu.ports:
                qname = f"{uid}.{p.name}"
                if qname not in port_nodes:
                    port_nodes.append(qname)

    component_to_fmu: dict[str, str] = {}
    for a in assignments:
        for comp in a.grounded_components:
            if comp and comp not in component_to_fmu:
                component_to_fmu[comp] = a.fmu_uid

    output_map: dict[str, list[tuple[str, PortMeta]]] = {}
    for uid in selected_uids:
        fmu = fmu_by_uid.get(uid)
        if not fmu:
            continue
        for p in _output_ports(fmu):
            output_map.setdefault(p.name.lower(), []).append((uid, p))

    bindings: list[PortBinding] = []
    for uid in selected_uids:
        fmu = fmu_by_uid.get(uid)
        if not fmu:
            continue
        for p in _input_ports(fmu):
            candidates = output_map.get(p.name.lower(), [])
            for src_uid, src_port in candidates:
                if src_uid == uid:
                    continue
                bindings.append(
                    PortBinding(
                        source_fmu=src_uid,
                        source_signal=src_port.name,
                        target_fmu=uid,
                        target_signal=p.name,
                        score=1.0,
                        selected_by="name_match",
                        reasons=["port_name_match"],
                    )
                )

    closure_ok = len(bindings) > 0 or len(selected_uids) <= 1
    return OrchestrationGraph(
        nodes=nodes,
        port_nodes=port_nodes,
        bindings=bindings,
        component_to_fmu=component_to_fmu,
        required_signal_chains=list(task_set.required_signal_chains),
        closure_ok=closure_ok,
        closure_failures=[],
        routing_failures=[],
        diagnostics={"builder": "simplified_name_match"},
    )


# ---------------------------------------------------------------------------
# Config & workspace validation
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
            "graph_match_only_stage2 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("graph_match_only_stage2 requires config['workspace_root']")

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


# ---------------------------------------------------------------------------
# Structural scoring
# ---------------------------------------------------------------------------

def _normalized_values(values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        compact = "".join(ch for ch in str(value or "").lower() if ch.isalnum())
        if compact and compact not in seen:
            normalized.append(compact)
            seen.add(compact)
    return normalized


def _signal_names(task) -> list[str]:
    names: list[str] = []
    for value in list(task.required_signals) + list(task.grounded_ports):
        text = str(value or "").strip()
        if text:
            names.append(text)
    for criterion in task.acceptance_criteria:
        metric = str(criterion.metric or "").strip()
        if metric:
            names.append(metric)
    return names


def _signal_overlap_score(task, fmu: FMU) -> tuple[float, list[str]]:
    snames = _signal_names(task)
    port_names = [port.name for port in _output_ports(fmu)] + [port.name for port in _input_ports(fmu)]
    port_tokens = {token for port_name in port_names for token in _tokenize(port_name)}
    exact_hits = 0
    partial_hits = 0
    reasons: list[str] = []
    for signal_name in snames:
        if any(signal_name.lower() == pn.lower() for pn in port_names):
            exact_hits += 1
            continue
        signal_tokens = _tokenize(signal_name)
        if signal_tokens and signal_tokens & port_tokens:
            partial_hits += 1
    if exact_hits:
        reasons.append(f"exact_signal_hits={exact_hits}")
    if partial_hits:
        reasons.append(f"token_signal_hits={partial_hits}")
    score = min(float(exact_hits) * 0.55 + float(partial_hits) * 0.25, 1.25)
    return score, reasons


def _alias_match_score(task, fmu: FMU) -> tuple[float, list[str]]:
    aliases = _fmu_aliases(fmu)
    component_values = _normalized_values(list(task.grounded_components))
    type_values = _normalized_values(list(task.grounded_component_types))
    score = 0.0
    reasons: list[str] = []

    if component_values:
        exact_components = [
            value
            for value in component_values
            if any(value == alias for alias in aliases)
        ]
        partial_components = [
            value
            for value in component_values
            if value not in exact_components and any(value in alias or alias in value for alias in aliases)
        ]
        if exact_components:
            score += 1.2
            reasons.append(f"component_exact={','.join(sorted(exact_components))}")
        elif partial_components:
            score += 0.7
            reasons.append(f"component_partial={','.join(sorted(partial_components))}")

    if type_values:
        exact_types = [
            value
            for value in type_values
            if any(value == alias for alias in aliases)
        ]
        partial_types = [
            value
            for value in type_values
            if value not in exact_types and any(value in alias or alias in value for alias in aliases)
        ]
        if exact_types:
            score += 0.8
            reasons.append(f"type_exact={','.join(sorted(exact_types))}")
        elif partial_types:
            score += 0.45
            reasons.append(f"type_partial={','.join(sorted(partial_types))}")

    return score, reasons


def _structural_pair_cost(task, fmu: FMU) -> tuple[float, float, list[str]]:
    """Structural cost from port/signal overlap and alias matching only."""
    alias_score, alias_reasons = _alias_match_score(task, fmu)
    signal_score, signal_reasons = _signal_overlap_score(task, fmu)
    score = alias_score + signal_score
    reasons = alias_reasons + signal_reasons
    cost = max(0.0, 4.5 - score)
    return cost, score, reasons or ["structural_only"]


def _build_structural_cost_matrix(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> tuple[list[list[float]], list[list[float]], list[list[list[str]]]]:
    costs: list[list[float]] = []
    scores: list[list[float]] = []
    reasons: list[list[list[str]]] = []
    for _row, task in enumerate(task_set.tasks):
        row_costs: list[float] = []
        row_scores: list[float] = []
        row_reasons: list[list[str]] = []
        for _col, fmu in enumerate(fmu_library):
            cost, score, pair_reasons = _structural_pair_cost(task, fmu)
            row_costs.append(cost)
            row_scores.append(score)
            row_reasons.append(pair_reasons)
        costs.append(row_costs)
        scores.append(row_scores)
        reasons.append(row_reasons)
    return costs, scores, reasons


# ---------------------------------------------------------------------------
# Greedy assignment
# ---------------------------------------------------------------------------

def _select_assignments(
    task_set: TaskSet,
    *,
    fmu_library: Sequence[FMU],
    structural_costs: Sequence[Sequence[float]],
    structural_scores: Sequence[Sequence[float]],
    reason_matrix: Sequence[Sequence[Sequence[str]]],
) -> tuple[list[TaskAssignment], float] | None:
    assignments: list[TaskAssignment] = []
    total_cost = 0.0
    for row, task in enumerate(task_set.tasks):
        finite_cols = [
            col
            for col, cost in enumerate(structural_costs[row])
            if cost != float("inf")
        ]
        if not finite_cols:
            return None
        best_col = min(
            finite_cols,
            key=lambda col: (
                float(structural_costs[row][col]),
                -float(structural_scores[row][col]),
                fmu_library[col].uid,
            ),
        )
        best_fmu = fmu_library[best_col]
        cost = float(structural_costs[row][best_col])
        total_cost += cost
        assignments.append(
            TaskAssignment(
                task_id=task.task_id,
                task_index=row,
                fmu_uid=best_fmu.uid,
                score=float(structural_scores[row][best_col]),
                cost=cost,
                hard_ok=True,
                semantic_cost=cost,
                hard_mask_value=0.0,
                transport_mass=1.0,
                revision_index=0,
                reasons=["graph_match_only", *list(reason_matrix[row][best_col])],
                grounded_components=list(task.grounded_components),
            )
        )
    return assignments, float(total_cost)


def _graph_match_result_for_taskset(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> MatchingResult:
    fmu_by_uid = {fmu.uid: fmu for fmu in fmu_library}
    structural_costs, structural_scores, reason_matrix = _build_structural_cost_matrix(
        task_set,
        mbse_context=mbse_context,
        fmu_library=fmu_library,
    )
    selected = _select_assignments(
        task_set,
        fmu_library=fmu_library,
        structural_costs=structural_costs,
        structural_scores=structural_scores,
        reason_matrix=reason_matrix,
    )
    if selected is None:
        return MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[],
            graph=OrchestrationGraph(
                nodes=[],
                bindings=[],
                component_to_fmu={},
                required_signal_chains=list(task_set.required_signal_chains),
                closure_ok=False,
                diagnostics={"status": "failed_assignment", "stage2_variant": "graph_match_only"},
            ),
            discrepancy_set=[],
            revision_trace=[{"revision": 0, "status": "failed", "reason": "no_finite_structural_assignment"}],
            final_cost=float("inf"),
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=float("inf"),
            diagnostics={
                "status": "failed",
                "stage2_variant": "graph_match_only",
                "structural_reasoning": True,
                "semantic_retrieval": False,
                "fallback_used": False,
                "failure_type": "no_feasible_assignment",
            },
        )

    assignments, total_cost = selected
    selected_fmu_uids = _ordered_assignment_uids(assignments)
    selected_fmus = [fmu_by_uid[uid] for uid in selected_fmu_uids]
    graph = _build_simple_port_graph(task_set, assignments, fmu_by_uid)
    closure_ok = graph.closure_ok
    return MatchingResult(
        task_set=task_set,
        assignments=assignments,
        selected_fmus=selected_fmus if closure_ok else [],
        graph=graph,
        discrepancy_set=[],
        revision_trace=[
            {
                "revision": 0,
                "status": "ok" if closure_ok else "failed",
                "closure_ok": closure_ok,
            }
        ],
        final_cost=float(total_cost),
        transport_plans=[],
        mask_history=[],
        taskset_results=[],
        selected_task_set_cost=float(total_cost),
        diagnostics={
            "status": "ok" if closure_ok else "failed",
            "stage2_variant": "graph_match_only",
            "structural_reasoning": True,
            "semantic_retrieval": False,
            "binding_count": len(graph.bindings),
            "fallback_used": False,
            "failure_type": "" if closure_ok else "port_graph_closure",
        },
    )


# ---------------------------------------------------------------------------
# Shared utilities (used by sibling stage2 modules)
# ---------------------------------------------------------------------------

def _selection_key(result: MatchingResult) -> tuple[int, float, float, str]:
    return (
        0 if result.diagnostics.get("status") == "ok" else 1,
        float(result.final_cost),
        -float(len(result.graph.bindings)),
        str(result.task_set.task_set_id or ""),
    )


def _ordered_assignment_uids(assignments: Sequence[TaskAssignment]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for assignment in assignments:
        uid = str(assignment.fmu_uid or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        ordered.append(uid)
    return ordered


def _build_taskset_result_summary(
    *,
    result: MatchingResult,
    selected_fmu_uids: Sequence[str] | None = None,
) -> dict[str, Any]:
    uids = list(selected_fmu_uids or _ordered_assignment_uids(result.assignments))
    return {
        "task_set_id": result.task_set.task_set_id,
        "status": str(result.diagnostics.get("status") or ""),
        "selected_task_set_cost": float(result.selected_task_set_cost),
        "final_cost": float(result.final_cost),
        "selected_fmus": list(uids),
        "discrepancy_count": len(result.discrepancy_set),
        "failure_type": str(result.diagnostics.get("failure_type") or ""),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def graph_match_only_stage2(
    task_candidates: Sequence[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
    config: Mapping[str, Any] | None,
) -> MatchingResult:
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)
    if not task_candidates:
        raise ValueError("graph_match_only_stage2 received empty task_candidates")
    if not fmu_library:
        raise ValueError("graph_match_only_stage2 received empty fmu_library")

    results = [
        _graph_match_result_for_taskset(
            task_set,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
        )
        for task_set in task_candidates
    ]
    taskset_summaries = [_build_taskset_result_summary(result=result) for result in results]
    best = min(results, key=_selection_key)
    return replace(best, taskset_results=taskset_summaries)


__all__ = ["graph_match_only_stage2"]
