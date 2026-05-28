"""Deterministic static-rule Stage-3 scheduler for baseline evaluator bundles.

Ablation: fixed topology templates, no adaptive optimization.
All logic is self-contained — only data-structure imports from pipeline.types.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pipeline.types import (
    CompositionResult,
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
        "ablation_stage3_static_rule_scheduler",
        "baseline_b1_rule_sequential",
        "baseline_b2_llm_retrieval_rule",
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
            "static_rule_scheduler_stage3 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("static_rule_scheduler_stage3 requires config['workspace_root']")

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

def _default_step_size(fmu: Any) -> float:
    default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
    if isinstance(default, dict):
        raw = default.get("stepSize")
        if raw is not None:
            try:
                step = float(raw)
                if step > 0.0:
                    return step
            except (TypeError, ValueError):
                pass
    if fmu.capabilities.fixed_internal_step_size is not None:
        try:
            step = float(fmu.capabilities.fixed_internal_step_size)
            if step > 0.0:
                return step
        except (TypeError, ValueError):
            pass
    return 0.01


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
# Graph helpers
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


def _is_weakly_connected(node_order: Sequence[str], undirected: Mapping[str, set[str]]) -> bool:
    if not node_order:
        return True
    visited: set[str] = set()
    queue = deque([node_order[0]])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(sorted(undirected[node] - visited))
    return len(visited) == len(node_order)


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
# Topology classification
# ---------------------------------------------------------------------------

def _strict_chain_family(
    node_order: Sequence[str],
    outgoing: Mapping[str, set[str]],
    incoming: Mapping[str, set[str]],
    undirected: Mapping[str, set[str]],
    edges: Sequence[tuple[str, str]],
) -> tuple[str, list[str]]:
    if len(node_order) <= 1:
        return "single_fmu", sorted(node_order)

    if _has_cycle(node_order, outgoing):
        raise ValueError("static_rule_scheduler_stage3 does not support loop handling")

    if len(edges) != len(node_order) - 1 or not _is_weakly_connected(node_order, undirected):
        raise ValueError("static_rule_scheduler_stage3 requires a strict chain topology")

    roots = [uid for uid in node_order if not incoming[uid]]
    sinks = [uid for uid in node_order if not outgoing[uid]]
    if len(roots) != 1 or len(sinks) != 1:
        raise ValueError("static_rule_scheduler_stage3 requires a strict chain topology")
    for uid in node_order:
        indegree = len(incoming[uid])
        outdegree = len(outgoing[uid])
        if uid in roots and indegree == 0 and outdegree == 1:
            continue
        if uid in sinks and indegree == 1 and outdegree == 0:
            continue
        if indegree == 1 and outdegree == 1:
            continue
        raise ValueError("static_rule_scheduler_stage3 requires a strict chain topology")

    ordered = _topological_order(node_order, outgoing, incoming)
    expected_edges = {(ordered[index], ordered[index + 1]) for index in range(len(ordered) - 1)}
    if set(edges) != expected_edges:
        raise ValueError("static_rule_scheduler_stage3 requires a strict chain topology")
    return "chain", ordered


# ---------------------------------------------------------------------------
# Ordering / connection helpers
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


def _strict_chain_bindings(
    bindings: Sequence[PortBinding],
    *,
    node_order: Sequence[str],
    node_index: Mapping[str, int],
) -> list[PortBinding]:
    if len(node_order) <= 1:
        return []
    by_pair: dict[tuple[str, str], PortBinding] = {}
    for binding in _sorted_bindings(bindings, node_index):
        pair = (binding.source_fmu, binding.target_fmu)
        by_pair.setdefault(pair, binding)
    pruned: list[PortBinding] = []
    for index in range(len(node_order) - 1):
        pair = (node_order[index], node_order[index + 1])
        binding = by_pair.get(pair)
        if binding is None:
            raise ValueError("static_rule_scheduler_stage3 requires a strict chain topology")
        pruned.append(binding)
    return pruned


def _build_connection_records(
    bindings: Sequence[PortBinding],
    *,
    schedule_family: str,
) -> list[dict[str, Any]]:
    return [
        {
            "source": f"{binding.source_fmu}.{binding.source_signal}",
            "target": f"{binding.target_fmu}.{binding.target_signal}",
            "kind": "direct",
            "selected_by": binding.selected_by or "static_rule",
            "rule_family": schedule_family,
        }
        for binding in bindings
    ]


# ---------------------------------------------------------------------------
# Communication grid & execution plan (local implementation)
# ---------------------------------------------------------------------------

def _build_communication_grid(step_size: float, duration: float) -> list[float]:
    if step_size <= 0 or duration <= 0:
        return [0.0]
    n_points = int(duration / step_size) + 1
    grid: list[float] = []
    for i in range(n_points):
        t = round(i * step_size, 12)
        if t > duration + 1e-12:
            break
        grid.append(t)
    return grid


def _build_execution_plan(
    communication_grid: Sequence[float],
    *,
    node_order: Sequence[str],
    schedule_family: str,
) -> list[dict[str, Any]]:
    return [
        {
            "time": round(float(time), 12),
            "active_nodes": list(node_order),
            "family": schedule_family,
            "requires_fixed_point_iteration": False,
        }
        for time in communication_grid
    ]


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

def static_rule_scheduler_stage3(
    matching_result: MatchingResult,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> CompositionResult:
    del mbse_context
    stage_config = _config_dict(config)
    method_name, workspace_root = _validate_workspace_context(stage_config)
    if not matching_result.selected_fmus:
        raise ValueError("static_rule_scheduler_stage3 received empty selected_fmus")

    selected_node_ids = [fmu.uid for fmu in matching_result.selected_fmus]
    selected_node_set = set(selected_node_ids)
    edges = _graph_edges(matching_result.graph.bindings, selected_node_set)
    outgoing, incoming, undirected = _degree_maps(selected_node_ids, edges)

    if not bool(matching_result.graph.closure_ok):
        raise ValueError("static_rule_scheduler_stage3 requires a closure_ok orchestration graph")
    if matching_result.discrepancy_set:
        raise ValueError("static_rule_scheduler_stage3 does not support discrepancy_set or adapter generation")

    schedule_family, node_order = _strict_chain_family(
        selected_node_ids, outgoing, incoming, undirected, edges,
    )
    node_index = {uid: index for index, uid in enumerate(node_order)}
    ordered_bindings = _strict_chain_bindings(
        matching_result.graph.bindings,
        node_order=node_order,
        node_index=node_index,
    )
    ordered_fmus = _ordered_fmus(matching_result, node_order)

    step_size = max(_default_step_size(fmu) for fmu in ordered_fmus) if ordered_fmus else 0.01
    duration = _infer_duration(matching_result)
    per_node_period = {uid: step_size for uid in node_order}

    materialized = (duration / step_size) <= _MAX_MATERIALIZED_POINTS
    communication_grid = _build_communication_grid(step_size, duration) if materialized else []
    execution_plan = (
        _build_execution_plan(
            communication_grid,
            node_order=node_order,
            schedule_family=schedule_family,
        )
        if materialized
        else []
    )

    schedule: dict[str, Any] = {
        "base_tick": step_size,
        "duration": duration,
        "per_node_period": dict(per_node_period),
        "per_edge_hold_policy": [],
        "loop_wrappers": [],
        "warnings": [],
        "base_tick_method": "max_default_step",
        "materialized": materialized,
        "communication_point_count": len(communication_grid),
        "family": schedule_family,
        "node_order": list(node_order),
        "fmu_steps": dict(per_node_period),
    }

    connections = _build_connection_records(ordered_bindings, schedule_family=schedule_family)
    connection_order = [f"{item['source']}->{item['target']}" for item in connections]

    simulation_config = SimulationConfig(
        step_size=step_size,
        duration=duration,
        fmus=ordered_fmus,
        connections=connections,
        scheduler={
            "base_tick": step_size,
            "per_node_period": dict(per_node_period),
            "communication_grid": communication_grid,
            "execution_plan": execution_plan,
            "materialized": materialized,
            "family": schedule_family,
            "node_order": list(node_order),
            "connection_order": connection_order,
            "deterministic": True,
            "start_time": 0.0,
            "stop_time": duration,
            "communication_point_count": len(communication_grid),
        },
        meta={
            "method_name": method_name,
            "workspace_root": str(workspace_root),
            "schedule_family": schedule_family,
            "selected_task_set_id": matching_result.task_set.task_set_id,
            "selected_asset_ids": [fmu.uid for fmu in ordered_fmus],
            "connection_order": connection_order,
            "adapters": [],
        },
    )

    validation_issues = _validate_simulation_config(simulation_config)

    graph_augmented = OrchestrationGraph(
        nodes=list(node_order),
        port_nodes=list(matching_result.graph.port_nodes),
        bindings=ordered_bindings,
        component_to_fmu=dict(matching_result.graph.component_to_fmu),
        required_signal_chains=list(matching_result.graph.required_signal_chains),
        binding_candidates=list(matching_result.graph.binding_candidates),
        closure_ok=bool(matching_result.graph.closure_ok),
        closure_failures=list(matching_result.graph.closure_failures),
        routing_failures=list(matching_result.graph.routing_failures),
        diagnostics={
            **dict(matching_result.graph.diagnostics),
            "stage3_variant": "static_rule_scheduler",
            "schedule_family": schedule_family,
            "global_optimization": False,
            "adapter_generation": False,
            "strict_chain_only": True,
        },
    )

    return CompositionResult(
        graph_augmented=graph_augmented,
        adapters=[],
        schedule=schedule,
        loop_resolution=[],
        simulation_config=simulation_config,
        diagnostics={
            "stage3_variant": "static_rule_scheduler",
            "schedule_family": schedule_family,
            "binding_count": len(ordered_bindings),
            "validation_issues": validation_issues,
            "deterministic": True,
            "global_optimization": False,
            "strict_chain_only": True,
        },
    )


__all__ = ["static_rule_scheduler_stage3"]
