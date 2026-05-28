from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional

from dataset.common import normalize_signal_name
from pipeline.types import CompositionResult, MatchingResult, TaskSet


def _norm(text: Any) -> str:
    value = str(text or "").strip()
    return normalize_signal_name(value) if value else ""


def _sorted_unique(values: Iterable[str]) -> List[str]:
    return sorted({value for value in values if value})


def _connection_key(item: Any) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    source = item.get("source") or item.get("from")
    target = item.get("target") or item.get("to")
    if not isinstance(source, str) or not isinstance(target, str):
        return None
    source_text = source.strip()
    target_text = target.strip()
    if not source_text or not target_text:
        return None
    return f"{source_text}->{target_text}"


def _signal_name(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    for key in ("name", "signal"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    source = item.get("source")
    if isinstance(source, str) and "." in source:
        return source.rsplit(".", 1)[-1].strip()
    return ""


def _schedule_summary(schedule: Any) -> Dict[str, Any]:
    if not isinstance(schedule, dict):
        return {}
    summary = {
        "kind": str(schedule.get("kind") or schedule.get("co_simulation_type") or "").strip(),
    }
    for key in ("step_size", "base_tick", "duration", "start_time", "stop_time"):
        value = schedule.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            summary[key] = float(value)
    return summary


def canonicalize_taskset(taskset: TaskSet) -> Dict[str, Any]:
    signals: List[str] = []
    components: List[str] = []
    constraints: List[str] = []
    inputs: List[str] = []
    time_windows: List[str] = []

    for task in taskset.tasks:
        signals.extend(_norm(item) for item in task.required_signals)
        signals.extend(_norm(spec.signal_name or spec.grounded_port_ref or spec.port_hint) for spec in task.signal_specs)
        components.extend(_norm(item) for item in task.grounded_components)
        for constraint in task.constraint_set:
            metric = _norm(constraint.grounded_signal or constraint.metric)
            operator = str(constraint.operator or "").strip()
            constraints.append(f"{metric}:{operator}" if metric or operator else "")
        regime = task.operating_regime
        if regime is not None:
            inputs.extend(_norm(name) for name in regime.inputs.keys())
            if regime.start_time is not None or regime.end_time is not None:
                start = "" if regime.start_time is None else str(float(regime.start_time))
                end = "" if regime.end_time is None else str(float(regime.end_time))
                time_windows.append(f"{start}:{end}")

    return {
        "task_set_id": taskset.task_set_id,
        "signals": _sorted_unique(signals),
        "components": _sorted_unique(components),
        "constraints": _sorted_unique(constraints),
        "inputs": _sorted_unique(inputs),
        "time_windows": _sorted_unique(time_windows),
    }


def canonicalize_matching(result: MatchingResult) -> Dict[str, Any]:
    return {
        "selected_asset_ids": sorted({str(fmu.uid) for fmu in result.selected_fmus if str(fmu.uid)}),
        "assignment_asset_ids": sorted({str(item.fmu_uid) for item in result.assignments if str(item.fmu_uid)}),
    }


def canonicalize_composition(result: CompositionResult) -> Dict[str, Any]:
    return {
        "connections": sorted(
            key for key in (_connection_key(item) for item in result.simulation_config.connections) if key is not None
        ),
        "schedule": _schedule_summary(result.schedule if isinstance(result.schedule, dict) else result.simulation_config.scheduler),
        "adapter_count": len(result.adapters),
    }


def canonicalize_solution(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "selected_asset_ids": sorted({str(item) for item in payload.get("selected_asset_ids", []) if str(item)}),
        "connections": sorted(
            key for key in (_connection_key(item) for item in payload.get("connections", [])) if key is not None
        ),
        "external_inputs": sorted(
            {_norm(_signal_name(item)) for item in payload.get("external_inputs", []) if _norm(_signal_name(item))}
        ),
        "monitored_outputs": sorted(
            {_norm(_signal_name(item)) for item in payload.get("monitored_outputs", []) if _norm(_signal_name(item))}
        ),
        "execution_order": [str(item) for item in payload.get("execution_order", []) if str(item)],
        "schedule": _schedule_summary(payload.get("schedule")),
    }
