"""Greedy semantic-structural Stage-2 matcher for baseline bundles.

Ablation: greedy hybrid — linear combination of semantic + structural costs
with single-pass conflict repair.
No priors, no transport optimization.
All logic is self-contained; the only pipeline import is ``pipeline.types``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from pipeline.types import FMU, MBSEContext, MatchingResult, OrchestrationGraph, PortBinding, PortMeta, TaskAssignment, TaskSet

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage2_greedy_hybrid",
        "baseline_b3_graph_aware",
    }
)

_SEMANTIC_WEIGHT = 0.5
_STRUCTURAL_WEIGHT = 0.5


# ---------------------------------------------------------------------------
# Local TF-IDF semantic cost (same approach as semantic_retrieval_only)
# ---------------------------------------------------------------------------

def _tokenize_text(text: str) -> list[str]:
    return [tok.lower() for tok in re.split(r"[^a-zA-Z0-9]+", text) if tok]


def _task_text(task) -> str:
    parts = [str(task.objective or "")]
    parts.extend(str(s) for s in task.required_signals)
    parts.extend(str(s) for s in task.grounded_components)
    parts.extend(str(s) for s in task.grounded_ports)
    for spec in task.signal_specs:
        parts.append(str(spec.signal_name or ""))
        parts.append(str(spec.component_hint or ""))
    for criterion in task.acceptance_criteria:
        parts.append(str(criterion.metric or ""))
    return " ".join(parts)


def _fmu_text(fmu: FMU) -> str:
    parts = [str(fmu.name or ""), str(fmu.description or "")]
    for port in fmu.ports:
        parts.append(str(port.name or ""))
        parts.append(str(port.description or ""))
    parts.extend(str(t) for t in fmu.tags)
    return " ".join(parts)


def _build_semantic_cost_matrix(
    task_set: TaskSet,
    fmu_library: Sequence[FMU],
) -> list[list[float]]:
    """Token-overlap TF-IDF similarity cost matrix.  Cost = 1 − cosine."""
    all_docs: list[list[str]] = []
    task_token_lists: list[list[str]] = []
    for task in task_set.tasks:
        tokens = _tokenize_text(_task_text(task))
        task_token_lists.append(tokens)
        all_docs.append(tokens)

    fmu_token_lists: list[list[str]] = []
    for fmu in fmu_library:
        tokens = _tokenize_text(_fmu_text(fmu))
        fmu_token_lists.append(tokens)
        all_docs.append(tokens)

    doc_count = len(all_docs) if all_docs else 1
    df: Counter[str] = Counter()
    for doc in all_docs:
        df.update(set(doc))
    idf = {term: math.log((doc_count + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}

    def _tfidf_vec(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: (count / total) * idf.get(term, 1.0) for term, count in tf.items()}

    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        shared = set(a) & set(b)
        if not shared:
            return 0.0
        dot = sum(a[k] * b[k] for k in shared)
        mag_a = math.sqrt(sum(v * v for v in a.values()))
        mag_b = math.sqrt(sum(v * v for v in b.values()))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    task_vecs = [_tfidf_vec(tokens) for tokens in task_token_lists]
    fmu_vecs = [_tfidf_vec(tokens) for tokens in fmu_token_lists]

    matrix: list[list[float]] = []
    for tvec in task_vecs:
        row = [max(0.0, 1.0 - _cosine(tvec, fvec)) for fvec in fmu_vecs]
        matrix.append(row)
    return matrix


# ---------------------------------------------------------------------------
# Inlined helpers (no cross-file imports from sibling stage2 modules)
# ---------------------------------------------------------------------------

def _input_ports(fmu: FMU) -> list[PortMeta]:
    return [p for p in fmu.ports if p.causality == "input"]


def _output_ports(fmu: FMU) -> list[PortMeta]:
    return [p for p in fmu.ports if p.causality == "output"]


def _tokenize(text: str) -> set[str]:
    return {tok.lower() for tok in re.split(r"[^a-zA-Z0-9]+", text) if tok}


def _fmu_aliases(fmu: FMU) -> list[str]:
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
    for a in raw:
        if a not in seen:
            seen.add(a)
            result.append(a)
    return result


def _ordered_assignment_uids(assignments: Sequence[TaskAssignment]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for a in assignments:
        uid = str(a.fmu_uid or "").strip()
        if uid and uid not in seen:
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


def _structural_pair_cost(task, fmu: FMU) -> tuple[float, float, list[str]]:
    """Hybrid-local structural cost (alias + signal overlap)."""
    aliases = _fmu_aliases(fmu)
    component_values = _normalized_values(list(task.grounded_components))
    type_values = _normalized_values(list(task.grounded_component_types))
    score = 0.0
    reasons: list[str] = []

    if component_values:
        exact = [v for v in component_values if any(v == a for a in aliases)]
        partial = [v for v in component_values if v not in exact and any(v in a or a in v for a in aliases)]
        if exact:
            score += 1.2
            reasons.append(f"comp_exact={len(exact)}")
        elif partial:
            score += 0.7
            reasons.append(f"comp_partial={len(partial)}")

    if type_values:
        exact = [v for v in type_values if any(v == a for a in aliases)]
        partial = [v for v in type_values if v not in exact and any(v in a or a in v for a in aliases)]
        if exact:
            score += 0.8
            reasons.append(f"type_exact={len(exact)}")
        elif partial:
            score += 0.45
            reasons.append(f"type_partial={len(partial)}")

    snames = _signal_names(task)
    port_names = [p.name for p in _output_ports(fmu)] + [p.name for p in _input_ports(fmu)]
    port_tokens = {tok for pn in port_names for tok in _tokenize(pn)}
    exact_hits = sum(1 for sn in snames if any(sn.lower() == pn.lower() for pn in port_names))
    partial_hits = sum(1 for sn in snames if not any(sn.lower() == pn.lower() for pn in port_names) and _tokenize(sn) & port_tokens)
    score += min(float(exact_hits) * 0.55 + float(partial_hits) * 0.25, 1.25)
    if exact_hits:
        reasons.append(f"sig_exact={exact_hits}")
    if partial_hits:
        reasons.append(f"sig_partial={partial_hits}")

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
    for task in task_set.tasks:
        row_c, row_s, row_r = [], [], []
        for fmu in fmu_library:
            c, s, r = _structural_pair_cost(task, fmu)
            row_c.append(c)
            row_s.append(s)
            row_r.append(r)
        costs.append(row_c)
        scores.append(row_s)
        reasons.append(row_r)
    return costs, scores, reasons


def _build_hybrid_port_graph(
    task_set: TaskSet,
    assignments: Sequence[TaskAssignment],
    fmu_by_uid: Mapping[str, FMU],
    semantic_costs: Sequence[Sequence[float]],
    fmu_library: Sequence[FMU],
) -> OrchestrationGraph:
    """Build port graph using combined semantic + name-match heuristic.

    Unlike the graph_match_only port graph (pure name-match), this version
    uses the semantic cost matrix to break ties when multiple output ports
    could connect to a given input.
    """
    selected_uids: list[str] = []
    seen_uids: set[str] = set()
    for a in assignments:
        if a.fmu_uid not in seen_uids:
            seen_uids.add(a.fmu_uid)
            selected_uids.append(a.fmu_uid)

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

    fmu_uid_to_lib_index = {fmu.uid: i for i, fmu in enumerate(fmu_library)}

    output_map: dict[str, list[tuple[str, PortMeta]]] = {}
    for uid in selected_uids:
        fmu = fmu_by_uid.get(uid)
        if not fmu:
            continue
        for p in _output_ports(fmu):
            output_map.setdefault(p.name.lower(), []).append((uid, p))

    bindings: list[PortBinding] = []
    for tgt_uid in selected_uids:
        fmu = fmu_by_uid.get(tgt_uid)
        if not fmu:
            continue
        for p in _input_ports(fmu):
            candidates = output_map.get(p.name.lower(), [])
            candidates = [(su, sp) for su, sp in candidates if su != tgt_uid]
            if not candidates:
                continue
            if len(candidates) == 1:
                src_uid, src_port = candidates[0]
            else:
                tgt_lib_idx = fmu_uid_to_lib_index.get(tgt_uid, 0)

                def _tie_key(pair):
                    su, sp = pair
                    si = fmu_uid_to_lib_index.get(su, 0)
                    sem = 1.0
                    for row in semantic_costs:
                        if tgt_lib_idx < len(row) and si < len(row):
                            sem = min(float(row[si]), sem)
                    return (sem, su, sp.name)

                src_uid, src_port = min(candidates, key=_tie_key)
            bindings.append(
                PortBinding(
                    source_fmu=src_uid,
                    source_signal=src_port.name,
                    target_fmu=tgt_uid,
                    target_signal=p.name,
                    score=1.0,
                    selected_by="hybrid_name_semantic",
                    reasons=["port_name_match", "semantic_tiebreak"],
                )
            )

    closure_ok = len(bindings) > 0 or len(selected_uids) <= 1
    return OrchestrationGraph(
        nodes=list(selected_uids),
        port_nodes=port_nodes,
        bindings=bindings,
        component_to_fmu=component_to_fmu,
        required_signal_chains=list(task_set.required_signal_chains),
        closure_ok=closure_ok,
        closure_failures=[],
        routing_failures=[],
        diagnostics={"builder": "hybrid_name_semantic_match"},
    )


# ---------------------------------------------------------------------------
# Simple conflict repair (replaces pipeline revision module)
# ---------------------------------------------------------------------------

def _select_conflict_pair(
    graph: OrchestrationGraph,
    assignments: Sequence[TaskAssignment],
) -> tuple[int, str] | None:
    """Pick the highest-cost assignment to mask out on conflict repair."""
    if not assignments:
        return None
    worst = max(assignments, key=lambda a: (a.cost, a.task_index))
    return (worst.task_index, worst.fmu_uid)


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
            "greedy_hybrid_stage2 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("greedy_hybrid_stage2 requires config['workspace_root']")

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
# Combined cost matrix & greedy assignment
# ---------------------------------------------------------------------------

def _combined_cost_matrix(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[list[list[str]]]]:
    semantic_costs = _build_semantic_cost_matrix(task_set, fmu_library)

    structural_costs, _structural_scores, reason_matrix = _build_structural_cost_matrix(
        task_set,
        mbse_context=mbse_context,
        fmu_library=fmu_library,
    )
    combined: list[list[float]] = []
    for row in range(len(task_set.tasks)):
        combined_row: list[float] = []
        for col in range(len(fmu_library)):
            structural = float(structural_costs[row][col])
            semantic = float(semantic_costs[row][col])
            if structural == float("inf"):
                combined_row.append(float("inf"))
            else:
                combined_row.append((_SEMANTIC_WEIGHT * semantic) + (_STRUCTURAL_WEIGHT * structural))
        combined.append(combined_row)
    return semantic_costs, structural_costs, combined, reason_matrix


def _build_assignments(
    task_set: TaskSet,
    *,
    fmu_library: Sequence[FMU],
    semantic_costs: Sequence[Sequence[float]],
    structural_costs: Sequence[Sequence[float]],
    combined_costs: Sequence[Sequence[float]],
    reason_matrix: Sequence[Sequence[Sequence[str]]],
    excluded_pair: tuple[int, str] | None = None,
) -> tuple[list[TaskAssignment], float] | None:
    assignments: list[TaskAssignment] = []
    total_cost = 0.0
    for row, task in enumerate(task_set.tasks):
        candidates = []
        for col, fmu in enumerate(fmu_library):
            if combined_costs[row][col] == float("inf"):
                continue
            if excluded_pair is not None and excluded_pair == (row, fmu.uid):
                continue
            candidates.append(col)
        if not candidates:
            return None
        best_col = min(
            candidates,
            key=lambda col: (
                float(combined_costs[row][col]),
                float(structural_costs[row][col]),
                float(semantic_costs[row][col]),
                fmu_library[col].uid,
            ),
        )
        chosen_fmu = fmu_library[best_col]
        combined_cost = float(combined_costs[row][best_col])
        structural_cost = float(structural_costs[row][best_col])
        semantic_cost = float(semantic_costs[row][best_col])
        total_cost += combined_cost
        assignments.append(
            TaskAssignment(
                task_id=task.task_id,
                task_index=row,
                fmu_uid=chosen_fmu.uid,
                score=max(0.0, 2.0 - combined_cost),
                cost=combined_cost,
                hard_ok=True,
                semantic_cost=semantic_cost,
                hard_mask_value=structural_cost,
                transport_mass=1.0,
                revision_index=0 if excluded_pair is None else 1,
                reasons=["greedy_hybrid", *list(reason_matrix[row][best_col])],
                grounded_components=list(task.grounded_components),
            )
        )
    return assignments, float(total_cost)


def _evaluate_assignments(
    task_set: TaskSet,
    assignments: Sequence[TaskAssignment],
    *,
    fmu_library: Sequence[FMU],
    semantic_costs: Sequence[Sequence[float]],
) -> tuple[bool, OrchestrationGraph, list[FMU]]:
    fmu_by_uid = {fmu.uid: fmu for fmu in fmu_library}
    graph = _build_hybrid_port_graph(task_set, assignments, fmu_by_uid, semantic_costs, fmu_library)
    selected_uids = _ordered_assignment_uids(assignments)
    selected_fmus = [fmu_by_uid[uid] for uid in selected_uids]
    return graph.closure_ok, graph, selected_fmus


# ---------------------------------------------------------------------------
# Per-taskset result builder
# ---------------------------------------------------------------------------

def _result_for_taskset(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> MatchingResult:
    semantic_costs, structural_costs, combined_costs, reason_matrix = _combined_cost_matrix(
        task_set,
        mbse_context=mbse_context,
        fmu_library=fmu_library,
    )
    first = _build_assignments(
        task_set,
        fmu_library=fmu_library,
        semantic_costs=semantic_costs,
        structural_costs=structural_costs,
        combined_costs=combined_costs,
        reason_matrix=reason_matrix,
    )
    if first is None:
        return MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[],
            graph=OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False),
            discrepancy_set=[],
            revision_trace=[{"revision": 0, "status": "failed", "reason": "no_finite_greedy_assignment"}],
            final_cost=float("inf"),
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=float("inf"),
            diagnostics={
                "status": "failed",
                "stage2_variant": "greedy_hybrid",
                "repair_used": False,
                "repair_attempted": False,
                "repair_succeeded": False,
                "failure_type": "no_feasible_assignment",
            },
        )

    assignments, total_cost = first
    closure_ok, graph, selected_fmus = _evaluate_assignments(
        task_set,
        assignments,
        fmu_library=fmu_library,
        semantic_costs=semantic_costs,
    )
    revision_trace: list[dict[str, Any]] = [
        {
            "revision": 0,
            "status": "ok" if closure_ok else "retry",
            "closure_ok": closure_ok,
        }
    ]
    if closure_ok:
        return MatchingResult(
            task_set=task_set,
            assignments=list(assignments),
            selected_fmus=selected_fmus,
            graph=graph,
            discrepancy_set=[],
            revision_trace=revision_trace,
            final_cost=float(total_cost),
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=float(total_cost),
            diagnostics={
                "status": "ok",
                "stage2_variant": "greedy_hybrid",
                "repair_used": False,
                "repair_attempted": False,
                "repair_succeeded": False,
                "failure_type": "",
            },
        )

    # Single-pass conflict repair: mask the worst assignment and retry once
    repair_pair = _select_conflict_pair(graph, assignments)
    if repair_pair is not None:
        repaired = _build_assignments(
            task_set,
            fmu_library=fmu_library,
            semantic_costs=semantic_costs,
            structural_costs=structural_costs,
            combined_costs=combined_costs,
            reason_matrix=reason_matrix,
            excluded_pair=repair_pair,
        )
        if repaired is not None:
            repaired_assignments, repaired_cost = repaired
            repaired_ok, repaired_graph, repaired_fmus = _evaluate_assignments(
                task_set,
                repaired_assignments,
                fmu_library=fmu_library,
                semantic_costs=semantic_costs,
            )
            revision_trace.append(
                {
                    "revision": 1,
                    "status": "ok" if repaired_ok else "failed",
                    "closure_ok": repaired_ok,
                    "excluded_pair": {"task_index": repair_pair[0], "fmu_uid": repair_pair[1]},
                }
            )
            if repaired_ok:
                return MatchingResult(
                    task_set=task_set,
                    assignments=list(repaired_assignments),
                    selected_fmus=repaired_fmus,
                    graph=repaired_graph,
                    discrepancy_set=[],
                    revision_trace=revision_trace,
                    final_cost=float(repaired_cost),
                    transport_plans=[],
                    mask_history=[],
                    taskset_results=[],
                    selected_task_set_cost=float(repaired_cost),
                    diagnostics={
                        "status": "ok",
                        "stage2_variant": "greedy_hybrid",
                        "repair_used": True,
                        "repair_attempted": True,
                        "repair_succeeded": True,
                        "failure_type": "",
                    },
                )
            return MatchingResult(
                task_set=task_set,
                assignments=list(repaired_assignments),
                selected_fmus=[],
                graph=repaired_graph,
                discrepancy_set=[],
                revision_trace=revision_trace,
                final_cost=float(repaired_cost),
                transport_plans=[],
                mask_history=[],
                taskset_results=[],
                selected_task_set_cost=float(repaired_cost),
                diagnostics={
                    "status": "failed",
                    "stage2_variant": "greedy_hybrid",
                    "repair_used": True,
                    "repair_attempted": True,
                    "repair_succeeded": False,
                    "failure_type": "port_graph_closure",
                },
            )

    return MatchingResult(
        task_set=task_set,
        assignments=list(assignments),
        selected_fmus=[],
        graph=graph,
        discrepancy_set=[],
        revision_trace=revision_trace,
        final_cost=float(total_cost),
        transport_plans=[],
        mask_history=[],
        taskset_results=[],
        selected_task_set_cost=float(total_cost),
        diagnostics={
            "status": "failed",
            "stage2_variant": "greedy_hybrid",
            "repair_used": False,
            "repair_attempted": False,
            "repair_succeeded": False,
            "failure_type": "port_graph_closure",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _selection_key(result: MatchingResult) -> tuple[int, float, float, str]:
    return (
        0 if result.diagnostics.get("status") == "ok" else 1,
        float(result.final_cost),
        float(len(result.selected_fmus)),
        str(result.task_set.task_set_id or ""),
    )


def greedy_hybrid_stage2(
    task_candidates: Sequence[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
    config: Mapping[str, Any] | None,
) -> MatchingResult:
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)
    if not task_candidates:
        raise ValueError("greedy_hybrid_stage2 received empty task_candidates")
    if not fmu_library:
        raise ValueError("greedy_hybrid_stage2 received empty fmu_library")

    results = [
        _result_for_taskset(
            task_set,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
        )
        for task_set in task_candidates
    ]
    taskset_summaries = [
        _build_taskset_result_summary(
            result=result,
            selected_fmu_uids=_ordered_assignment_uids(result.assignments),
        )
        for result in results
    ]
    best = min(results, key=_selection_key)
    return replace(
        best,
        taskset_results=taskset_summaries,
        diagnostics={
            **dict(best.diagnostics),
            "semantic_weight": _SEMANTIC_WEIGHT,
            "structural_weight": _STRUCTURAL_WEIGHT,
        },
    )


__all__ = ["greedy_hybrid_stage2"]
