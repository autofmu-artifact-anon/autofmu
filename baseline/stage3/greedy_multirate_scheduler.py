"""Heuristic greedy multi-rate Stage-3 scheduler for baseline bundles.

Ablation: heuristic per-node step sizes with ZOH.
Completely self-contained — only data-structure imports from pipeline.types.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pipeline.types import (
    CompositionResult,
    FMU,
    MatchingResult,
    MBSEContext,
    OrchestrationGraph,
    PortBinding,
    SimulationConfig,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage3_greedy_multirate",
        "baseline_b3_graph_aware",
    }
)

_MAX_MATERIALIZED_POINTS = 100_000


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
            "greedy_multirate_scheduler_stage3 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("greedy_multirate_scheduler_stage3 requires config['workspace_root']")

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
# FMU step-size / duration inference
# ---------------------------------------------------------------------------

def _preferred_step(fmu: FMU) -> float:
    default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
    raw = default.get("stepSize") if isinstance(default, dict) else None
    if raw is None:
        raw = fmu.capabilities.fixed_internal_step_size
    try:
        step = float(raw)
    except (TypeError, ValueError):
        step = 0.01
    return step if step > 0.0 else 0.01


def _node_is_adjustable(fmu: FMU) -> bool:
    return bool(
        fmu.capabilities.can_handle_variable_communication_step_size
        and fmu.capabilities.fixed_internal_step_size is None
    )


def _infer_duration(matching: MatchingResult) -> float:
    regimes = [
        task.operating_regime
        for task in matching.task_set.tasks
        if task.operating_regime is not None
    ]
    for regime in regimes:
        if regime and regime.end_time is not None and regime.end_time > 0:
            return float(regime.end_time - (regime.start_time or 0.0)) or float(regime.end_time)

    durations: list[float] = []
    for fmu in matching.selected_fmus:
        default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
        if isinstance(default, dict):
            stop = default.get("stopTime")
            start = default.get("startTime", 0.0)
            if isinstance(stop, (int, float)) and float(stop) > float(start):
                durations.append(float(stop) - float(start))
    return max(durations) if durations else 1.0


# ---------------------------------------------------------------------------
# GCD-based base tick computation
# ---------------------------------------------------------------------------

def _float_gcd(a: float, b: float, precision: int = 9) -> float:
    """GCD of two positive floats via integer scaling."""
    factor = 10**precision
    return math.gcd(round(a * factor), round(b * factor)) / factor


def _compute_base_tick(step_sizes: Sequence[float]) -> float:
    """Compute base tick as GCD of all FMU default step sizes."""
    if not step_sizes:
        return 0.01
    positive = [s for s in step_sizes if s > 0.0]
    if not positive:
        return 0.01
    result = positive[0]
    for s in positive[1:]:
        result = _float_gcd(result, s)
    return max(result, 1e-12)


def _quantize_period(preferred_step: float, base_tick: float) -> float:
    """Quantize a preferred step size to the nearest multiple of base tick."""
    multiples = max(1, round(preferred_step / base_tick))
    return float(multiples) * float(base_tick)


# ---------------------------------------------------------------------------
# Graph helpers (self-contained, no import from static_rule_scheduler)
# ---------------------------------------------------------------------------

def _graph_edges(bindings: Sequence[PortBinding], node_set: set[str]) -> list[tuple[str, str]]:
    edges = {
        (binding.source_fmu, binding.target_fmu)
        for binding in bindings
        if binding.source_fmu in node_set
        and binding.target_fmu in node_set
        and binding.source_fmu != binding.target_fmu
    }
    return sorted(edges)


def _degree_maps(
    node_order: Sequence[str],
    edges: Sequence[tuple[str, str]],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    outgoing: dict[str, set[str]] = {uid: set() for uid in node_order}
    incoming: dict[str, set[str]] = {uid: set() for uid in node_order}
    undirected: dict[str, set[str]] = {uid: set() for uid in node_order}
    for source, target in edges:
        outgoing[source].add(target)
        incoming[target].add(source)
        undirected[source].add(target)
        undirected[target].add(source)
    return outgoing, incoming, undirected


def _has_cycle(node_order: Sequence[str], outgoing: Mapping[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visited:
            return False
        if node in visiting:
            return True
        visiting.add(node)
        for neighbor in sorted(outgoing[node]):
            if visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in node_order)


def _topological_order(
    node_order: Sequence[str],
    outgoing: Mapping[str, set[str]],
    incoming: Mapping[str, set[str]],
) -> list[str]:
    indegree = {uid: len(incoming[uid]) for uid in node_order}
    ready = deque(sorted(uid for uid in node_order if indegree[uid] == 0))
    ordered: list[str] = []

    while ready:
        node = ready.popleft()
        ordered.append(node)
        for neighbor in sorted(outgoing[node]):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)

    if len(ordered) != len(node_order):
        return sorted(node_order)
    return ordered


# ---------------------------------------------------------------------------
# Ordering helpers
# ---------------------------------------------------------------------------

def _sorted_bindings(bindings: Sequence[PortBinding], node_index: Mapping[str, int]) -> list[PortBinding]:
    return sorted(
        bindings,
        key=lambda binding: (
            node_index.get(binding.source_fmu, 10**6),
            node_index.get(binding.target_fmu, 10**6),
            binding.source_fmu,
            binding.target_fmu,
            binding.source_signal,
            binding.target_signal,
            binding.chain_id,
            binding.segment_id,
        ),
    )


def _ordered_fmus(matching: MatchingResult, node_order: Sequence[str]) -> list[Any]:
    fmu_by_uid = {fmu.uid: fmu for fmu in matching.selected_fmus}
    return [fmu_by_uid[uid] for uid in node_order if uid in fmu_by_uid]


def _linearized_bindings(
    bindings: Sequence[PortBinding],
    *,
    node_index: Mapping[str, int],
) -> list[PortBinding]:
    used_sources: set[str] = set()
    used_targets: set[str] = set()
    linearized: list[PortBinding] = []
    for binding in _sorted_bindings(bindings, node_index):
        source_index = node_index.get(binding.source_fmu, -1)
        target_index = node_index.get(binding.target_fmu, -1)
        if source_index < 0 or target_index < 0 or source_index >= target_index:
            continue
        if binding.source_fmu in used_sources or binding.target_fmu in used_targets:
            continue
        used_sources.add(binding.source_fmu)
        used_targets.add(binding.target_fmu)
        linearized.append(binding)
    return linearized


def _coarse_periods(
    node_order: Sequence[str],
    *,
    bindings: Sequence[PortBinding],
    base_tick: float,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    incoming_nodes = {binding.target_fmu for binding in bindings}
    periods: dict[str, float] = {}
    adjustments: list[dict[str, Any]] = []
    for uid in node_order:
        period = 2.0 * float(base_tick) if uid in incoming_nodes else float(base_tick)
        periods[uid] = period
        if period > float(base_tick):
            adjustments.append(
                {
                    "node": uid,
                    "old_period": float(base_tick),
                    "new_period": period,
                    "reason": "coarse_linearized_downstream",
                }
            )
    return periods, adjustments


# ---------------------------------------------------------------------------
# Greedy node ordering
# ---------------------------------------------------------------------------

def _greedy_node_order(
    matching_result: MatchingResult,
    *,
    selected_node_ids: Sequence[str],
    outgoing: Mapping[str, set[str]],
    incoming: Mapping[str, set[str]],
) -> list[str]:
    fmu_by_uid = {fmu.uid: fmu for fmu in matching_result.selected_fmus}
    preferred_steps = {
        uid: _preferred_step(fmu_by_uid[uid])
        for uid in selected_node_ids
        if uid in fmu_by_uid
    }
    if _has_cycle(selected_node_ids, outgoing):
        return sorted(selected_node_ids, key=lambda uid: (preferred_steps.get(uid, 0.01), uid))

    indegree = {uid: len(incoming[uid]) for uid in selected_node_ids}
    ready = sorted(
        [uid for uid in selected_node_ids if indegree[uid] == 0],
        key=lambda uid: (preferred_steps.get(uid, 0.01), -len(outgoing[uid]), uid),
    )
    ordered: list[str] = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for neighbor in sorted(outgoing[node]):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)
                ready.sort(key=lambda uid: (preferred_steps.get(uid, 0.01), -len(outgoing[uid]), uid))
    if len(ordered) != len(selected_node_ids):
        return _topological_order(selected_node_ids, outgoing, incoming)
    return ordered


# ---------------------------------------------------------------------------
# Greedy period adjustment
# ---------------------------------------------------------------------------

def _greedy_adjust_periods(
    ordered_bindings: Sequence[PortBinding],
    *,
    ordered_fmus: Sequence[FMU],
    base_tick: float,
    per_node_period: Mapping[str, float],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    adjusted = {uid: float(step) for uid, step in per_node_period.items()}
    fmu_by_uid = {fmu.uid: fmu for fmu in ordered_fmus}
    adjustments: list[dict[str, Any]] = []
    for binding in ordered_bindings:
        source_period = float(adjusted.get(binding.source_fmu, base_tick))
        target_period = float(adjusted.get(binding.target_fmu, base_tick))
        if source_period <= 0.0 or target_period <= 0.0:
            continue
        if source_period <= target_period:
            faster_uid, slower_uid = binding.source_fmu, binding.target_fmu
        else:
            faster_uid, slower_uid = binding.target_fmu, binding.source_fmu
        faster = float(adjusted.get(faster_uid, base_tick))
        slower = float(adjusted.get(slower_uid, base_tick))
        if faster <= 0.0 or slower <= 0.0:
            continue
        ratio = slower / faster
        rounded_ratio = round(ratio)
        if abs(ratio - rounded_ratio) <= 1e-8 and rounded_ratio >= 1:
            continue
        slower_fmu = fmu_by_uid.get(slower_uid)
        if slower_fmu is None or not _node_is_adjustable(slower_fmu):
            continue
        compatible_multiple = max(1, int(slower // faster))
        candidate = max(float(base_tick), float(compatible_multiple) * faster)
        if candidate >= slower - 1e-12:
            continue
        adjusted[slower_uid] = candidate
        adjustments.append(
            {
                "node": slower_uid,
                "old_period": slower,
                "new_period": candidate,
                "reason": f"align_with_{faster_uid}",
            }
        )
    return adjusted, adjustments


# ---------------------------------------------------------------------------
# ZOH edge labeling
# ---------------------------------------------------------------------------

def _label_edges_zoh(
    bindings: Sequence[PortBinding],
    per_node_period: Mapping[str, float],
) -> list[dict[str, Any]]:
    """Label each edge as sync or async (ZOH) based on source/target periods."""
    policies: list[dict[str, Any]] = []
    for binding in bindings:
        source_period = per_node_period.get(binding.source_fmu, 0.0)
        target_period = per_node_period.get(binding.target_fmu, 0.0)
        is_async = abs(source_period - target_period) > 1e-12
        policies.append({
            "source_fmu": binding.source_fmu,
            "source_signal": binding.source_signal,
            "target_fmu": binding.target_fmu,
            "target_signal": binding.target_signal,
            "source_period": source_period,
            "target_period": target_period,
            "async": is_async,
            "hold": "zoh" if is_async else "none",
        })
    return policies


# ---------------------------------------------------------------------------
# Communication grid & per-node schedule
# ---------------------------------------------------------------------------

def _build_communication_grid(base_tick: float, duration: float) -> list[float]:
    if base_tick <= 0 or duration <= 0:
        return [0.0]
    n_points = int(duration / base_tick) + 1
    grid: list[float] = []
    for i in range(n_points):
        t = round(i * base_tick, 12)
        if t > duration + 1e-12:
            break
        grid.append(t)
    return grid


def _build_per_node_schedule(
    per_node_period: Mapping[str, float],
    communication_grid: Sequence[float],
    base_tick: float,
) -> dict[str, list[float]]:
    schedules: dict[str, list[float]] = {}
    for uid, period in per_node_period.items():
        rate_multiple = max(1, round(period / base_tick))
        node_times = [
            communication_grid[i]
            for i in range(len(communication_grid))
            if i % rate_multiple == 0
        ]
        schedules[uid] = node_times
    return schedules


# ---------------------------------------------------------------------------
# Connection records & execution plan
# ---------------------------------------------------------------------------

def _build_connection_records(bindings: Sequence[PortBinding]) -> list[dict[str, Any]]:
    return [
        {
            "source": f"{binding.source_fmu}.{binding.source_signal}",
            "target": f"{binding.target_fmu}.{binding.target_signal}",
            "kind": "direct",
            "selected_by": binding.selected_by or "greedy_multirate",
            "scheduler_family": "greedy_multirate",
        }
        for binding in bindings
    ]


def _build_execution_plan(
    communication_grid: Sequence[float],
    per_node_schedule: Mapping[str, Sequence[float]],
    *,
    node_order: Sequence[str],
    per_node_period: Mapping[str, float],
    base_tick: float,
) -> list[dict[str, Any]]:
    rounded_schedule = {
        uid: {round(float(time), 12) for time in times}
        for uid, times in per_node_schedule.items()
    }
    execution_plan: list[dict[str, Any]] = []
    for time in communication_grid:
        rounded_time = round(float(time), 12)
        active_nodes = [uid for uid in node_order if rounded_time in rounded_schedule.get(uid, set())]
        execution_plan.append(
            {
                "time": rounded_time,
                "active_nodes": active_nodes,
                "family": "greedy_multirate",
                "rate_multiples": {
                    uid: round(float(per_node_period.get(uid, base_tick)) / max(float(base_tick), 1e-12), 6)
                    for uid in active_nodes
                },
                "requires_fixed_point_iteration": False,
            }
        )
    return execution_plan


def _adjusted_node_map(adjustments: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for item in adjustments:
        node = str(item.get("node") or "").strip()
        if not node:
            continue
        reason = str(item.get("reason") or "")
        aligned_with = reason.removeprefix("align_with_") if reason.startswith("align_with_") else ""
        mapped[node] = {
            "old_step": float(item.get("old_period") or 0.0),
            "new_step": float(item.get("new_period") or 0.0),
            "aligned_with": aligned_with,
        }
    return mapped


# ---------------------------------------------------------------------------
# Multirate edge validation
# ---------------------------------------------------------------------------

def _rate_ratio_supported(edge_policy: Mapping[str, Any]) -> bool:
    source_period = float(edge_policy.get("source_period") or 0.0)
    target_period = float(edge_policy.get("target_period") or 0.0)
    faster = min(source_period, target_period)
    slower = max(source_period, target_period)
    if faster <= 0.0 or slower <= 0.0:
        return False
    ratio = slower / faster
    rounded_ratio = round(ratio)
    return rounded_ratio >= 1 and abs(ratio - rounded_ratio) <= 1e-8


def _unsupported_multirate_edges(per_edge_hold_policy: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in per_edge_hold_policy if bool(item.get("async")) and not _rate_ratio_supported(item)]


# ---------------------------------------------------------------------------
# Local config validation
# ---------------------------------------------------------------------------

def _validate_simulation_config(config: SimulationConfig) -> list[str]:
    issues: list[str] = []
    if config.step_size <= 0:
        issues.append("step_size must be positive")
    if config.duration <= 0:
        issues.append("duration must be positive")
    if not config.fmus:
        issues.append("fmus list is empty")
    if config.step_size > config.duration:
        issues.append("step_size exceeds duration")
    fmu_uids = [fmu.uid for fmu in config.fmus]
    if len(fmu_uids) != len(set(fmu_uids)):
        issues.append("duplicate fmu uids")
    seen_conns: set[str] = set()
    for conn in config.connections:
        key = f"{conn.get('source', '')}->{conn.get('target', '')}"
        if key in seen_conns:
            issues.append(f"duplicate connection: {key}")
        seen_conns.add(key)
    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def greedy_multirate_scheduler_stage3(
    matching_result: MatchingResult,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> CompositionResult:
    del mbse_context
    stage_config = _config_dict(config)
    method_name, workspace_root = _validate_workspace_context(stage_config)
    if not matching_result.selected_fmus:
        raise ValueError("greedy_multirate_scheduler_stage3 received empty selected_fmus")

    selected_node_ids = [fmu.uid for fmu in matching_result.selected_fmus]
    selected_node_set = set(selected_node_ids)
    edges = _graph_edges(matching_result.graph.bindings, selected_node_set)
    outgoing, incoming, _ = _degree_maps(selected_node_ids, edges)

    if not bool(matching_result.graph.closure_ok):
        raise ValueError("greedy_multirate_scheduler_stage3 requires a closure_ok orchestration graph")
    if matching_result.discrepancy_set:
        raise ValueError("greedy_multirate_scheduler_stage3 does not support discrepancy_set or adapter generation")

    node_order = _greedy_node_order(
        matching_result,
        selected_node_ids=selected_node_ids,
        outgoing=outgoing,
        incoming=incoming,
    )
    node_index = {uid: index for index, uid in enumerate(node_order)}
    ordered_fmus = _ordered_fmus(matching_result, node_order)

    ordered_bindings = _linearized_bindings(
        matching_result.graph.bindings,
        node_index=node_index,
    )

    step_sizes = [_preferred_step(fmu) for fmu in ordered_fmus]
    base_tick = max(step_sizes) if step_sizes else 0.01
    raw_periods = {uid: float(base_tick) for uid in node_order}
    per_node_period, adjustments = _coarse_periods(
        node_order,
        bindings=ordered_bindings,
        base_tick=base_tick,
    )
    adjusted_nodes = _adjusted_node_map(adjustments)

    per_edge_hold_policy = _label_edges_zoh(ordered_bindings, per_node_period)

    duration = _infer_duration(matching_result)
    materialized = (duration / base_tick) <= _MAX_MATERIALIZED_POINTS
    communication_grid = _build_communication_grid(base_tick, duration) if materialized else []
    per_node_schedule = (
        _build_per_node_schedule(per_node_period, communication_grid, base_tick)
        if materialized
        else {}
    )
    execution_plan = (
        _build_execution_plan(
            communication_grid,
            per_node_schedule,
            node_order=node_order,
            per_node_period=per_node_period,
            base_tick=base_tick,
        )
        if materialized
        else []
    )

    schedule: dict[str, Any] = {
        "base_tick": base_tick,
        "duration": duration,
        "per_node_period": dict(per_node_period),
        "per_edge_hold_policy": per_edge_hold_policy,
        "loop_wrappers": [],
        "warnings": [],
        "base_tick_method": "max_default_step",
        "materialized": materialized,
        "communication_point_count": len(communication_grid),
        "family": "greedy_multirate",
        "node_order": list(node_order),
        "adjustments": list(adjustments),
        "adjusted_nodes": dict(adjusted_nodes),
        "initial_fmu_steps": dict(raw_periods),
    }

    connections = _build_connection_records(ordered_bindings)
    connection_order = [f"{item['source']}->{item['target']}" for item in connections]

    simulation_config = SimulationConfig(
        step_size=base_tick,
        duration=duration,
        fmus=ordered_fmus,
        connections=connections,
        scheduler={
            "base_tick": base_tick,
            "per_node_period": dict(per_node_period),
            "communication_grid": communication_grid,
            "per_node_schedule": {uid: list(times) for uid, times in per_node_schedule.items()} if per_node_schedule else {},
            "per_edge_hold_policy": per_edge_hold_policy,
            "execution_plan": execution_plan,
            "materialized": materialized,
            "warnings": [],
            "family": "greedy_multirate",
            "node_order": list(node_order),
            "adjustments": list(adjustments),
            "adjusted_nodes": dict(adjusted_nodes),
            "async_edges": [item for item in per_edge_hold_policy if item.get("async")],
            "start_time": 0.0,
            "stop_time": duration,
            "communication_point_count": len(communication_grid),
        },
        meta={
            "method_name": method_name,
            "workspace_root": str(workspace_root),
            "selected_task_set_id": matching_result.task_set.task_set_id,
            "selected_asset_ids": [fmu.uid for fmu in ordered_fmus],
            "rate_adjustments": list(adjustments),
            "adjusted_nodes": dict(adjusted_nodes),
            "adapters": [],
        },
    )

    validation_issues = _validate_simulation_config(simulation_config)

    graph_augmented = OrchestrationGraph(
        nodes=list(node_order),
        port_nodes=list(matching_result.graph.port_nodes),
        bindings=list(ordered_bindings),
        component_to_fmu=dict(matching_result.graph.component_to_fmu),
        required_signal_chains=list(matching_result.graph.required_signal_chains),
        binding_candidates=list(matching_result.graph.binding_candidates),
        closure_ok=bool(matching_result.graph.closure_ok),
        closure_failures=list(matching_result.graph.closure_failures),
        routing_failures=list(matching_result.graph.routing_failures),
        diagnostics={
            **dict(matching_result.graph.diagnostics),
            "stage3_variant": "greedy_multirate_scheduler",
            "rate_adjustment_count": len(adjustments),
            "adapter_generation": False,
            "linearized_binding_count": len(ordered_bindings),
            "coarse_multirate": True,
        },
    )

    return CompositionResult(
        graph_augmented=graph_augmented,
        adapters=[],
        schedule=schedule,
        loop_resolution=[],
        simulation_config=simulation_config,
        diagnostics={
            "stage3_variant": "greedy_multirate_scheduler",
            "rate_adjustment_count": len(adjustments),
            "validation_issues": validation_issues,
            "linearized_binding_count": len(ordered_bindings),
            "coarse_multirate": True,
        },
    )


__all__ = ["greedy_multirate_scheduler_stage3"]
