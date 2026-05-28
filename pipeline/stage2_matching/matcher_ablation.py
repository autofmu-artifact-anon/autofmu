"""Stage 2 ablation: simple best-FMU selection without graph revision."""

from __future__ import annotations

from typing import List, Optional

from pipeline.types import MatchingResult, OrchestrationGraph, TaskAssignment, TaskSet, FMU, MBSEContext

from .scoring import pairwise_semantic_cost, pairwise_semantic_similarity


def match(
    task_sets: List[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: List[FMU],
    max_revisions: int = 0,
    top_m_per_task: int = 1,
    max_port_candidates: int = 1,
) -> MatchingResult:
    del mbse_context, max_revisions, top_m_per_task, max_port_candidates
    if not task_sets:
        raise ValueError("match_ablation() received empty task_sets")
    if not fmu_library:
        raise ValueError("match_ablation() received empty fmu_library")

    best_task_set = task_sets[0]
    best_fmu: Optional[FMU] = None
    best_score = -1.0
    for task_set in task_sets:
        joined_objective = " ".join(task.objective for task in task_set.tasks)
        seed_task = task_set.tasks[0]
        for fmu in fmu_library:
            score = pairwise_semantic_similarity(seed_task, fmu) + 0.01 * len(joined_objective)
            if score > best_score:
                best_score = score
                best_task_set = task_set
                best_fmu = fmu

    assert best_fmu is not None
    assignment = TaskAssignment(
        task_id=best_task_set.tasks[0].task_id,
        task_index=0,
        fmu_uid=best_fmu.uid,
        score=float(best_score),
        cost=float(pairwise_semantic_cost(best_task_set.tasks[0], best_fmu)),
        semantic_cost=float(pairwise_semantic_cost(best_task_set.tasks[0], best_fmu)),
        hard_mask_value=0.0,
        transport_mass=1.0,
        revision_index=0,
        hard_ok=True,
        grounded_components=list(best_task_set.tasks[0].grounded_components),
    )
    return MatchingResult(
        task_set=best_task_set,
        assignments=[assignment],
        selected_fmus=[best_fmu],
        graph=OrchestrationGraph(nodes=[best_fmu.uid], bindings=[], component_to_fmu={}, diagnostics={"ablation": True}),
        discrepancy_set=[],
        revision_trace=[{"revision": 0, "status": "ablation_single_fmu"}],
        final_cost=float(assignment.cost),
        transport_plans=[],
        mask_history=[],
        taskset_results=[],
        selected_task_set_cost=float(assignment.cost),
        diagnostics={"status": "ok", "ablation": True},
    )
