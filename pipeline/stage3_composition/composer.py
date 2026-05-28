"""Stage 3 full implementation: composition, adapters, schedule, loop metadata."""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from pipeline.scenario_binding import derive_execution_order
from pipeline.types import CompositionResult, FMU, FMUCapabilities, MatchingResult, MBSEContext, OrchestrationGraph, PortMeta

from .loop_wrappers import build_gauss_seidel_wrapper_specs, detect_scc_loops
from .middleware import materialize_adapter_artifact, rewrite_graph_with_adapters, synthesize_adapter_spec
from .schedule_spec import (
    attach_zoh_policy,
    build_base_tick,
    build_communication_grid,
    build_compact_schedule_descriptor,
    build_execution_plan,
    build_per_node_schedule,
    should_materialize_schedule,
)
from .scheduler import build_multi_rate_config
from .validator import validate_config


_MAX_EXECUTION_COMMUNICATION_POINTS = 500_000


def _scenario_step_size(scenario_window: Mapping[str, Any] | None) -> float | None:
    if not isinstance(scenario_window, Mapping):
        return None
    try:
        numeric = float(scenario_window.get("step_size"))
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


def _refine_step_size(current_step: float, scenario_step: float | None) -> float:
    current_numeric = float(current_step)
    if scenario_step is None or scenario_step <= 0:
        return current_numeric
    return min(current_numeric, float(scenario_step))


def _infer_duration(
    matching: MatchingResult,
    scenario_window: Mapping[str, Any] | None = None,
    mbse_context: MBSEContext | None = None,
) -> float:
    candidates: List[float] = []

    if isinstance(scenario_window, Mapping):
        sw_stop = scenario_window.get("stop_time")
        sw_start = scenario_window.get("start_time", 0.0)
        if isinstance(sw_stop, (int, float)) and float(sw_stop) > 0:
            sw_dur = float(sw_stop) - (float(sw_start) if isinstance(sw_start, (int, float)) else 0.0)
            if sw_dur > 0:
                candidates.append(sw_dur)

    regimes = [task.operating_regime for task in matching.task_set.tasks if task.operating_regime is not None]
    for regime in regimes:
        if regime and regime.end_time is not None and regime.end_time > 0:
            regime_dur = float(regime.end_time - (regime.start_time or 0.0)) or float(regime.end_time)
            if regime_dur > 0:
                candidates.append(regime_dur)

    _TIME_PATTERN = re.compile(r"(?:after_t|at\s+t|during_t=\[)[=\s]*([\d.]+)s?(?:\s*,\s*([\d.]+)s?\])?")
    for task in matching.task_set.tasks:
        for criterion in (task.acceptance_criteria or []):
            metric = str(getattr(criterion, "metric", "") or "")
            for m in _TIME_PATTERN.finditer(metric):
                for group_val in (m.group(1), m.group(2)):
                    if group_val:
                        try:
                            t_val = float(group_val)
                            if t_val > 0:
                                candidates.append(t_val * 1.2)
                        except (TypeError, ValueError):
                            pass

    for fmu in matching.selected_fmus:
        default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
        if isinstance(default, dict):
            stop = default.get("stopTime")
            start = default.get("startTime", 0.0)
            if isinstance(stop, (int, float)) and float(stop) > float(start):
                candidates.append(float(stop) - float(start))

    return max(candidates) if candidates else 1.0


def _cap_base_tick_for_execution(
    base_tick: float,
    duration: float,
    *,
    matching: MatchingResult,
    mbse_context: MBSEContext,
) -> Tuple[float, List[str]]:
    if base_tick <= 0 or duration <= 0:
        return base_tick, []
    if str(mbse_context.metadata.get("source_type") or "") != "benchmark_single_fmu_case":
        return base_tick, []
    if len(matching.selected_fmus) != 1 or matching.graph.bindings:
        return base_tick, []
    communication_points = int(round(duration / base_tick)) + 1
    if communication_points <= _MAX_EXECUTION_COMMUNICATION_POINTS:
        return base_tick, []
    capped_tick = max(base_tick, float(duration) / float(_MAX_EXECUTION_COMMUNICATION_POINTS - 1))
    return capped_tick, [
        f"capped_communication_points={communication_points}->{_MAX_EXECUTION_COMMUNICATION_POINTS}",
        f"capped_base_tick={base_tick}->{capped_tick}",
    ]


def _adapter_output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "generated_adapters"


def _adapter_to_runtime_fmu(adapter, *, step_size: float) -> FMU:
    input_specs = list(((adapter.io_contract or {}).get("inputs") or []))
    output_specs = list(((adapter.io_contract or {}).get("outputs") or []))
    if not input_specs:
        input_specs = [{"name": "input"}]
    if not output_specs:
        output_specs = [{"name": "output"}]
    ports: List[PortMeta] = []
    for input_spec in input_specs:
        input_meta = dict(input_spec.get("port_meta") or {})
        ports.append(
            PortMeta(
                name=str(input_spec.get("name") or "input"),
                causality="input",
                type=str(input_spec.get("dtype") or input_meta.get("type") or "Real"),
                unit=str(input_spec.get("unit") or input_meta.get("unit") or ""),
                dimensions=[int(item) for item in list(input_spec.get("dimensions") or input_meta.get("dimensions") or [])],
                description=f"Adapter inbound port for {adapter.source}",
            )
        )
    for output_spec in output_specs:
        output_meta = dict(output_spec.get("port_meta") or {})
        ports.append(
            PortMeta(
                name=str(output_spec.get("name") or "output"),
                causality="output",
                type=str(output_spec.get("dtype") or output_meta.get("type") or "Real"),
                unit=str(output_spec.get("unit") or output_meta.get("unit") or ""),
                dimensions=[int(item) for item in list(output_spec.get("dimensions") or output_meta.get("dimensions") or [])],
                description=f"Adapter outbound port for {adapter.target}",
            )
        )
    return FMU(
        uid=adapter.inserted_node_id or adapter.adapter_id,
        name=adapter.adapter_id,
        description=f"Generated adapter for {adapter.source} -> {adapter.target}",
        path=adapter.artifact_path or None,
        fmi_version="2.0",
        fmi_types=["CoSimulation"] if adapter.artifact_kind == "proxy_fmu" else [],
        ports=ports,
        inputs=[port.name for port in ports if port.causality == "input"],
        outputs=[port.name for port in ports if port.causality == "output"],
        tags=["generated_adapter", adapter.kind],
        capabilities=FMUCapabilities(
            can_handle_variable_communication_step_size=True,
            fixed_internal_step_size=float(step_size),
        ),
        meta={
            "generated_adapter": True,
            "adapter_id": adapter.adapter_id,
            "transform": dict(adapter.transform),
            "io_contract": dict(adapter.io_contract),
            "default_experiment": {"stepSize": float(step_size), "stopTime": 0.0},
        },
    )


def compose(
    matching: MatchingResult,
    *,
    mbse_context: MBSEContext,
    scenario_window: Mapping[str, Any] | None = None,
) -> CompositionResult:
    if not matching.selected_fmus:
        raise ValueError("compose() received empty selected_fmus")

    discrepancy_map = {
        (item.source_fmu, item.source_signal, item.target_fmu, item.target_signal): item
        for item in matching.discrepancy_set
    }
    fmu_by_uid = {fmu.uid: fmu for fmu in matching.selected_fmus}
    adapters = []
    for binding in matching.graph.bindings:
        key = (binding.source_fmu, binding.source_signal, binding.target_fmu, binding.target_signal)
        discrepancy = discrepancy_map.get(key)
        if discrepancy is None:
            continue
        adapter = synthesize_adapter_spec(
            discrepancy,
            binding,
            fmu_by_uid[binding.source_fmu],
            fmu_by_uid[binding.target_fmu],
            mbse_context,
        )
        adapters.append(materialize_adapter_artifact(adapter, out_dir=_adapter_output_dir()))

    graph_augmented, connection_records = rewrite_graph_with_adapters(matching.graph, adapters)
    base_tick_result = build_base_tick(matching.selected_fmus)
    duration = _infer_duration(matching, scenario_window=scenario_window, mbse_context=mbse_context)
    scenario_step = _scenario_step_size(scenario_window)
    base_tick_warnings = list(base_tick_result["warnings"])
    if scenario_step is not None:
        refined_base_tick = _refine_step_size(float(base_tick_result["base_tick"]), scenario_step)
        if abs(float(base_tick_result["base_tick"]) - refined_base_tick) > 1e-12:
            base_tick_warnings.append(
                f"scenario_step_size_refine={base_tick_result['base_tick']}->{refined_base_tick}"
            )
        base_tick_result["base_tick"] = refined_base_tick
    base_tick, cap_warnings = _cap_base_tick_for_execution(
        float(base_tick_result["base_tick"]),
        duration,
        matching=matching,
        mbse_context=mbse_context,
    )
    if scenario_step is not None:
        per_node_period: Dict[str, float] = {}
        fmu_by_uid = {fmu.uid: fmu for fmu in matching.selected_fmus}
        for uid, step in base_tick_result["fmu_steps"].items():
            fmu = fmu_by_uid.get(uid)
            step_numeric = float(step)
            if fmu is None:
                per_node_period[uid] = max(_refine_step_size(step_numeric, scenario_step), base_tick)
                continue
            fixed_step = fmu.capabilities.fixed_internal_step_size
            if fixed_step is not None:
                try:
                    fixed_numeric = float(fixed_step)
                except (TypeError, ValueError):
                    fixed_numeric = 0.0
                if fixed_numeric > 0:
                    per_node_period[uid] = max(_refine_step_size(step_numeric, scenario_step), fixed_numeric, base_tick)
                    continue
            if not fmu.capabilities.can_handle_variable_communication_step_size:
                per_node_period[uid] = max(step_numeric, base_tick)
                continue
            per_node_period[uid] = max(_refine_step_size(step_numeric, scenario_step), base_tick)
    else:
        per_node_period = {uid: max(float(step), base_tick) for uid, step in base_tick_result["fmu_steps"].items()}
    for adapter in adapters:
        per_node_period[adapter.inserted_node_id] = base_tick
    per_edge_hold_policy = attach_zoh_policy(graph_augmented.bindings, per_node_period)
    loop_components = detect_scc_loops(graph_augmented)
    preferred_execution_order = derive_execution_order(
        selected_fmus=matching.selected_fmus,
        selected_task_set=matching.task_set,
    )
    loop_wrappers = build_gauss_seidel_wrapper_specs(
        loop_components,
        graph_augmented,
        preferred_order=preferred_execution_order,
    )
    communication_grid: List[float] = []
    per_node_schedule: Dict[str, List[float]] = {}
    execution_plan: List[Dict[str, object]] = []
    materialized_schedule = should_materialize_schedule(base_tick, duration)
    if materialized_schedule:
        communication_grid = build_communication_grid(base_tick, duration)
        per_node_schedule = build_per_node_schedule(per_node_period, communication_grid)
        execution_plan = build_execution_plan(communication_grid, per_node_schedule, loop_wrappers)
    schedule = build_compact_schedule_descriptor(
        base_tick=base_tick,
        duration=duration,
        per_node_period=per_node_period,
        per_edge_hold_policy=per_edge_hold_policy,
        loop_wrappers=loop_wrappers,
        warnings=[*base_tick_warnings, *cap_warnings],
        base_tick_method=str(base_tick_result["method"]),
        materialized=materialized_schedule,
        communication_grid=communication_grid,
        per_node_schedule=per_node_schedule,
        execution_plan=execution_plan,
    )
    schedule["fmu_steps"] = dict(per_node_period)
    runtime_fmus = list(matching.selected_fmus) + [
        _adapter_to_runtime_fmu(adapter, step_size=float(base_tick_result["base_tick"]))
        for adapter in adapters
    ]
    meta = {
        "selected_task_set": asdict(matching.task_set),
        "graph": asdict(matching.graph),
        "graph_augmented": asdict(graph_augmented),
        "discrepancy_set": [asdict(item) for item in matching.discrepancy_set],
        "adapters": [asdict(adapter) for adapter in adapters],
        "runtime_fmus": [fmu.uid for fmu in runtime_fmus],
        "mbse_system": mbse_context.system_name,
        "trace_index": {
            "chain_ids": sorted({item.chain_id for item in matching.discrepancy_set if item.chain_id}),
            "discrepancy_segments": [item.segment_id for item in matching.discrepancy_set if item.segment_id],
        },
    }
    simulation_config = build_multi_rate_config(
        fmus=runtime_fmus,
        base_tick=base_tick,
        duration=duration,
        connections=connection_records,
        communication_grid=communication_grid,
        per_node_period=per_node_period,
        per_node_schedule=per_node_schedule,
        per_edge_hold_policy=per_edge_hold_policy,
        loop_wrappers=loop_wrappers,
        scheduler_meta={
            "materialized": materialized_schedule,
            "warnings": [*base_tick_warnings, *cap_warnings],
            "base_tick_method": base_tick_result["method"],
            "execution_plan": execution_plan,
            "async_edges": [item for item in per_edge_hold_policy if item.get("async")],
            "start_time": 0.0,
            "stop_time": duration,
            "communication_point_count": schedule["communication_point_count"],
        },
        meta=meta,
    )
    validation = validate_config(simulation_config)
    return CompositionResult(
        graph_augmented=graph_augmented,
        adapters=adapters,
        schedule=schedule,
        loop_resolution=loop_wrappers,
        simulation_config=simulation_config,
        diagnostics={
            "adapter_count": len(adapters),
            "loop_count": len(loop_wrappers),
            "validation_issues": validation.issues,
        },
    )
