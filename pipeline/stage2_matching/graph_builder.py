"""Graph instantiation helpers for Stage 2."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Sequence

from pipeline.types import (
    BindingCandidate,
    ChainSegment,
    DiscrepancyEdge,
    FMU,
    MBSEConnection,
    MBSEContext,
    OrchestrationGraph,
    PortBinding,
    RequiredSignalChain,
    TaskAssignment,
    TaskSet,
)

from .feasibility import has_topology_edge, resolve_port_binding


def build_required_signal_chains(taskset: TaskSet, mbse_context: MBSEContext) -> List[RequiredSignalChain]:
    if taskset.required_signal_chains:
        return list(taskset.required_signal_chains)
    if not mbse_context.connections:
        return []
    chains: List[RequiredSignalChain] = []
    for index, connection in enumerate(mbse_context.connections):
        origin_task_ids = [
            task.task_id
            for task in taskset.tasks
            if connection.source_component in task.grounded_components
            or connection.target_component in task.grounded_components
            or connection.source_signal in task.required_signals
            or connection.target_signal in task.required_signals
        ]
        chain_id = f"chain_{index}"
        chains.append(
            RequiredSignalChain(
                chain_id=chain_id,
                source_component=connection.source_component,
                target_component=connection.target_component,
                signals=[connection.source_signal, connection.target_signal],
                origin_task_ids=origin_task_ids,
                segments=[
                    ChainSegment(
                        segment_id=f"{chain_id}_seg_0",
                        source_component=connection.source_component,
                        source_signal=connection.source_signal,
                        target_component=connection.target_component,
                        target_signal=connection.target_signal,
                        semantic_intent=f"{connection.source_signal} -> {connection.target_signal}",
                        adjacency_evidence={
                            "source_component": connection.source_component,
                            "target_component": connection.target_component,
                        },
                    )
                ],
                semantic_intent=f"{connection.source_component}.{connection.source_signal} -> {connection.target_component}.{connection.target_signal}",
                details={
                    "source_signal": connection.source_signal,
                    "target_signal": connection.target_signal,
                    "fallback_chain": True,
                },
            )
        )
    return chains


def expand_chain_segments(chains: Sequence[RequiredSignalChain]) -> List[tuple[RequiredSignalChain, ChainSegment]]:
    expanded: List[tuple[RequiredSignalChain, ChainSegment]] = []
    for chain in chains:
        for segment in chain.segments:
            expanded.append((chain, segment))
    return expanded


def _compact_name(text: str) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def _expand_component_mapping(
    required_signal_chains: Sequence[RequiredSignalChain],
    component_to_fmu: Dict[str, str],
    assignments_by_component: Dict[str, TaskAssignment],
    assignments: Sequence[TaskAssignment],
    fmu_by_uid: Dict[str, FMU],
    mbse_context: MBSEContext,
) -> None:
    """Fill component_to_fmu for chain endpoints not covered by task grounding."""
    needed: List[str] = []
    for chain in required_signal_chains:
        for segment in chain.segments:
            for comp in (segment.source_component, segment.target_component):
                if comp and comp not in component_to_fmu and comp not in needed:
                    needed.append(comp)
    if not needed:
        return

    assigned_uids = {a.fmu_uid for a in assignments}
    assigned_fmus = [fmu_by_uid[uid] for uid in assigned_uids if uid in fmu_by_uid]
    mbse_comp_map = {c.name: c for c in mbse_context.components}

    for comp_name in needed:
        comp = mbse_comp_map.get(comp_name)
        comp_norm = _compact_name(comp_name)
        comp_type_norm = _compact_name(comp.component_type) if comp else ""
        comp_ports = set()
        if comp:
            comp_ports = {str(p.name).strip() for p in comp.ports if str(p.name).strip()}

        best_fmu: Optional[FMU] = None
        best_score = 0.0
        for fmu in assigned_fmus:
            score = 0.0
            uid_norm = _compact_name(fmu.uid)
            name_norm = _compact_name(fmu.name)
            if comp_norm and (comp_norm in uid_norm or comp_norm in name_norm):
                score += 4.0
            if comp_type_norm and (comp_type_norm in uid_norm or comp_type_norm in name_norm):
                score += 3.0
            if comp_ports:
                fmu_ports = {str(p.name).strip() for p in fmu.ports}
                overlap = len(comp_ports & fmu_ports)
                score += float(overlap)
            if score > best_score:
                best_score = score
                best_fmu = fmu

        if best_fmu is not None and best_score >= 1.0:
            component_to_fmu[comp_name] = best_fmu.uid
            ref_assignment = next(
                (a for a in assignments if a.fmu_uid == best_fmu.uid), None
            )
            if ref_assignment is not None:
                assignments_by_component[comp_name] = ref_assignment


def instantiate_port_graph(
    taskset: TaskSet,
    assignments: Sequence[TaskAssignment],
    mbse_context: MBSEContext,
    fmu_by_uid: Dict[str, FMU],
    max_port_candidates: int,
    *,
    ambiguity_resolver: Optional[Callable[[MBSEConnection, FMU, FMU, Sequence[BindingCandidate], MBSEContext], int]] = None,
) -> Dict[str, Any]:
    required_signal_chains = build_required_signal_chains(taskset, mbse_context)
    port_nodes = _collect_port_nodes(assignments, fmu_by_uid)
    component_to_fmu: Dict[str, str] = {}
    assignments_by_component: Dict[str, TaskAssignment] = {}
    closure_failures: List[Dict[str, Any]] = []
    binding_candidates: List[Dict[str, Any]] = []

    for assignment, task in zip(assignments, taskset.tasks):
        for component_name in task.grounded_components:
            current = component_to_fmu.get(component_name)
            if current is not None:
                continue
            component_to_fmu[component_name] = assignment.fmu_uid
            assignments_by_component[component_name] = assignment

    _expand_component_mapping(
        required_signal_chains,
        component_to_fmu,
        assignments_by_component,
        assignments,
        fmu_by_uid,
        mbse_context,
    )

    if not required_signal_chains:
        graph = OrchestrationGraph(
            nodes=sorted({assignment.fmu_uid for assignment in assignments}),
            port_nodes=port_nodes,
            bindings=[],
            component_to_fmu=component_to_fmu,
            required_signal_chains=required_signal_chains,
            binding_candidates=[],
            closure_ok=True,
            closure_failures=[],
            routing_failures=[],
            diagnostics={"status": "ok", "note": "no_required_signal_chains", "routing_failure_count": 0},
        )
        return {"graph": graph, "discrepancy_set": [], "closure_ok": True, "closure_failure": None}

    bindings: List[PortBinding] = []
    discrepancies: List[DiscrepancyEdge] = []
    for chain, segment in expand_chain_segments(required_signal_chains):
        routed = route_chain_segment(
            chain,
            segment,
            component_to_fmu=component_to_fmu,
            assignments_by_component=assignments_by_component,
            mbse_context=mbse_context,
            fmu_by_uid=fmu_by_uid,
            max_port_candidates=max_port_candidates,
            ambiguity_resolver=ambiguity_resolver,
        )
        binding_candidates.append(routed["binding_candidate_record"])
        if routed.get("skipped"):
            continue
        if routed["failure"] is not None:
            closure_failures.append(routed["failure"])
            return _failure_result(
                assignments=assignments,
                component_to_fmu=component_to_fmu,
                required_signal_chains=required_signal_chains,
                port_nodes=port_nodes,
                binding_candidates=binding_candidates,
                bindings=bindings,
                discrepancies=discrepancies,
                failure=routed["failure"],
            )
        bindings.append(routed["binding"])
        if routed["discrepancy"] is not None:
            discrepancies.append(routed["discrepancy"])

    graph = OrchestrationGraph(
        nodes=sorted({assignment.fmu_uid for assignment in assignments}),
        port_nodes=port_nodes,
        bindings=bindings,
        component_to_fmu=component_to_fmu,
        required_signal_chains=required_signal_chains,
        binding_candidates=binding_candidates,
        closure_ok=True,
        closure_failures=closure_failures,
        routing_failures=closure_failures,
        diagnostics={
            "status": "ok",
            "binding_count": len(bindings),
            "chain_count": len(required_signal_chains),
            "routing_failure_count": 0,
            "discrepancy_count": len(discrepancies),
        },
    )
    return {"graph": graph, "discrepancy_set": discrepancies, "closure_ok": True, "closure_failure": None}


def route_chain_segment(
    chain: RequiredSignalChain,
    segment: ChainSegment,
    *,
    component_to_fmu: Dict[str, str],
    assignments_by_component: Dict[str, TaskAssignment],
    mbse_context: MBSEContext,
    fmu_by_uid: Dict[str, FMU],
    max_port_candidates: int,
    ambiguity_resolver: Optional[Callable[[MBSEConnection, FMU, FMU, Sequence[BindingCandidate], MBSEContext], int]] = None,
) -> Dict[str, Any]:
    validation = _validate_segment_mapping(
        segment, component_to_fmu, assignments_by_component, mbse_context,
        fmu_by_uid=fmu_by_uid,
    )
    if validation == _INTRA_FMU_SKIP:
        return {
            "binding": None,
            "discrepancy": None,
            "failure": None,
            "skipped": True,
            "binding_candidate_record": _empty_candidate_record(chain, segment),
        }
    if validation is not None:
        return {
            "binding": None,
            "discrepancy": None,
            "failure": _with_chain_failure(validation, chain.chain_id, segment.segment_id),
            "binding_candidate_record": _empty_candidate_record(chain, segment),
        }

    source_fmu = fmu_by_uid[component_to_fmu[segment.source_component]]
    target_fmu = fmu_by_uid[component_to_fmu[segment.target_component]]
    topology_ok = has_topology_edge(mbse_context, segment.source_component, segment.target_component)
    candidates = [
        _with_chain_candidate(item, chain.chain_id)
        for item in resolve_port_binding(
            segment=segment,
            source_fmu=source_fmu,
            target_fmu=target_fmu,
            max_candidates=max_port_candidates,
            topology_ok=topology_ok,
        )
    ]
    routeable_candidates = [candidate for candidate in candidates if candidate.routeable]
    binding_candidate_record = {
        "chain_id": chain.chain_id,
        "segment_id": segment.segment_id,
        "semantic_intent": chain.semantic_intent or segment.semantic_intent,
        "source_component": segment.source_component,
        "target_component": segment.target_component,
        "source_fmu": source_fmu.uid,
        "target_fmu": target_fmu.uid,
        "candidates": [
            {
                "source_signal": candidate.source_port.name,
                "target_signal": candidate.target_port.name,
                "score": float(candidate.score),
                "score_breakdown": dict(candidate.score_breakdown),
                "preserves_signal_path": bool(candidate.preserves_signal_path),
                "routeable": bool(candidate.routeable),
                "route_status": str(candidate.discrepancy_details.get("route_status") or ("routeable" if candidate.routeable else "blocked")),
                "route_decision": str(candidate.discrepancy_details.get("route_decision") or ("bind_direct" if candidate.routeable else "reject")),
                "route_blockers": list(candidate.discrepancy_details.get("route_blockers") or []),
                "hard_failure_kind": candidate.discrepancy_details.get("hard_failure_kind"),
                "discrepancy_kind": candidate.discrepancy_kind,
                "deferred_discrepancy": bool(candidate.discrepancy_details.get("deferred_discrepancy")),
                "deferred_discrepancy_kind": candidate.discrepancy_details.get("deferred_discrepancy_kind"),
                "discrepancy_axes": list(candidate.discrepancy_details.get("discrepancy_axes") or []),
                "preservation_evidence": dict(candidate.discrepancy_details.get("preservation_evidence") or {}),
            }
            for candidate in candidates
        ],
    }
    if not routeable_candidates:
        blocker_histogram: Dict[str, int] = {}
        for candidate in candidates:
            for blocker in candidate.discrepancy_details.get("route_blockers") or []:
                blocker_histogram[blocker] = blocker_histogram.get(blocker, 0) + 1
        failure = {
            "failure_type": "unroutable_segment",
            "failure_class": "routing_failure",
            "eligible_for_mask_revision": True,
            "revision_action": "exclude_pair",
            "chain_id": chain.chain_id,
            "segment_id": segment.segment_id,
            "details": {
                "source_fmu": source_fmu.uid,
                "target_fmu": target_fmu.uid,
                "candidate_count": len(candidates),
                "routeable_candidate_count": len(routeable_candidates),
                "deferred_discrepancy_count": sum(
                    1 for candidate in candidates if bool(candidate.discrepancy_details.get("deferred_discrepancy"))
                ),
                "route_blocker_histogram": blocker_histogram,
                "best_candidate_score": max((float(candidate.score) for candidate in candidates), default=0.0),
                "candidate_diagnostics": [
                    {
                        "source_signal": candidate.source_port.name,
                        "target_signal": candidate.target_port.name,
                        "route_blockers": list(candidate.discrepancy_details.get("route_blockers") or []),
                        "route_decision": candidate.discrepancy_details.get("route_decision"),
                        "hard_failure_kind": candidate.discrepancy_details.get("hard_failure_kind"),
                        "preservation_evidence": dict(candidate.discrepancy_details.get("preservation_evidence") or {}),
                    }
                    for candidate in candidates[:3]
                ],
            },
            "responsible_pair": _choose_responsible_pair(segment, candidates, assignments_by_component),
        }
        return {
            "binding": None,
            "discrepancy": None,
            "failure": failure,
            "binding_candidate_record": binding_candidate_record,
        }

    selected_index = 0
    selected_by = "score"
    if ambiguity_resolver is not None and len(routeable_candidates) > 1 and abs(routeable_candidates[0].score - routeable_candidates[1].score) <= 1e-9:
        connection = MBSEConnection(
            source_component=segment.source_component,
            source_signal=segment.source_signal,
            target_component=segment.target_component,
            target_signal=segment.target_signal,
        )
        selected_index = max(0, min(int(ambiguity_resolver(connection, source_fmu, target_fmu, routeable_candidates, mbse_context)), len(routeable_candidates) - 1))
        selected_by = "llm_tiebreak"
    selected = routeable_candidates[selected_index]
    binding = PortBinding(
        source_fmu=source_fmu.uid,
        source_signal=selected.source_port.name,
        target_fmu=target_fmu.uid,
        target_signal=selected.target_port.name,
        score=float(selected.score),
        chain_id=chain.chain_id,
        segment_id=segment.segment_id,
        selected_by=selected_by,
        score_breakdown=dict(selected.score_breakdown),
        reasons=[f"mapped_from={segment.source_signal}->{segment.target_signal}"],
    )

    discrepancy = None
    if isinstance(selected.discrepancy_kind, str) and selected.discrepancy_kind:
        discrepancy = DiscrepancyEdge(
            source_fmu=source_fmu.uid,
            source_signal=selected.source_port.name,
            target_fmu=target_fmu.uid,
            target_signal=selected.target_port.name,
            kind=selected.discrepancy_kind,
            details={
                **dict(selected.discrepancy_details),
                "required_source_signal": segment.source_signal,
                "required_target_signal": segment.target_signal,
                "deferred_from_stage2": True,
            },
            chain_id=chain.chain_id,
            segment_id=segment.segment_id,
            preserves_signal_path=bool(selected.preserves_signal_path),
            preservation_evidence=dict(selected.discrepancy_details.get("preservation_evidence") or {}),
            source_port_meta=_port_meta_dict(selected.source_port),
            target_port_meta=_port_meta_dict(selected.target_port),
            local_mbse_context={
                "system_name": mbse_context.system_name,
                "source_component": segment.source_component,
                "target_component": segment.target_component,
                "semantic_intent": chain.semantic_intent or segment.semantic_intent,
                "topology_ok": topology_ok,
                "route_decision": selected.discrepancy_details.get("route_decision"),
            },
        )
    return {
        "binding": binding,
        "discrepancy": discrepancy,
        "failure": None,
        "binding_candidate_record": binding_candidate_record,
    }


def detect_graph_closure_failure(graph_result: Dict[str, Any]) -> Dict[str, Any] | None:
    failure = graph_result.get("closure_failure")
    return failure if isinstance(failure, dict) else None


_INTRA_FMU_SKIP = "intra_fmu_internal_routing"


def _validate_segment_mapping(
    segment: ChainSegment,
    component_to_fmu: Dict[str, str],
    assignments_by_component: Dict[str, TaskAssignment],
    mbse_context: MBSEContext,
    fmu_by_uid: Optional[Dict[str, FMU]] = None,
) -> Dict[str, Any] | str | None:
    """Return a failure dict, the sentinel ``_INTRA_FMU_SKIP``, or *None*."""
    src_fmu_uid = component_to_fmu.get(segment.source_component)
    dst_fmu_uid = component_to_fmu.get(segment.target_component)
    if not src_fmu_uid:
        assignment = assignments_by_component.get(segment.source_component)
        return {
            "failure_type": "missing_source_component_mapping",
            "failure_class": "routing_failure",
            "eligible_for_mask_revision": True,
            "revision_action": "exclude_pair",
            "details": {"source_component": segment.source_component},
            "responsible_pair": (assignment.task_index, assignment.fmu_uid) if assignment is not None else None,
        }
    if not dst_fmu_uid:
        assignment = assignments_by_component.get(segment.target_component)
        return {
            "failure_type": "missing_target_component_mapping",
            "failure_class": "routing_failure",
            "eligible_for_mask_revision": True,
            "revision_action": "exclude_pair",
            "details": {"target_component": segment.target_component},
            "responsible_pair": (assignment.task_index, assignment.fmu_uid) if assignment is not None else None,
        }
    if src_fmu_uid == dst_fmu_uid:
        if fmu_by_uid is not None:
            fmu = fmu_by_uid.get(src_fmu_uid)
            if fmu is not None:
                port_names = {str(p.name).strip() for p in getattr(fmu, "ports", [])}
                src_ok = segment.source_signal in port_names or any(
                    segment.source_signal.lower() == p.lower() for p in port_names
                )
                tgt_ok = segment.target_signal in port_names or any(
                    segment.target_signal.lower() == p.lower() for p in port_names
                )
                if src_ok and tgt_ok:
                    return _INTRA_FMU_SKIP
        assignment = assignments_by_component.get(segment.source_component) or assignments_by_component.get(segment.target_component)
        return {
            "failure_type": "intra_fmu_edge_forbidden",
            "failure_class": "routing_failure",
            "eligible_for_mask_revision": True,
            "revision_action": "exclude_pair",
            "details": {"fmu_uid": src_fmu_uid},
            "responsible_pair": (assignment.task_index, assignment.fmu_uid) if assignment is not None else None,
        }
    if not has_topology_edge(mbse_context, segment.source_component, segment.target_component):
        assignment = assignments_by_component.get(segment.source_component) or assignments_by_component.get(segment.target_component)
        return {
            "failure_type": "topology_disallows",
            "failure_class": "routing_failure",
            "eligible_for_mask_revision": True,
            "revision_action": "exclude_pair",
            "details": {
                "source_component": segment.source_component,
                "target_component": segment.target_component,
            },
            "responsible_pair": (assignment.task_index, assignment.fmu_uid) if assignment is not None else None,
        }
    return None


def _with_chain_candidate(candidate: BindingCandidate, chain_id: str) -> BindingCandidate:
    return BindingCandidate(
        source_port=candidate.source_port,
        target_port=candidate.target_port,
        score=candidate.score,
        chain_id=chain_id,
        segment_id=candidate.segment_id,
        score_breakdown=dict(candidate.score_breakdown),
        causality_ok=candidate.causality_ok,
        topology_ok=candidate.topology_ok,
        preserves_signal_path=candidate.preserves_signal_path,
        routeable=candidate.routeable,
        discrepancy_kind=candidate.discrepancy_kind,
        discrepancy_details=dict(candidate.discrepancy_details),
        reasons=list(candidate.reasons),
    )


def _with_chain_failure(failure: Dict[str, Any], chain_id: str, segment_id: str) -> Dict[str, Any]:
    return {
        **dict(failure),
        "chain_id": chain_id,
        "segment_id": segment_id,
    }


def _failure_result(
    *,
    assignments: Sequence[TaskAssignment],
    component_to_fmu: Dict[str, str],
    required_signal_chains: List[RequiredSignalChain],
    port_nodes: List[str],
    binding_candidates: List[Dict[str, Any]],
    bindings: List[PortBinding],
    discrepancies: List[DiscrepancyEdge],
    failure: Dict[str, Any],
) -> Dict[str, Any]:
    graph = OrchestrationGraph(
        nodes=sorted({assignment.fmu_uid for assignment in assignments}),
        port_nodes=port_nodes,
        bindings=bindings,
        component_to_fmu=component_to_fmu,
        required_signal_chains=required_signal_chains,
        binding_candidates=binding_candidates,
        closure_ok=False,
        closure_failures=[failure],
        routing_failures=[failure] if _is_routing_failure(failure) else [],
        diagnostics={"status": "failed", "routing_failure_count": 1 if _is_routing_failure(failure) else 0},
    )
    return {"graph": graph, "discrepancy_set": discrepancies, "closure_ok": False, "closure_failure": failure}


def _choose_responsible_pair(
    segment: ChainSegment,
    candidates: Sequence[BindingCandidate],
    assignments_by_component: Dict[str, TaskAssignment],
) -> tuple[int, str] | None:
    source_best = max((float(candidate.score_breakdown.get("source_name", 0.0)) for candidate in candidates), default=0.0)
    target_best = max((float(candidate.score_breakdown.get("target_name", 0.0)) for candidate in candidates), default=0.0)
    if source_best <= target_best:
        assignment = assignments_by_component.get(segment.source_component)
        if assignment is not None:
            return assignment.task_index, assignment.fmu_uid
    assignment = assignments_by_component.get(segment.target_component)
    if assignment is not None:
        return assignment.task_index, assignment.fmu_uid
    assignment = assignments_by_component.get(segment.source_component)
    return (assignment.task_index, assignment.fmu_uid) if assignment is not None else None


def _empty_candidate_record(chain: RequiredSignalChain, segment: ChainSegment) -> Dict[str, Any]:
    return {
        "chain_id": chain.chain_id,
        "segment_id": segment.segment_id,
        "semantic_intent": chain.semantic_intent or segment.semantic_intent,
        "source_component": segment.source_component,
        "target_component": segment.target_component,
        "route_blocker_histogram": {},
        "candidates": [],
    }


def _is_routing_failure(failure: Dict[str, Any]) -> bool:
    return str(failure.get("failure_class") or "") == "routing_failure"


def _port_meta_dict(port) -> Dict[str, Any]:
    return asdict(port)


def _collect_port_nodes(assignments: Sequence[TaskAssignment], fmu_by_uid: Dict[str, FMU]) -> List[str]:
    nodes: List[str] = []
    seen = set()
    for assignment in assignments:
        fmu = fmu_by_uid.get(assignment.fmu_uid)
        if fmu is None:
            continue
        for port in fmu.ports:
            node_id = f"{fmu.uid}.{port.name}"
            if node_id in seen:
                continue
            seen.add(node_id)
            nodes.append(node_id)
    return nodes
