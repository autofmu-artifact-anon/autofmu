"""Validation checks for Stage 3 outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pipeline.types import SimulationConfig


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: List[str]


def validate_config(cfg: SimulationConfig) -> ValidationResult:
    issues: List[str] = []
    if cfg.step_size <= 0:
        issues.append("step_size<=0")
    if cfg.duration <= 0:
        issues.append("duration<=0")
    if not cfg.fmus:
        issues.append("no_fmus")

    scheduler = cfg.scheduler if isinstance(cfg.scheduler, dict) else {}
    if scheduler.get("kind") == "multi_rate":
        materialized = bool(scheduler.get("materialized", True))
        if materialized:
            if not isinstance(scheduler.get("communication_grid"), list) or not scheduler.get("communication_grid"):
                issues.append("missing_communication_grid")
            if not isinstance(scheduler.get("per_node_schedule"), dict):
                issues.append("missing_per_node_schedule")
            if not isinstance(scheduler.get("execution_plan"), list):
                issues.append("missing_execution_plan")
        else:
            if float(scheduler.get("base_tick", 0.0) or 0.0) <= 0.0:
                issues.append("missing_base_tick")
            if int(scheduler.get("communication_point_count", 0) or 0) <= 0:
                issues.append("missing_communication_point_count")
        if not isinstance(scheduler.get("per_node_period"), dict):
            issues.append("missing_per_node_period")
        if not isinstance(scheduler.get("per_edge_hold_policy"), list):
            issues.append("missing_per_edge_hold_policy")
        if not isinstance(scheduler.get("loop_wrappers"), list):
            issues.append("missing_loop_wrappers")

    known_nodes = {fmu.uid for fmu in cfg.fmus}
    for adapter in (cfg.meta or {}).get("adapters", []):
        adapter_id = (adapter.get("inserted_node_id") or adapter.get("adapter_id")) if isinstance(adapter, dict) else None
        if isinstance(adapter_id, str) and adapter_id:
            known_nodes.add(adapter_id)

    for connection in cfg.connections:
        src = connection.get("source")
        dst = connection.get("target")
        if not isinstance(src, str) or "." not in src:
            issues.append(f"invalid_source={src}")
            continue
        if not isinstance(dst, str) or "." not in dst:
            issues.append(f"invalid_target={dst}")
            continue
        src_node = src.split(".", 1)[0]
        dst_node = dst.split(".", 1)[0]
        if src_node not in known_nodes:
            issues.append(f"unknown_source_node={src_node}")
        if dst_node not in known_nodes:
            issues.append(f"unknown_target_node={dst_node}")
        if src_node == dst_node:
            issues.append(f"intra_node_edge={src_node}")
    return ValidationResult(ok=not issues, issues=issues)
