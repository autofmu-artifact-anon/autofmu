"""Transport helpers for Stage 2 matching."""

from __future__ import annotations

import math
from typing import List, Sequence

from pipeline.types import FMU, TaskAssignment, TaskSet

from .feasibility import assignment_mask_value, explain_assignment_mask
from .scoring import semantic_cost_matrix


def build_semantic_cost_matrix(taskset: TaskSet, fmu_library: Sequence[FMU]) -> List[List[float]]:
    return semantic_cost_matrix(taskset, fmu_library)


def build_hard_mask_explanations(taskset: TaskSet, mbse_context, fmu_library: Sequence[FMU]) -> List[List[dict]]:
    rows = len(taskset.tasks)
    cols = len(fmu_library)
    explanations = [[{} for _ in range(cols)] for _ in range(rows)]
    for row, task in enumerate(taskset.tasks):
        for col, fmu in enumerate(fmu_library):
            explanations[row][col] = explain_assignment_mask(
                task,
                fmu,
                mbse_context=mbse_context,
                taskset_context=taskset,
            )
    return explanations


def build_hard_mask_matrix(taskset: TaskSet, mbse_context, fmu_library: Sequence[FMU]) -> List[List[float]]:
    rows = len(taskset.tasks)
    cols = len(fmu_library)
    mask = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for row, task in enumerate(taskset.tasks):
        for col, fmu in enumerate(fmu_library):
            mask[row][col] = float(
                assignment_mask_value(
                    task,
                    fmu,
                    mbse_context=mbse_context,
                    taskset_context=taskset,
                )
            )
    return mask


def solve_row_constrained_sinkhorn(
    cost_matrix: List[List[float]],
    row_mass: List[float],
    epsilon: float = 0.05,
    max_iters: int = 200,
    tol: float = 1e-6,
) -> dict:
    epsilon = max(float(epsilon), 1e-6)
    if not cost_matrix:
        return {
            "cost_matrix": cost_matrix,
            "transport_matrix": cost_matrix,
            "iterations": 0,
            "converged": True,
            "epsilon": epsilon,
        }
    rows = len(cost_matrix)
    cols = len(cost_matrix[0]) if rows else 0
    log_kernel = [[-math.inf for _ in range(cols)] for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            if math.isfinite(cost_matrix[row][col]):
                log_kernel[row][col] = -cost_matrix[row][col] / epsilon
    current = [[0.0 for _ in range(cols)] for _ in range(rows)]
    converged = False
    iteration = 0
    for iteration in range(max(int(max_iters), 1)):
        previous = [list(row) for row in current]
        for row in range(rows):
            row_vals = log_kernel[row]
            finite_vals = [value for value in row_vals if math.isfinite(value)]
            if not finite_vals:
                current[row] = [0.0 for _ in range(cols)]
                continue
            max_val = max(finite_vals)
            probs = [0.0 for _ in range(cols)]
            for col in range(cols):
                if math.isfinite(row_vals[col]):
                    probs[col] = math.exp(row_vals[col] - max_val)
            denom = float(sum(probs))
            if denom <= 0:
                current[row] = [0.0 for _ in range(cols)]
                continue
            current[row] = [value / denom * float(row_mass[row]) for value in probs]
        delta = max(abs(current[row][col] - previous[row][col]) for row in range(rows) for col in range(cols))
        if delta <= tol:
            converged = True
            break
    return {
        "cost_matrix": cost_matrix,
        "transport_matrix": current,
        "iterations": iteration + 1,
        "converged": converged,
        "epsilon": epsilon,
    }


def compute_transport_objective(plan: dict) -> float:
    transport = plan.get("transport_matrix", [])
    cost_matrix = plan.get("cost_matrix", [])
    epsilon = float(plan.get("epsilon", 0.0) or 0.0)
    if not transport or not cost_matrix:
        return float("inf")
    total_cost = 0.0
    entropy = 0.0
    for row in range(min(len(transport), len(cost_matrix))):
        for col in range(min(len(transport[row]), len(cost_matrix[row]))):
            mass = float(transport[row][col])
            if mass <= 0.0:
                continue
            cost = float(cost_matrix[row][col])
            if not math.isfinite(cost):
                continue
            total_cost += mass * cost
            entropy -= mass * math.log(max(mass, 1e-12))
    return float(total_cost - epsilon * entropy)


def extract_assignment_from_transport(
    plan: dict,
    taskset: TaskSet,
    fmu_library: Sequence[FMU],
    top_m_per_task: int,
    *,
    mask_matrix: List[List[float]],
    semantic_matrix: List[List[float]],
    revision_index: int,
) -> List[TaskAssignment]:
    transport = plan.get("transport_matrix", [])
    assignments: List[TaskAssignment] = []
    if not transport:
        return assignments
    for row, task in enumerate(taskset.tasks):
        if row >= len(transport):
            continue
        if float(sum(transport[row])) <= 0.0:
            continue
        candidate_cols = sorted(
            range(len(transport[row])),
            key=lambda col: (-float(transport[row][col]), fmu_library[col].uid),
        )[: max(int(top_m_per_task), 1)]
        if not candidate_cols:
            continue
        selected_col = int(candidate_cols[0])
        fmu = fmu_library[selected_col]
        transport_mass = float(transport[row][selected_col])
        if transport_mass <= 0.0:
            continue
        semantic_cost = float(semantic_matrix[row][selected_col])
        hard_mask_value = float(mask_matrix[row][selected_col])
        assignments.append(
            TaskAssignment(
                task_id=task.task_id,
                task_index=row,
                fmu_uid=fmu.uid,
                score=float(1.0 - semantic_cost),
                cost=float(semantic_cost + (0.0 if math.isfinite(hard_mask_value) else 1e6)),
                hard_ok=bool(math.isfinite(hard_mask_value)),
                semantic_cost=semantic_cost,
                hard_mask_value=hard_mask_value,
                transport_mass=transport_mass,
                revision_index=int(revision_index),
                reasons=[f"transport_top_mass={transport_mass:.6f}"],
                grounded_components=list(task.grounded_components),
            )
        )
    return assignments
