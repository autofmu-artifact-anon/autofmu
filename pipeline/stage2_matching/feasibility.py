"""Feasibility helpers for Stage 2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from pipeline.types import BindingCandidate, ChainSegment, FMU, MBSEContext, PortMeta, TaskSet, VerificationTask

from .scoring import rank_port_candidates, tokenize


def _compact_name(text: str) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


_GENERIC_PORT_NAMES = frozenset({"input", "inputs", "output", "outputs"})


def _is_generic_port_name(text: str) -> bool:
    return str(text or "").strip().lower() in _GENERIC_PORT_NAMES


def output_ports(fmu: FMU) -> List[PortMeta]:
    return [port for port in fmu.ports if port.causality == "output"] or [PortMeta(name=name, causality="output") for name in fmu.outputs]


def input_ports(fmu: FMU) -> List[PortMeta]:
    return [port for port in fmu.ports if port.causality == "input"] or [PortMeta(name=name, causality="input") for name in fmu.inputs]


def has_topology_edge(mbse_context: MBSEContext, source_component: str, target_component: str) -> bool:
    if not mbse_context.adjacency:
        return True
    return target_component in mbse_context.adjacency.get(source_component, [])


def check_signal_support(task: VerificationTask, fmu: FMU) -> bool:
    required = {spec.signal_name for spec in task.signal_specs if spec.signal_name} or {signal for signal in task.required_signals if signal}
    available = _available_port_names(fmu)
    if not required:
        return True
    required_exact = {signal for signal in required if signal and not _is_generic_port_name(signal)}
    available_exact = {signal for signal in available if signal and not _is_generic_port_name(signal)}
    if not required_exact:
        if required & available:
            return True
        required_tokens = {token for signal in required for token in tokenize(signal)}
        available_tokens = {token for signal in available for token in tokenize(signal)}
        return bool(required_tokens & available_tokens)

    available_compact = {_compact_name(signal) for signal in available_exact}
    for signal_name in required_exact:
        compact_signal = _compact_name(signal_name)
        if signal_name in available_exact or (compact_signal and compact_signal in available_compact):
            return True
        if "[" in signal_name and "]" in signal_name:
            continue
        signal_tokens = tokenize(signal_name)
        if signal_tokens and any(signal_tokens & tokenize(candidate) for candidate in available_exact):
            return True
    if required_exact & available_exact:
        return True
    return False


def check_component_role_compatibility(task: VerificationTask, fmu: FMU) -> bool:
    if not task.grounded_components and not task.grounded_component_types:
        return True
    grounded_tokens = {
        token
        for value in list(task.grounded_components) + list(task.grounded_component_types)
        for token in tokenize(value)
    }
    fmu_tokens = tokenize(fmu.name) | tokenize(fmu.description) | {token for tag in fmu.tags for token in tokenize(tag)}
    fmu_tokens |= {token for port_name in _available_port_names(fmu) for token in tokenize(port_name)}
    return bool(grounded_tokens & fmu_tokens) or check_signal_support(task, fmu)


def check_topology_predicate(task: VerificationTask, fmu: FMU, mbse_context: MBSEContext, taskset_context: TaskSet) -> bool:
    roles = _task_role_hints(task, taskset_context)
    if not roles:
        if not (task.grounded_components or task.required_signals):
            return False
        if not task.grounded_components or not mbse_context.connections:
            return True
        task_components = set(task.grounded_components)
        return any(
            connection.source_component in task_components or connection.target_component in task_components
            for connection in mbse_context.connections
        )
    available_outputs = {port.name for port in output_ports(fmu)}
    available_inputs = {port.name for port in input_ports(fmu)}
    output_tokens = {token for name in available_outputs for token in tokenize(name)}
    input_tokens = {token for name in available_inputs for token in tokenize(name)}
    output_compact = {_compact_name(name) for name in available_outputs}
    input_compact = {_compact_name(name) for name in available_inputs}
    role_hits: List[bool] = []
    for role, signal_name in roles:
        signal_tokens = tokenize(signal_name)
        signal_compact = _compact_name(signal_name)
        if role == "source" and available_outputs and (
            not signal_name
            or signal_name in available_outputs
            or signal_tokens & output_tokens
            or (signal_compact and signal_compact in output_compact)
        ):
            role_hits.append(True)
            continue
        if role == "target" and available_inputs and (
            not signal_name
            or signal_name in available_inputs
            or signal_tokens & input_tokens
            or (signal_compact and signal_compact in input_compact)
        ):
            role_hits.append(True)
            continue
        role_hits.append(False)
    if not any(role_hits):
        return False
    if not task.grounded_components or not mbse_context.connections:
        return True
    task_components = set(task.grounded_components)
    return any(
        (
            connection.source_component in task_components
            and has_topology_edge(mbse_context, connection.source_component, connection.target_component)
        )
        or (
            connection.target_component in task_components
            and has_topology_edge(mbse_context, connection.source_component, connection.target_component)
        )
        for connection in mbse_context.connections
    )


def check_fmi_contract_feasibility(task: VerificationTask, fmu: FMU) -> bool:
    # Stage 2 performs structural matching only. FMUs that need an execution tool
    # are still valid composition candidates as long as their FMI I/O contract fits.
    if not fmu.ports and not fmu.inputs and not fmu.outputs:
        return not bool(task.required_signals or task.signal_specs)
    directions = {(spec.direction or "").lower() for spec in task.signal_specs if spec.direction}
    if any(direction in {"out", "output"} for direction in directions) and not output_ports(fmu):
        return False
    if any(direction in {"in", "input"} for direction in directions) and not input_ports(fmu):
        return False
    return True


def explain_assignment_mask(task: VerificationTask, fmu: FMU, *, mbse_context: MBSEContext, taskset_context: TaskSet) -> Dict[str, Any]:
    checks = {
        "signal_support": check_signal_support(task, fmu),
        "component_role_compatibility": check_component_role_compatibility(task, fmu),
        "topology_predicate": check_topology_predicate(task, fmu, mbse_context, taskset_context),
        "fmi_contract_feasibility": check_fmi_contract_feasibility(task, fmu),
    }
    reasons = [name for name, ok in checks.items() if not ok]
    return {
        "mask_value": 0.0 if all(checks.values()) else float("inf"),
        "checks": checks,
        "reasons": reasons,
    }


def assignment_mask_value(
    task: VerificationTask,
    fmu: FMU,
    *,
    mbse_context: MBSEContext,
    taskset_context: TaskSet,
) -> float:
    return float(explain_assignment_mask(task, fmu, mbse_context=mbse_context, taskset_context=taskset_context)["mask_value"])


def resolve_port_binding(
    *,
    segment: ChainSegment,
    source_fmu: FMU,
    target_fmu: FMU,
    max_candidates: int,
    topology_ok: bool,
) -> List[BindingCandidate]:
    outputs = output_ports(source_fmu)
    inputs = input_ports(target_fmu)
    source_rank = {name: score for name, score in rank_port_candidates(segment.source_signal, [port.name for port in outputs])}
    target_rank = {name: score for name, score in rank_port_candidates(segment.target_signal, [port.name for port in inputs])}
    pairs: List[BindingCandidate] = []
    for output_port in outputs:
        for input_port in inputs:
            causal_ok = output_port.causality == "output" and input_port.causality == "input"
            if not causal_ok:
                continue
            score_breakdown = score_binding_candidate(segment, output_port, input_port)
            discrepancy_kind = classify_discrepancy(output_port, input_port)
            discrepancy_profile = describe_discrepancy(output_port, input_port, discrepancy_kind)
            preservation_probe = BindingCandidate(
                source_port=output_port,
                target_port=input_port,
                score=float(score_breakdown["total"]),
                chain_id="",
                segment_id=segment.segment_id,
                score_breakdown=score_breakdown,
                causality_ok=causal_ok,
                topology_ok=bool(topology_ok),
                preserves_signal_path=False,
                routeable=False,
                discrepancy_kind=discrepancy_kind,
                discrepancy_details={},
                reasons=[f"source_signal={segment.source_signal}", f"target_signal={segment.target_signal}"],
            )
            preservation_evidence = signal_path_preservation_evidence(segment, preservation_probe)
            preserves = bool(preservation_evidence["preserves"])
            route_blockers = _route_blockers(
                causality_ok=causal_ok,
                topology_ok=bool(topology_ok),
                preserves_signal_path=preserves,
            )
            routeable = len(route_blockers) == 0
            route_decision = "reject"
            route_status = "blocked"
            if routeable and discrepancy_kind:
                route_decision = "defer_to_middleware"
                route_status = "routeable_deferred_discrepancy"
            elif routeable:
                route_decision = "bind_direct"
                route_status = "routeable_exact"
            candidate = BindingCandidate(
                source_port=output_port,
                target_port=input_port,
                score=float(score_breakdown["total"]),
                chain_id="",
                segment_id=segment.segment_id,
                score_breakdown=score_breakdown,
                causality_ok=causal_ok,
                topology_ok=bool(topology_ok),
                preserves_signal_path=False,
                routeable=False,
                discrepancy_kind=discrepancy_kind,
                discrepancy_details={
                    "source_port_type": output_port.type,
                    "target_port_type": input_port.type,
                    "source_unit": output_port.unit,
                    "target_unit": input_port.unit,
                    "source_dimensions": list(output_port.dimensions),
                    "target_dimensions": list(input_port.dimensions),
                    "source_signal_rank": float(source_rank.get(output_port.name, 0.0)),
                    "target_signal_rank": float(target_rank.get(input_port.name, 0.0)),
                    "deferred_discrepancy": bool(discrepancy_kind and routeable),
                    "deferred_discrepancy_kind": discrepancy_kind if routeable else None,
                    "discrepancy_axes": list(discrepancy_profile["axes"]),
                    "discrepancy_classification": discrepancy_profile,
                    "route_blockers": route_blockers,
                    "route_status": route_status,
                    "route_decision": route_decision,
                    "hard_failure_kind": None if routeable else "routing_failure",
                    "preservation_evidence": preservation_evidence,
                    "preserves_signal_path": preserves,
                },
                reasons=[f"source_signal={segment.source_signal}", f"target_signal={segment.target_signal}"],
            )
            pairs.append(
                BindingCandidate(
                    source_port=candidate.source_port,
                    target_port=candidate.target_port,
                    score=candidate.score,
                    chain_id=candidate.chain_id,
                    segment_id=candidate.segment_id,
                    score_breakdown=candidate.score_breakdown,
                    causality_ok=candidate.causality_ok,
                    topology_ok=candidate.topology_ok,
                    preserves_signal_path=preserves,
                    routeable=routeable,
                    discrepancy_kind=candidate.discrepancy_kind,
                    discrepancy_details=dict(candidate.discrepancy_details),
                    reasons=list(candidate.reasons)
                    + [f"route_status={route_status}", f"route_decision={route_decision}"]
                    + list(preservation_evidence.get("reasons") or []),
                )
            )
    pairs.sort(
        key=lambda item: (
            -int(item.routeable),
            -int(item.preserves_signal_path),
            -float(item.score),
            getattr(item.source_port, "name", ""),
            getattr(item.target_port, "name", ""),
        )
    )
    return pairs[: max(int(max_candidates), 1)]


def score_binding_candidate(segment: ChainSegment, source_port: PortMeta, target_port: PortMeta) -> Dict[str, float]:
    source_name = _rank_name(segment.source_signal, source_port.name)
    target_name = _rank_name(segment.target_signal, target_port.name)
    intent = _rank_name(segment.semantic_intent or f"{segment.source_signal} {segment.target_signal}", f"{source_port.name} {target_port.name}")
    unit_match = _compatibility_score((source_port.unit or "").strip().lower(), (target_port.unit or "").strip().lower())
    type_match = _compatibility_score((source_port.type or "").strip().lower(), (target_port.type or "").strip().lower())
    total = 0.42 * source_name + 0.42 * target_name + 0.08 * intent + 0.04 * unit_match + 0.04 * type_match
    return {
        "source_name": float(source_name),
        "target_name": float(target_name),
        "intent": float(intent),
        "unit_match": float(unit_match),
        "type_match": float(type_match),
        "total": float(total),
    }


def preserves_signal_path(segment: ChainSegment, candidate: BindingCandidate) -> bool:
    return bool(signal_path_preservation_evidence(segment, candidate)["preserves"])


def signal_path_preservation_evidence(segment: ChainSegment, candidate: BindingCandidate) -> Dict[str, Any]:
    source_name = float(candidate.score_breakdown.get("source_name", 0.0))
    target_name = float(candidate.score_breakdown.get("target_name", 0.0))
    intent = float(candidate.score_breakdown.get("intent", 0.0))
    source_signal = (segment.source_signal or "").strip().lower()
    target_signal = (segment.target_signal or "").strip().lower()
    source_port_name = (candidate.source_port.name or "").strip().lower()
    target_port_name = (candidate.target_port.name or "").strip().lower()
    exact_source = bool(source_signal) and source_signal == source_port_name
    exact_target = bool(target_signal) and target_signal == target_port_name
    source_overlap = sorted(tokenize(segment.source_signal) & tokenize(candidate.source_port.name))
    target_overlap = sorted(tokenize(segment.target_signal) & tokenize(candidate.target_port.name))
    preserves = bool(
        candidate.causality_ok
        and candidate.topology_ok
        and ((source_name >= 0.15 and target_name >= 0.15) or exact_source or exact_target or intent >= 0.35)
    )
    reasons: List[str] = []
    if exact_source:
        reasons.append("exact_source_signal_match")
    if exact_target:
        reasons.append("exact_target_signal_match")
    if source_overlap:
        reasons.append("source_token_overlap")
    if target_overlap:
        reasons.append("target_token_overlap")
    if intent >= 0.35:
        reasons.append("semantic_intent_support")
    if not candidate.causality_ok:
        reasons.append("causality_mismatch")
    if not candidate.topology_ok:
        reasons.append("topology_violation")
    if not preserves:
        reasons.append("insufficient_signal_path_evidence")
    return {
        "preserves": preserves,
        "decision": "preserve" if preserves else "reject",
        "causality_ok": bool(candidate.causality_ok),
        "topology_ok": bool(candidate.topology_ok),
        "source_name_score": source_name,
        "target_name_score": target_name,
        "intent_score": intent,
        "source_token_overlap": source_overlap,
        "target_token_overlap": target_overlap,
        "exact_source_match": exact_source,
        "exact_target_match": exact_target,
        "reasons": reasons,
    }


def classify_discrepancy(source_port: PortMeta, target_port: PortMeta) -> Optional[str]:
    src_type = (source_port.type or "").lower()
    dst_type = (target_port.type or "").lower()
    src_unit = (source_port.unit or "").strip().lower()
    dst_unit = (target_port.unit or "").strip().lower()
    src_dimensions = list(source_port.dimensions or [])
    dst_dimensions = list(target_port.dimensions or [])

    if (src_dimensions or dst_dimensions) and src_dimensions != dst_dimensions:
        return "dimension_adapter"

    if src_type and dst_type and src_type != dst_type:
        if {src_type, dst_type} <= {"real", "integer", "boolean"}:
            return "mode_signal_adapter"
        return "type_adapter"

    if src_unit and dst_unit and src_unit != dst_unit:
        return "unit_transform_adapter"

    return None


def describe_discrepancy(source_port: PortMeta, target_port: PortMeta, discrepancy_kind: Optional[str]) -> Dict[str, Any]:
    src_type = (source_port.type or "").lower()
    dst_type = (target_port.type or "").lower()
    src_unit = (source_port.unit or "").strip().lower()
    dst_unit = (target_port.unit or "").strip().lower()
    src_dimensions = list(source_port.dimensions or [])
    dst_dimensions = list(target_port.dimensions or [])
    axes: List[str] = []
    if (src_dimensions or dst_dimensions) and src_dimensions != dst_dimensions:
        axes.append("dimensions")
    if src_type and dst_type and src_type != dst_type:
        axes.append("type")
    if src_unit and dst_unit and src_unit != dst_unit:
        axes.append("unit")
    return {
        "kind": discrepancy_kind,
        "axes": axes,
        "requires_middleware": bool(discrepancy_kind),
        "source_type": source_port.type,
        "target_type": target_port.type,
        "source_unit": source_port.unit,
        "target_unit": target_port.unit,
        "source_dimensions": src_dimensions,
        "target_dimensions": dst_dimensions,
    }


def _route_blockers(*, causality_ok: bool, topology_ok: bool, preserves_signal_path: bool) -> List[str]:
    blockers: List[str] = []
    if not causality_ok:
        blockers.append("causality")
    if not topology_ok:
        blockers.append("topology")
    if not preserves_signal_path:
        blockers.append("signal_path")
    return blockers


def _available_port_names(fmu: FMU) -> set[str]:
    return {port.name for port in fmu.ports} | set(fmu.inputs) | set(fmu.outputs)


def _task_role_hints(task: VerificationTask, taskset_context: TaskSet) -> List[tuple[str, str]]:
    hints: List[tuple[str, str]] = []
    task_components = set(task.grounded_components)
    task_signals = set(task.required_signals)
    for chain in taskset_context.required_signal_chains:
        for segment in chain.segments:
            if task_components:
                if segment.source_component in task_components:
                    hints.append(("source", segment.source_signal))
                if segment.target_component in task_components:
                    hints.append(("target", segment.target_signal))
                continue
            if segment.source_signal in task_signals:
                hints.append(("source", segment.source_signal))
            if segment.target_signal in task_signals:
                hints.append(("target", segment.target_signal))
    if hints:
        return hints
    for spec in task.signal_specs:
        direction = (spec.direction or "").lower()
        if direction in {"out", "output"}:
            hints.append(("source", spec.signal_name))
        elif direction in {"in", "input"}:
            hints.append(("target", spec.signal_name))
    return hints


def _rank_name(left: str, right: str) -> float:
    if not left and not right:
        return 0.0
    if left.strip().lower() == right.strip().lower():
        return 1.0
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return float(len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1))


def _compatibility_score(left: str, right: str) -> float:
    if not left or not right:
        return 1.0
    return 1.0 if left == right else 0.25
