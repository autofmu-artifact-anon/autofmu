"""Failure-driven mask revisions for Stage 2."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from pipeline.types import TaskAssignment


def select_conflict_pair_for_mask_update(graph_failure: Dict[str, object] | None, assignments: Sequence[TaskAssignment]) -> Tuple[int, str] | None:
    if not isinstance(graph_failure, dict):
        return None
    if not _failure_requires_mask_revision(graph_failure):
        return None
    pair = graph_failure.get("responsible_pair")
    if isinstance(pair, (list, tuple)) and len(pair) == 2:
        task_index, fmu_uid = pair
        try:
            normalized = (int(task_index), str(fmu_uid))
        except (TypeError, ValueError):
            return None
        if assignments and normalized not in {(assignment.task_index, assignment.fmu_uid) for assignment in assignments}:
            return None
        return normalized
    return None


def apply_failure_mask_update(mask_matrix: Sequence[Sequence[float]], pair: Tuple[int, str], fmu_uids: Sequence[str]) -> List[List[float]]:
    updated = [list(row) for row in mask_matrix]
    task_index, fmu_uid = pair
    if 0 <= int(task_index) < len(updated):
        for col, uid in enumerate(fmu_uids):
            if uid == fmu_uid:
                updated[int(task_index)][col] = float("inf")
                break
    return updated


def _failure_requires_mask_revision(graph_failure: Dict[str, object]) -> bool:
    if "eligible_for_mask_revision" in graph_failure:
        return bool(graph_failure.get("eligible_for_mask_revision"))
    if str(graph_failure.get("revision_action") or "") not in {"", "exclude_pair"}:
        return False
    return str(graph_failure.get("failure_type") or "") in {
        "component_mapping_conflict",
        "missing_source_component_mapping",
        "missing_target_component_mapping",
        "intra_fmu_edge_forbidden",
        "topology_disallows",
        "unroutable_segment",
    }
