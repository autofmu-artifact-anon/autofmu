"""Minimal semantic-only Stage-2 wrapper for baseline evaluator bundles.

Ablation: semantic retrieval only — no structural constraints.
Uses TF-IDF token-overlap similarity instead of the pipeline's CodeBERT
embeddings.  No priors, no fallback mechanisms.
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
        "ablation_stage2_semantic_retrieval_only",
        "baseline_b2_llm_retrieval_rule",
    }
)


# ---------------------------------------------------------------------------
# Local TF-IDF semantic similarity (replaces pipeline's CodeBERT cost matrix)
# ---------------------------------------------------------------------------

def _tokenize_text(text: str) -> list[str]:
    """Split *text* on non-alphanumeric boundaries into lowercase tokens."""
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


def _build_semantic_port_graph(
    task_set: TaskSet,
    assignments: Sequence[TaskAssignment],
    fmu_by_uid: Mapping[str, FMU],
) -> OrchestrationGraph:
    """Semantic-only port graph: nodes listed, but NO structural port bindings.

    This ablation intentionally omits topology reasoning.  Closure is granted
    when there is exactly one FMU (single-node trivially closed) so that
    simple benchmark cases can proceed to execution.  Multi-FMU cases will
    report ``closure_ok=False`` because we have no structural basis for
    wiring ports.
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

    closure_ok = len(selected_uids) <= 1
    return OrchestrationGraph(
        nodes=list(selected_uids),
        port_nodes=port_nodes,
        bindings=[],
        component_to_fmu=component_to_fmu,
        required_signal_chains=list(task_set.required_signal_chains),
        closure_ok=closure_ok,
        closure_failures=[] if closure_ok else ["no_structural_reasoning"],
        routing_failures=[],
        diagnostics={"builder": "semantic_only_no_bindings"},
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
            "semantic_retrieval_only_stage2 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("semantic_retrieval_only_stage2 requires config['workspace_root']")

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
# Greedy assignment (no priors, no fallback)
# ---------------------------------------------------------------------------

def _select_semantic_assignments(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> tuple[list[TaskAssignment], float]:
    semantic_matrix = _build_semantic_cost_matrix(task_set, fmu_library)

    assignments: list[TaskAssignment] = []
    total_cost = 0.0
    for row, task in enumerate(task_set.tasks):
        if row >= len(semantic_matrix) or not semantic_matrix[row]:
            raise ValueError(f"semantic matrix row missing for task index {row}")
        best_col = min(
            range(len(semantic_matrix[row])),
            key=lambda col: (float(semantic_matrix[row][col]), fmu_library[col].uid),
        )
        semantic_cost = float(semantic_matrix[row][best_col])
        best_fmu = fmu_library[best_col]
        total_cost += semantic_cost
        assignments.append(
            TaskAssignment(
                task_id=task.task_id,
                task_index=row,
                fmu_uid=best_fmu.uid,
                score=float(1.0 - semantic_cost),
                cost=semantic_cost,
                hard_ok=True,
                semantic_cost=semantic_cost,
                hard_mask_value=0.0,
                transport_mass=1.0,
                revision_index=0,
                reasons=["semantic_retrieval_only"],
                grounded_components=list(task.grounded_components),
            )
        )
    return assignments, float(total_cost)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def semantic_retrieval_only_stage2(
    task_candidates: Sequence[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
    config: Mapping[str, Any] | None,
) -> MatchingResult:
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)
    if not task_candidates:
        raise ValueError("semantic_retrieval_only_stage2 received empty task_candidates")
    if not fmu_library:
        raise ValueError("semantic_retrieval_only_stage2 received empty fmu_library")

    fmu_by_uid = {fmu.uid: fmu for fmu in fmu_library}
    results: list[MatchingResult] = []
    taskset_summaries: list[dict[str, Any]] = []
    for task_set in task_candidates:
        assignments, total_cost = _select_semantic_assignments(
            task_set,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
        )
        selected_fmu_uids = _ordered_assignment_uids(assignments)
        selected_fmus = [fmu_by_uid[uid] for uid in selected_fmu_uids]
        graph = _build_semantic_port_graph(task_set, assignments, fmu_by_uid)
        closure_ok = graph.closure_ok
        result = MatchingResult(
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
                "stage2_variant": "semantic_retrieval_only",
                "structural_reasoning": False,
                "selected_task_count": len(assignments),
                "failure_type": "" if closure_ok else "port_graph_closure",
            },
        )
        results.append(result)
        taskset_summaries.append(
            _build_taskset_result_summary(
                result=result,
                selected_fmu_uids=selected_fmu_uids,
            )
        )

    def _selection_key(result: MatchingResult) -> tuple[int, float, float, str]:
        return (
            0 if result.diagnostics.get("status") == "ok" else 1,
            float(result.final_cost),
            -float(len(result.graph.bindings)),
            str(result.task_set.task_set_id or ""),
        )

    best = min(results, key=_selection_key)
    return replace(best, taskset_results=taskset_summaries)


__all__ = ["semantic_retrieval_only_stage2"]
