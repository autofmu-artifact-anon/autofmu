"""Schedule construction helpers for Stage 3."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from pipeline.types import FMU, PortBinding

from .gcd_utils import gcd_like_base_tick


MAX_MATERIALIZED_COMMUNICATION_POINTS = 5000


def build_base_tick(fmus: Iterable[FMU]) -> Dict[str, object]:
    per_fmu: Dict[str, float] = {}
    warnings: List[str] = []
    for fmu in fmus:
        default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
        step = None
        if isinstance(default, dict):
            step = default.get("stepSize")
        if step is None and fmu.capabilities.fixed_internal_step_size is not None:
            step = fmu.capabilities.fixed_internal_step_size
        try:
            numeric = float(step)
        except (TypeError, ValueError):
            numeric = 0.01
            warnings.append(f"fallback_step_size_for_{fmu.uid}=0.01")
        if numeric <= 0:
            numeric = 0.01
            warnings.append(f"fallback_step_size_for_{fmu.uid}=0.01")
        per_fmu[fmu.uid] = numeric
    base_tick, method = gcd_like_base_tick(per_fmu.values())
    if base_tick <= 0:
        base_tick = min(per_fmu.values()) if per_fmu else 0.01
        warnings.append(f"fallback_base_tick={base_tick}")
    return {
        "base_tick": float(base_tick),
        "fmu_steps": per_fmu,
        "method": method,
        "warnings": warnings,
    }


def build_communication_grid(base_tick: float, duration: float) -> List[float]:
    if base_tick <= 0:
        base_tick = 0.01
    if duration <= 0:
        duration = base_tick
    points = int(round(duration / base_tick))
    grid = [round(index * base_tick, 12) for index in range(points + 1)]
    if not grid or grid[-1] < duration:
        grid.append(round(float(duration), 12))
    return grid


def communication_point_count(base_tick: float, duration: float) -> int:
    if base_tick <= 0:
        base_tick = 0.01
    if duration <= 0:
        duration = base_tick
    points = int(round(float(duration) / float(base_tick)))
    needs_stop_append = round(points * float(base_tick), 12) < round(float(duration), 12)
    return points + 1 + (1 if needs_stop_append else 0)


def build_per_node_schedule(fmu_steps: Dict[str, float], communication_grid: List[float]) -> Dict[str, List[float]]:
    schedules: Dict[str, List[float]] = {}
    for uid, step in fmu_steps.items():
        schedules[uid] = [time for time in communication_grid if _aligned(time, step)]
    return schedules


def attach_zoh_policy(bindings: List[PortBinding], fmu_steps: Dict[str, float]) -> List[Dict[str, object]]:
    policies: List[Dict[str, object]] = []
    for binding in bindings:
        source_period = float(fmu_steps.get(binding.source_fmu, 0.0))
        target_period = float(fmu_steps.get(binding.target_fmu, 0.0))
        async_edge = abs(source_period - target_period) > 1e-12
        policies.append(
            {
                "source": f"{binding.source_fmu}.{binding.source_signal}",
                "target": f"{binding.target_fmu}.{binding.target_signal}",
                "policy": "zoh" if async_edge else "direct",
                "source_period": source_period,
                "target_period": target_period,
                "async": async_edge,
            }
        )
    return policies


def build_execution_plan(
    communication_grid: List[float],
    per_node_schedule: Dict[str, List[float]],
    loop_wrappers: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    rounded_grid = [round(float(time), 12) for time in communication_grid]
    rounded_schedule = {
        uid: {round(float(time), 12) for time in times}
        for uid, times in per_node_schedule.items()
    }
    loop_ids = [str(item.get("loop_id") or "") for item in loop_wrappers]
    execution_plan: List[Dict[str, object]] = []
    for time in rounded_grid:
        active_nodes = sorted(uid for uid, times in rounded_schedule.items() if time in times)
        active_loops = [
            {
                "loop_id": loop_id,
                "iteration_budget": int(item.get("max_iters") or 0),
                "tol": float(item.get("tol") or 0.0),
                "method": str(item.get("method") or "gauss_seidel"),
                "node_order": list(item.get("node_order") or []),
                "iterate_until_converged": bool((item.get("runtime_policy") or {}).get("iterate_until_converged", False)),
                "boundary_variables": list(item.get("boundary_variables") or []),
                "runtime_policy": dict(item.get("runtime_policy") or {}),
            }
            for loop_id, item in zip(loop_ids, loop_wrappers)
            if loop_id and _loop_active_at_time(item, active_nodes)
        ]
        execution_plan.append(
            {
                "time": time,
                "active_nodes": active_nodes,
                "loop_ids": [str(item.get("loop_id") or "") for item in loop_wrappers if _loop_active_at_time(item, active_nodes)],
                "active_loops": active_loops,
                "requires_fixed_point_iteration": bool(active_loops),
            }
        )
    return execution_plan


def should_materialize_schedule(base_tick: float, duration: float) -> bool:
    return communication_point_count(base_tick, duration) <= MAX_MATERIALIZED_COMMUNICATION_POINTS


def build_compact_schedule_descriptor(
    *,
    base_tick: float,
    duration: float,
    per_node_period: Dict[str, float],
    per_edge_hold_policy: List[Dict[str, object]],
    loop_wrappers: List[Dict[str, object]],
    warnings: List[str],
    base_tick_method: str,
    materialized: bool,
    communication_grid: List[float] | None = None,
    per_node_schedule: Dict[str, List[float]] | None = None,
    execution_plan: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    point_count = communication_point_count(base_tick, duration)
    schedule: Dict[str, Any] = {
        "kind": "multi_rate",
        "base_tick": float(base_tick),
        "start_time": 0.0,
        "duration": float(duration),
        "stop_time": float(duration),
        "communication_point_count": point_count,
        "materialized": bool(materialized),
        "per_node_period": {str(uid): float(step) for uid, step in per_node_period.items()},
        "per_edge_hold_policy": list(per_edge_hold_policy),
        "loop_wrappers": list(loop_wrappers),
        "async_edges": [item for item in per_edge_hold_policy if item.get("async")],
        "warnings": list(warnings),
        "base_tick_method": str(base_tick_method),
    }
    if materialized:
        schedule["communication_grid"] = list(communication_grid or [])
        schedule["per_node_schedule"] = {str(uid): list(times) for uid, times in (per_node_schedule or {}).items()}
        schedule["execution_plan"] = list(execution_plan or [])
    return schedule


def _aligned(time: float, step: float) -> bool:
    if step <= 0:
        return False
    ratio = time / step if step else 0.0
    return abs(ratio - round(ratio)) <= 1e-8


def _loop_active_at_time(loop_wrapper: Dict[str, object], active_nodes: List[str]) -> bool:
    loop_nodes = [str(node) for node in list(loop_wrapper.get("node_order") or loop_wrapper.get("nodes") or []) if node]
    if not loop_nodes:
        return False
    active = set(active_nodes)
    return all(node in active for node in loop_nodes)
