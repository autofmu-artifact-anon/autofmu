"""Schedule/config builders for Stage 3."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from pipeline.types import FMU, SimulationConfig


def build_fixed_step_config(
    *,
    fmus: Sequence[FMU],
    step_size: float,
    duration: float,
    connections: List[Dict[str, Any]],
    meta: Dict[str, Any],
) -> SimulationConfig:
    return SimulationConfig(
        step_size=float(step_size),
        duration=float(duration),
        fmus=list(fmus),
        connections=list(connections),
        scheduler={"kind": "fixed_step", "step_size": float(step_size)},
        meta=dict(meta),
    )


def build_multi_rate_config(
    *,
    fmus: Sequence[FMU],
    base_tick: float,
    duration: float,
    connections: List[Dict[str, Any]],
    communication_grid: List[float],
    per_node_period: Dict[str, float],
    per_node_schedule: Dict[str, List[float]],
    per_edge_hold_policy: List[Dict[str, object]],
    loop_wrappers: List[Dict[str, object]],
    scheduler_meta: Dict[str, Any],
    meta: Dict[str, Any],
) -> SimulationConfig:
    scheduler = {
        "kind": "multi_rate",
        "base_tick": float(base_tick),
        "duration": float(duration),
        "per_node_period": {str(uid): float(step) for uid, step in per_node_period.items()},
        "per_edge_hold_policy": list(per_edge_hold_policy),
        "loop_wrappers": list(loop_wrappers),
        **scheduler_meta,
    }
    if communication_grid:
        scheduler["communication_grid"] = list(communication_grid)
        scheduler["communication_point_count"] = len(communication_grid)
    if per_node_schedule:
        scheduler["per_node_schedule"] = {str(uid): list(times) for uid, times in per_node_schedule.items()}
    return SimulationConfig(
        step_size=float(base_tick),
        duration=float(duration),
        fmus=list(fmus),
        connections=list(connections),
        scheduler=scheduler,
        meta=dict(meta),
    )
