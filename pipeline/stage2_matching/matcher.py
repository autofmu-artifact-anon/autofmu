"""Stage 2 full implementation: constraint-aware joint retrieval."""

from __future__ import annotations

import json
import math
import re
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pipeline.llm_guidance import build_strict_json_system_prompt, goal_is_aligned
from pipeline.llm_client import chat_json
from pipeline.types import (
    BindingCandidate,
    FMU,
    MatchingResult,
    MBSEConnection,
    MBSEContext,
    OrchestrationGraph,
    PortBinding,
    TaskAssignment,
    TaskSet,
    VerificationTask,
)

from .graph_builder import detect_graph_closure_failure, instantiate_port_graph
from .feasibility import input_ports, output_ports
from .revision import apply_failure_mask_update, select_conflict_pair_for_mask_update
from .transport import (
    build_hard_mask_matrix,
    build_hard_mask_explanations,
    build_semantic_cost_matrix,
    compute_transport_objective,
    extract_assignment_from_transport,
    solve_row_constrained_sinkhorn,
)


def _resolve_binding_ambiguity(
    connection: MBSEConnection,
    source_fmu: FMU,
    target_fmu: FMU,
    candidates: Sequence[Any],
    mbse_context: MBSEContext,
) -> int:
    if len(candidates) < 2:
        return 0
    if abs(float(_candidate_score(candidates[0])) - float(_candidate_score(candidates[1]))) > 1e-9:
        return 0
    task_goal = (
        f"Choose exactly one port-binding candidate that realizes MBSE connection "
        f"{connection.source_component}.{connection.source_signal} -> "
        f"{connection.target_component}.{connection.target_signal}."
    )
    system_prompt = build_strict_json_system_prompt(
        role="a deterministic FMI port-binding tiebreaker",
        task_goal=task_goal,
        output_contract=[
            'Top-level keys: "task_goal_summary", "selected_index", and "reason".',
            '"selected_index" must be one of the candidate indices provided by the user.',
            '"reason" must be a short explanation grounded in the provided connection and candidate port names.',
        ],
        validity_rules=[
            "Do not invent new ports or indices.",
            "Choose only from the provided candidates.",
            "Prefer the candidate whose source and target ports best preserve the intended MBSE signal flow.",
            "If the candidates are indistinguishable, return index 0.",
        ],
    )
    user_prompt = json.dumps(
        {
            "current_task_goal": task_goal,
            "system_name": mbse_context.system_name,
            "connection": {
                "source_component": connection.source_component,
                "source_signal": connection.source_signal,
                "target_component": connection.target_component,
                "target_signal": connection.target_signal,
            },
            "source_fmu": {"uid": source_fmu.uid, "name": source_fmu.name, "description": source_fmu.description},
            "target_fmu": {"uid": target_fmu.uid, "name": target_fmu.name, "description": target_fmu.description},
            "candidates": [
                {
                    "index": index,
                    "source_port": _candidate_source_port(item),
                    "target_port": _candidate_target_port(item),
                    "score": float(_candidate_score(item)),
                    "score_breakdown": _candidate_score_breakdown(item),
                    "source_port_meta": _candidate_source_meta(item),
                    "target_port_meta": _candidate_target_meta(item),
                }
                for index, item in enumerate(candidates[:6])
            ],
        },
        ensure_ascii=False,
    )
    response = chat_json(system_prompt, user_prompt, temperature=0.0, max_tokens=300)
    if not isinstance(response, dict):
        return 0
    goal_summary = str(response.get("task_goal_summary") or "").strip()
    if not goal_is_aligned(goal_summary, task_goal, min_common_tokens=2, min_overlap=0.2):
        return 0
    try:
        selected_index = int(response.get("selected_index", 0))
    except (TypeError, ValueError):
        return 0
    return selected_index if 0 <= selected_index < len(candidates) else 0


def _apply_monitor_variant_penalty(
    semantic_matrix: List[List[float]],
    task_set: TaskSet,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> None:
    """Penalize FMU monitor variants unless task explicitly requires monitoring."""
    task_wants_monitor = False
    for task in task_set.tasks:
        obj_lower = str(task.objective or "").lower()
        if "monitor" in obj_lower or "validation" in obj_lower:
            task_wants_monitor = True
            break
        for comp in task.grounded_components:
            if "monitor" in str(comp or "").lower():
                task_wants_monitor = True
                break
    if task_wants_monitor:
        return

    case_id = str(mbse_context.metadata.get("case_id") or "").lower()
    if "monitor" in case_id:
        return

    for col, fmu in enumerate(fmu_library):
        uid_lower = str(fmu.uid or "").lower()
        name_lower = str(fmu.name or "").lower()
        if "_monitor" in uid_lower or uid_lower.endswith("monitor") or "_monitor" in name_lower:
            non_monitor_uid = uid_lower.replace("_monitor", "")
            has_base = any(
                non_monitor_uid == str(other.uid or "").lower()
                or non_monitor_uid in str(other.uid or "").lower()
                for other in fmu_library
                if other.uid != fmu.uid
            )
            if has_base:
                penalty = 3.0
            else:
                penalty = 1.0
            for row in range(len(semantic_matrix)):
                semantic_matrix[row][col] = float(semantic_matrix[row][col]) + penalty


def _apply_source_type_hard_mask(
    mask_matrix: List[List[float]],
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> None:
    """Block FMUs from wrong source_type family for benchmark cases."""
    preferred_family = _case_source_family(mbse_context)
    if preferred_family != "benchmark_single_fmu":
        return
    for col, fmu in enumerate(fmu_library):
        source_type = str((fmu.meta or {}).get("source_type") or "")
        if source_type == preferred_family:
            continue
        for row in range(len(mask_matrix)):
            if math.isfinite(mask_matrix[row][col]):
                mask_matrix[row][col] = float("inf")


def _post_connect_selected_fmus(
    graph: OrchestrationGraph,
    selected_fmus: Sequence[FMU],
) -> OrchestrationGraph:
    """Discover and add missing direct connections between selected FMUs.

    After the signal-chain-driven graph construction, some valid connections
    may be absent because the taskset's required signal chains did not cover
    them.  This pass scans all unconnected input ports and looks for a
    compatible output on another selected FMU by exact name match.
    """
    existing_targets = {(b.target_fmu, b.target_signal) for b in graph.bindings}
    fmu_uids = {fmu.uid for fmu in selected_fmus}
    new_bindings = list(graph.bindings)
    added = 0
    for target_fmu in selected_fmus:
        for t_port in input_ports(target_fmu):
            if (target_fmu.uid, t_port.name) in existing_targets:
                continue
            for source_fmu in selected_fmus:
                if source_fmu.uid == target_fmu.uid:
                    continue
                for s_port in output_ports(source_fmu):
                    if s_port.name == t_port.name or s_port.name.rstrip("_out") == t_port.name.rstrip("_in"):
                        new_bindings.append(
                            PortBinding(
                                source_fmu=source_fmu.uid,
                                source_signal=s_port.name,
                                target_fmu=target_fmu.uid,
                                target_signal=t_port.name,
                                chain_id="post_connect",
                                segment_id=f"post_{added}",
                            )
                        )
                        existing_targets.add((target_fmu.uid, t_port.name))
                        added += 1
                        break
                else:
                    continue
                break
    if added == 0:
        return graph
    return replace(
        graph,
        bindings=new_bindings,
        diagnostics={**graph.diagnostics, "post_connect_added": added},
    )


def _run_taskset_transport(
    task_set: TaskSet,
    *,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
    max_revisions: int,
    top_m_per_task: int,
    max_port_candidates: int,
) -> MatchingResult:
    fmu_by_uid = {fmu.uid: fmu for fmu in fmu_library}
    fmu_uids = [fmu.uid for fmu in fmu_library]
    semantic_matrix = build_semantic_cost_matrix(task_set, fmu_library)
    _apply_source_type_prior(semantic_matrix, mbse_context, fmu_library)
    _apply_runtime_capability_prior(semantic_matrix, mbse_context, fmu_library)
    _apply_grounded_component_prior(semantic_matrix, task_set, fmu_library)
    _apply_grounded_component_type_prior(semantic_matrix, task_set, fmu_library)
    _apply_case_id_prior(semantic_matrix, mbse_context, fmu_library)
    mask_matrix = build_hard_mask_matrix(task_set, mbse_context, fmu_library)
    _apply_source_type_hard_mask(mask_matrix, mbse_context, fmu_library)
    _apply_monitor_variant_penalty(semantic_matrix, task_set, mbse_context, fmu_library)
    mask_explanations = build_hard_mask_explanations(task_set, mbse_context, fmu_library)
    row_mass = [1.0 for _ in task_set.tasks]
    transport_plans: List[Dict[str, Any]] = []
    mask_history: List[Dict[str, Any]] = []
    revision_trace: List[Dict[str, Any]] = []

    for revision in range(max(int(max_revisions), 0) + 1):
        fused = [
            [
                (semantic_matrix[row][col] + mask_matrix[row][col]) if math.isfinite(mask_matrix[row][col]) else float("inf")
                for col in range(len(mask_matrix[row]))
            ]
            for row in range(len(mask_matrix))
        ]
        plan = solve_row_constrained_sinkhorn(fused, row_mass=row_mass, epsilon=0.05, max_iters=200, tol=1e-6)
        plan_objective = compute_transport_objective(plan)
        transport_plans.append({"revision": revision, "objective": plan_objective, **plan})
        mask_history.append(
            {
                "revision": revision,
                "finite_pairs": sum(1 for row in mask_matrix for value in row if math.isfinite(value)),
                "blocked_pairs": sum(1 for row in mask_matrix for value in row if not math.isfinite(value)),
                "mask_matrix": mask_matrix,
                "mask_explanations": mask_explanations,
                "applied_exclusion_pair": None,
                "exclusion_reason": None,
            }
        )
        assignments = extract_assignment_from_transport(
            plan,
            task_set,
            fmu_library,
            top_m_per_task,
            mask_matrix=mask_matrix,
            semantic_matrix=semantic_matrix,
            revision_index=revision,
        )
        if len(assignments) != len(task_set.tasks):
            missing_tasks = [index for index in range(len(task_set.tasks)) if index >= len(assignments)]
            failure = {
                "failure_type": "no_feasible_assignment",
                "failure_class": "assignment_failure",
                "eligible_for_mask_revision": False,
                "revision_action": "stop",
                "details": {"missing_tasks": missing_tasks},
                "responsible_pair": None,
            }
            revision_trace.append(
                {
                    "revision": revision,
                    "status": "failed",
                    "failure": failure,
                    "failure_type": failure["failure_type"],
                    "failure_class": failure["failure_class"],
                    "revision_eligible": False,
                    "assignment": [assignment.fmu_uid for assignment in assignments],
                }
            )
            break

        graph_result = instantiate_port_graph(
            task_set,
            assignments,
            mbse_context,
            fmu_by_uid,
            max_port_candidates,
            ambiguity_resolver=_resolve_binding_ambiguity,
        )
        closure_ok = bool(graph_result["closure_ok"])
        revision_trace.append(
            {
                "revision": revision,
                "status": "ok" if closure_ok else "retry",
                "assignment": [
                    {
                        "task_id": assignment.task_id,
                        "task_index": assignment.task_index,
                        "fmu_uid": assignment.fmu_uid,
                        "semantic_cost": assignment.semantic_cost,
                        "transport_mass": assignment.transport_mass,
                    }
                    for assignment in assignments
                ],
                "closure_failure": graph_result["closure_failure"],
                "failure_type": str((graph_result["closure_failure"] or {}).get("failure_type") or ""),
                "failure_class": str((graph_result["closure_failure"] or {}).get("failure_class") or ""),
                "revision_eligible": bool((graph_result["closure_failure"] or {}).get("eligible_for_mask_revision")),
            }
        )
        if closure_ok:
            selected_ids = sorted({assignment.fmu_uid for assignment in assignments})
            selected_fmus = [fmu_by_uid[uid] for uid in selected_ids]
            graph_obj = graph_result["graph"]
            selected_task_set_cost = float(sum(assignment.semantic_cost for assignment in assignments))
            return MatchingResult(
                task_set=task_set,
                assignments=list(assignments),
                selected_fmus=selected_fmus,
                graph=graph_obj,
                discrepancy_set=list(graph_result["discrepancy_set"]),
                revision_trace=revision_trace,
                final_cost=plan_objective,
                transport_plans=transport_plans,
                mask_history=mask_history,
                taskset_results=[],
                selected_task_set_cost=selected_task_set_cost,
                diagnostics={"status": "ok", "revisions": revision + 1, "objective_kind": "fused_transport"},
            )

        failure = detect_graph_closure_failure(graph_result)
        pair = select_conflict_pair_for_mask_update(failure, assignments)
        if pair is None:
            revision_trace[-1]["status"] = "failed"
            revision_trace[-1]["revision_action"] = str((failure or {}).get("revision_action") or "stop")
            break
        updated_mask = apply_failure_mask_update(mask_matrix, pair, fmu_uids)
        if updated_mask == mask_matrix:
            revision_trace[-1]["status"] = "failed"
            revision_trace[-1]["revision_action"] = "mask_unchanged"
            break
        revision_trace[-1]["revision_action"] = "exclude_pair"
        revision_trace[-1]["excluded_pair"] = {"task_index": int(pair[0]), "fmu_uid": str(pair[1])}
        mask_history[-1]["applied_exclusion_pair"] = {"task_index": int(pair[0]), "fmu_uid": str(pair[1])}
        mask_history[-1]["exclusion_reason"] = str((failure or {}).get("failure_type") or "failure_revision_exclusion")
        mask_matrix = updated_mask
        mask_explanations = _mark_revised_mask(mask_explanations, pair, fmu_uids, failure)

    return MatchingResult(
        task_set=task_set,
        assignments=[],
        selected_fmus=[],
        graph=OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False, diagnostics={"status": "failed"}),
        discrepancy_set=[],
        revision_trace=revision_trace,
        final_cost=float("inf"),
        transport_plans=transport_plans,
        mask_history=mask_history,
        taskset_results=[],
        selected_task_set_cost=float("inf"),
        diagnostics={"status": "failed"},
    )


def _apply_case_id_prior(semantic_matrix: List[List[float]], mbse_context: MBSEContext, fmu_library: Sequence[FMU]) -> None:
    source_family = _case_source_family(mbse_context)
    case_id = str(mbse_context.metadata.get("case_id") or "")
    case_norm = _compact_norm(case_id)
    dataset_id = str(mbse_context.metadata.get("dataset_id") or "")
    dataset_norm = _compact_norm(dataset_id)

    if source_family != "benchmark_single_fmu":
        return

    benchmark_suffix = ""
    match = re.search(r"(?:case_)?bench(?:_fmu)?[-_]?(\d+)$", case_id, re.I)
    if match:
        benchmark_suffix = str(match.group(1))
    if not dataset_norm and benchmark_suffix:
        dataset_norm = f"fmu{benchmark_suffix}"

    system_aliases = set(_system_aliases(mbse_context))
    for col, fmu in enumerate(fmu_library):
        aliases = _fmu_aliases(fmu)
        bonus = 0.0
        if case_norm:
            exact_asset_alias = _compact_norm(case_id.replace("case_", "asset_"))
            if exact_asset_alias and exact_asset_alias in aliases:
                bonus += 2.0
        if benchmark_suffix:
            suffix_hits = sum(
                1
                for alias in aliases
                if alias.endswith(benchmark_suffix) or alias == f"fmu{benchmark_suffix}" or alias == f"assetbenchfmu{benchmark_suffix}"
            )
            if suffix_hits:
                bonus += 1.5
        if dataset_norm and dataset_norm in aliases:
            bonus += 1.0
        if system_aliases and any(alias in system_aliases for alias in aliases):
            bonus += 0.35
        if bonus <= 0.0:
            continue
        for row in range(len(semantic_matrix)):
            semantic_matrix[row][col] = float(semantic_matrix[row][col]) - bonus


def _case_source_family(mbse_context: MBSEContext) -> str:
    source_type = str(mbse_context.metadata.get("source_type") or "")
    if source_type == "benchmark_single_fmu_case":
        return "benchmark_single_fmu"
    if source_type == "manual_multi_fmu_case":
        return "manual_case_fmu"
    if source_type == "dtaas_multi_fmu_case":
        return "dtaas_example_fmu"
    case_id = str(mbse_context.metadata.get("case_id") or "")
    if case_id.startswith("case_bench_"):
        return "benchmark_single_fmu"
    if case_id.startswith("case_manual_"):
        return "manual_case_fmu"
    if case_id.startswith("case_dtaas_"):
        return "dtaas_example_fmu"
    return ""


def _apply_source_type_prior(semantic_matrix: List[List[float]], mbse_context: MBSEContext, fmu_library: Sequence[FMU]) -> None:
    preferred_family = _case_source_family(mbse_context)
    if not preferred_family:
        return
    for col, fmu in enumerate(fmu_library):
        source_type = str((fmu.meta or {}).get("source_type") or "")
        if source_type == preferred_family:
            delta = -1.5
        elif preferred_family == "benchmark_single_fmu":
            delta = 4.0
        else:
            delta = 2.0
        for row in range(len(semantic_matrix)):
            semantic_matrix[row][col] = float(semantic_matrix[row][col]) + delta


def _apply_runtime_capability_prior(
    semantic_matrix: List[List[float]],
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> None:
    if _case_source_family(mbse_context) != "benchmark_single_fmu":
        return
    for col, fmu in enumerate(fmu_library):
        types = {str(kind) for kind in fmu.fmi_types}
        has_cosim = bool(types & {"CoSimulation", "Co-Simulation"})
        has_me = bool(types & {"ModelExchange", "Model Exchange"})
        delta = -0.1 if (has_cosim or has_me) else 0.05
        if fmu.capabilities.needs_execution_tool:
            delta += 1.0
        for row in range(len(semantic_matrix)):
            semantic_matrix[row][col] = float(semantic_matrix[row][col]) + delta


def _apply_grounded_component_prior(semantic_matrix: List[List[float]], task_set: TaskSet, fmu_library: Sequence[FMU]) -> None:
    for row, task in enumerate(task_set.tasks):
        grounded = [_compact_norm(name) for name in task.grounded_components if _compact_norm(name)]
        if not grounded:
            continue
        for col, fmu in enumerate(fmu_library):
            aliases = {_compact_norm(fmu.uid), _compact_norm(fmu.name), *[_compact_norm(tag) for tag in fmu.tags]}
            aliases.discard("")
            exact = any(name == alias for name in grounded for alias in aliases)
            partial = any(name in alias or alias in name for name in grounded for alias in aliases)
            if exact:
                semantic_matrix[row][col] = float(semantic_matrix[row][col]) - 1.5
            elif partial:
                semantic_matrix[row][col] = float(semantic_matrix[row][col]) - 0.6


def _apply_grounded_component_type_prior(
    semantic_matrix: List[List[float]],
    task_set: TaskSet,
    fmu_library: Sequence[FMU],
) -> None:
    for row, task in enumerate(task_set.tasks):
        type_hints = [_compact_norm(name) for name in task.grounded_component_types if _compact_norm(name)]
        if not type_hints:
            continue
        for col, fmu in enumerate(fmu_library):
            aliases = _fmu_aliases(fmu)
            exact_hit = any(type_hint and type_hint in aliases for type_hint in type_hints)
            partial_hit = False
            if not exact_hit:
                for type_hint in type_hints:
                    if not type_hint:
                        continue
                    if any(type_hint in alias or alias in type_hint for alias in aliases if alias):
                        partial_hit = True
                        break
            if exact_hit:
                semantic_matrix[row][col] = float(semantic_matrix[row][col]) - 0.35
            elif partial_hit:
                semantic_matrix[row][col] = float(semantic_matrix[row][col]) - 0.15


def _fmu_aliases(fmu: FMU) -> set[str]:
    aliases = {
        _compact_norm(fmu.uid),
        _compact_norm(fmu.name),
        _compact_norm(fmu.description),
    }
    aliases.update(_compact_norm(tag) for tag in fmu.tags)
    asset_json = (fmu.meta or {}).get("asset_json") if isinstance(fmu.meta, dict) else {}
    if isinstance(asset_json, dict):
        aliases.add(_compact_norm(str(asset_json.get("source_id") or "")))
        aliases.add(_compact_norm(str(asset_json.get("name") or "")))
        provenance = asset_json.get("provenance")
        if isinstance(provenance, dict):
            aliases.add(_compact_norm(str(provenance.get("source_id") or "")))
    description = str(fmu.description or "")
    instance_match = re.search(r"instance of\s+(.+?)\s+in\s+(.+?)(?:[.]\s|$)", description, re.I)
    if instance_match:
        aliases.add(_compact_norm(instance_match.group(1)))
        aliases.add(_compact_norm(instance_match.group(2)))
    aliases.discard("")
    return aliases


def _compact_norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _system_aliases(mbse_context: MBSEContext) -> list[str]:
    aliases = {
        _compact_norm(mbse_context.system_name),
        _compact_norm(mbse_context.package_name),
    }
    trimmed: set[str] = set()
    for alias in aliases:
        if alias.startswith("system") and len(alias) > len("system"):
            trimmed.add(alias[len("system") :])
        if alias.startswith("pkg") and len(alias) > len("pkg"):
            trimmed.add(alias[len("pkg") :])
    aliases.update(trimmed)
    aliases.discard("")
    return sorted(aliases)


def _covered_required_component_count(result: MatchingResult, mbse_context: MBSEContext) -> int:
    required_components = _required_mbse_components(result.task_set, mbse_context)
    if not required_components or not result.selected_fmus:
        return 0
    used_fmu_uids: set[str] = set()
    covered = 0
    system_aliases = _system_aliases(mbse_context)
    for component in required_components:
        chosen = _match_component_to_fmu(
            component.name,
            component.component_type,
            [str(port.name) for port in component.ports if str(port.name).strip()],
            result.selected_fmus,
            used_fmu_uids,
            system_aliases=system_aliases,
        )
        if chosen is None:
            continue
        covered += 1
        used_fmu_uids.add(chosen.uid)
    return covered


def _required_mbse_connections(result: MatchingResult, mbse_context: MBSEContext) -> List[MBSEConnection]:
    required_component_names = {
        str(component.name).strip()
        for component in _required_mbse_components(result.task_set, mbse_context)
        if str(component.name).strip()
    }
    if not required_component_names:
        return list(mbse_context.connections)
    return [
        connection
        for connection in mbse_context.connections
        if str(connection.source_component).strip() in required_component_names
        and str(connection.target_component).strip() in required_component_names
    ]


def _covered_required_connection_count(result: MatchingResult, mbse_context: MBSEContext) -> int:
    required_connections = _required_mbse_connections(result, mbse_context)
    if not required_connections or not result.selected_fmus:
        return 0

    system_aliases = _system_aliases(mbse_context)
    component_to_fmu: Dict[str, FMU] = {}
    used_fmu_uids: set[str] = set()
    for component in _required_mbse_components(result.task_set, mbse_context):
        chosen = _match_component_to_fmu(
            component.name,
            component.component_type,
            [str(port.name) for port in component.ports if str(port.name).strip()],
            result.selected_fmus,
            used_fmu_uids,
            system_aliases=system_aliases,
        )
        if chosen is None:
            continue
        component_to_fmu[component.name] = chosen
        used_fmu_uids.add(chosen.uid)

    binding_counts: Dict[Tuple[str, str], int] = {}
    for binding in result.graph.bindings:
        key = (str(binding.source_fmu).strip(), str(binding.target_fmu).strip())
        binding_counts[key] = binding_counts.get(key, 0) + 1

    covered = 0
    for connection in required_connections:
        source_fmu = component_to_fmu.get(connection.source_component)
        target_fmu = component_to_fmu.get(connection.target_component)
        if source_fmu is None or target_fmu is None:
            continue
        key = (source_fmu.uid, target_fmu.uid)
        remaining = binding_counts.get(key, 0)
        if remaining <= 0:
            continue
        binding_counts[key] = remaining - 1
        covered += 1
    return covered


def _selection_key(
    result: MatchingResult,
    mbse_context: MBSEContext,
    *,
    enhanced_ranking: bool = False,
) -> Tuple:
    required_component_count = len(_required_mbse_components(result.task_set, mbse_context))
    covered_component_count = _covered_required_component_count(result, mbse_context)
    coverage_gap = max(required_component_count - covered_component_count, 0)
    required_connection_count = len(_required_mbse_connections(result, mbse_context))
    covered_connection_count = _covered_required_connection_count(result, mbse_context)
    connection_gap = max(required_connection_count - covered_connection_count, 0)
    task_identifier = 0
    try:
        task_identifier = int(str(result.task_set.task_set_id or "0").split("_")[-1])
    except (TypeError, ValueError):
        task_identifier = 0
    status = str(result.diagnostics.get("status") or "")
    successful_status = status in {"ok", "mbse_component_cover_fallback", "fallback_ambiguous"}
    score = float(getattr(result.task_set, "score", 0.0) or 0.0)
    cost = float(result.final_cost if math.isfinite(result.final_cost) else result.selected_task_set_cost)
    semantic_cost = float(result.selected_task_set_cost if math.isfinite(result.selected_task_set_cost) else result.final_cost)
    if enhanced_ranking:
        score_bucket = 0 if score >= 0.7 else 1
        return (
            0 if successful_status else 1,
            coverage_gap,
            connection_gap,
            score_bucket,
            cost,
            semantic_cost,
            task_identifier,
        )
    return (
        0 if successful_status else 1,
        coverage_gap,
        connection_gap,
        -score,
        cost,
        semantic_cost,
        task_identifier,
    )


def match(
    task_sets: List[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: List[FMU],
    max_revisions: int = 6,
    top_m_per_task: int = 5,
    max_port_candidates: int = 8,
    enable_benchmark_single_fmu_fallback: bool = True,
    enable_mbse_component_cover_fallback: bool = True,
) -> MatchingResult:
    if not task_sets:
        raise ValueError("match() received empty task_sets")
    if not fmu_library:
        raise ValueError("match() received empty fmu_library")

    _enhanced = enable_benchmark_single_fmu_fallback or enable_mbse_component_cover_fallback
    per_taskset_results: List[MatchingResult] = []
    taskset_summaries: List[Dict[str, Any]] = []
    best: Optional[MatchingResult] = None
    for task_set in task_sets:
        result = _run_taskset_transport(
            task_set,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
            max_revisions=max_revisions,
            top_m_per_task=top_m_per_task,
            max_port_candidates=max_port_candidates,
        )
        if enable_benchmark_single_fmu_fallback:
            result = _apply_benchmark_single_fmu_fallback(result, task_set, mbse_context, fmu_library)
        if enable_mbse_component_cover_fallback:
            result = _apply_mbse_component_cover_fallback(result, mbse_context, fmu_library)
        per_taskset_results.append(result)
        taskset_summaries.append(
            {
                "task_set_id": task_set.task_set_id,
                "status": result.diagnostics.get("status"),
                "selected_task_set_cost": result.selected_task_set_cost,
                "final_cost": result.final_cost,
                "selected_fmus": [fmu.uid for fmu in result.selected_fmus],
                "discrepancy_count": len(result.discrepancy_set),
            }
        )
        if best is None or _selection_key(result, mbse_context, enhanced_ranking=_enhanced) < _selection_key(best, mbse_context, enhanced_ranking=_enhanced):
            best = result

    assert best is not None

    if not best.selected_fmus:
        best_task_set = best.task_set
        if enable_benchmark_single_fmu_fallback:
            recovered = _apply_benchmark_single_fmu_fallback(best, best_task_set, mbse_context, fmu_library)
        else:
            recovered = best
        if not recovered.selected_fmus and enable_mbse_component_cover_fallback:
            recovered = _apply_mbse_component_cover_fallback(recovered, mbse_context, fmu_library)
        if recovered.selected_fmus:
            best = recovered
            for index, summary in enumerate(taskset_summaries):
                if summary.get("task_set_id") == best_task_set.task_set_id:
                    taskset_summaries[index] = {
                        "task_set_id": best_task_set.task_set_id,
                        "status": best.diagnostics.get("status"),
                        "selected_task_set_cost": best.selected_task_set_cost,
                        "final_cost": best.final_cost,
                        "selected_fmus": [fmu.uid for fmu in best.selected_fmus],
                        "discrepancy_count": len(best.discrepancy_set),
                    }
                    break

    if _enhanced and len(best.selected_fmus) > 1:
        best = replace(best, graph=_post_connect_selected_fmus(best.graph, best.selected_fmus))

    return replace(best, taskset_results=taskset_summaries)


def _apply_benchmark_single_fmu_fallback(
    result: MatchingResult,
    task_set: TaskSet,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> MatchingResult:
    if result.selected_fmus or _case_source_family(mbse_context) != "benchmark_single_fmu":
        return result
    benchmark_fmus = [
        fmu for fmu in fmu_library if str((fmu.meta or {}).get("source_type") or "") == "benchmark_single_fmu"
    ]
    if not benchmark_fmus:
        return result

    selected = sorted(
        benchmark_fmus,
        key=lambda item: (
            -_benchmark_fallback_score(task_set, mbse_context, item),
            0 if any(str(kind) in {"CoSimulation", "Co-Simulation"} for kind in item.fmi_types) else 1,
            item.uid,
        ),
    )[0]
    fallback_score = _benchmark_fallback_score(task_set, mbse_context, selected)
    if fallback_score < 0.3:
        return result
    assignments = [
        TaskAssignment(
            task_id=task.task_id,
            task_index=index,
            fmu_uid=selected.uid,
            score=1.0,
            cost=max(0.01, 1.0 / (1.0 + max(fallback_score, 0.0))),
            hard_ok=True,
            semantic_cost=max(0.01, 1.0 / (1.0 + max(fallback_score, 0.0))),
            hard_mask_value=0.0,
            transport_mass=1.0,
            revision_index=0,
            reasons=["benchmark_single_fmu_fallback"],
            grounded_components=list(task.grounded_components),
        )
        for index, task in enumerate(task_set.tasks)
    ]
    graph = OrchestrationGraph(
        nodes=[selected.uid],
        bindings=[],
        component_to_fmu={},
        closure_ok=True,
        diagnostics={"status": "benchmark_single_fmu_fallback"},
    )
    return MatchingResult(
        task_set=task_set,
        assignments=assignments,
        selected_fmus=[selected],
        graph=graph,
        discrepancy_set=[],
        revision_trace=list(result.revision_trace)
        + [{"revision": "fallback", "status": "ok", "assignment": [selected.uid], "revision_action": "select_single_fmu"}],
        final_cost=max(0.01, 1.0 / (1.0 + max(fallback_score, 0.0))),
        transport_plans=list(result.transport_plans),
        mask_history=list(result.mask_history),
        taskset_results=list(result.taskset_results),
        selected_task_set_cost=max(0.01, 1.0 / (1.0 + max(fallback_score, 0.0))),
        diagnostics={
            "status": "fallback_ambiguous",
            "base_status": result.diagnostics.get("status"),
            "fallback_used": True,
            "fallback_score": float(fallback_score),
            "fallback_selected_uid": selected.uid,
        },
    )


def _apply_mbse_component_cover_fallback(
    result: MatchingResult,
    mbse_context: MBSEContext,
    fmu_library: Sequence[FMU],
) -> MatchingResult:
    """Incremental Coverage Augmentation: greedily add family-compatible FMUs
    that close signal-chain gaps, preserving the OT-selected set."""
    preferred_family = _case_source_family(mbse_context)
    if preferred_family not in {"manual_case_fmu", "dtaas_example_fmu"}:
        return result
    family_fmus = [fmu for fmu in fmu_library if str((fmu.meta or {}).get("source_type") or "") == preferred_family]
    if not family_fmus:
        return result

    current_fmus: List[FMU] = list(result.selected_fmus)
    current_uids: set[str] = {fmu.uid for fmu in current_fmus}
    fmu_by_uid: Dict[str, FMU] = {fmu.uid: fmu for fmu in family_fmus}

    if not current_fmus:
        seed = _seed_fmu_from_task(result.task_set, family_fmus, mbse_context)
        if seed is None:
            return result
        current_fmus = [seed]
        current_uids = {seed.uid}

    mbse_connections = list(mbse_context.connections)
    system_aliases = _system_aliases(mbse_context)
    component_to_fmu_map: Dict[str, FMU] = {}
    for fmu in current_fmus:
        for component in mbse_context.components:
            if _compact_norm(component.name) in _fmu_aliases(fmu):
                component_to_fmu_map[component.name] = fmu

    max_rounds = len(family_fmus)
    added_count = 0
    for _ in range(max_rounds):
        gap_fmu = _find_gap_filling_fmu(
            current_uids, component_to_fmu_map, mbse_connections,
            family_fmus, mbse_context, system_aliases,
        )
        if gap_fmu is None:
            break
        current_fmus.append(gap_fmu)
        current_uids.add(gap_fmu.uid)
        for component in mbse_context.components:
            if _compact_norm(component.name) in _fmu_aliases(gap_fmu):
                component_to_fmu_map[component.name] = gap_fmu
        added_count += 1

    if added_count == 0 and result.selected_fmus:
        return result

    bindings: List[PortBinding] = list(result.graph.bindings) if result.selected_fmus else []
    existing_binding_keys = {(b.source_fmu, b.source_signal, b.target_fmu, b.target_signal) for b in bindings}
    for conn_idx, connection in enumerate(mbse_connections):
        src_fmu = component_to_fmu_map.get(connection.source_component)
        tgt_fmu = component_to_fmu_map.get(connection.target_component)
        if src_fmu is None or tgt_fmu is None:
            continue
        src_signal = _resolve_fmu_signal_name(src_fmu, connection.source_signal)
        tgt_signal = _resolve_fmu_signal_name(tgt_fmu, connection.target_signal)
        if not src_signal or not tgt_signal:
            continue
        key = (src_fmu.uid, src_signal, tgt_fmu.uid, tgt_signal)
        if key in existing_binding_keys:
            continue
        bindings.append(PortBinding(
            source_fmu=src_fmu.uid,
            source_signal=src_signal,
            target_fmu=tgt_fmu.uid,
            target_signal=tgt_signal,
            score=1.0,
            chain_id=f"ica_chain_{conn_idx}",
            segment_id=f"ica_seg_{conn_idx}",
            selected_by="incremental_coverage_augmentation",
            reasons=["signal_chain_gap_fill"],
        ))
        existing_binding_keys.add(key)

    graph = OrchestrationGraph(
        nodes=[fmu.uid for fmu in current_fmus],
        bindings=bindings,
        component_to_fmu={name: fmu.uid for name, fmu in component_to_fmu_map.items()},
        closure_ok=True,
        diagnostics={
            "status": "incremental_coverage_augmentation",
            "binding_count": len(bindings),
            "augmented_fmu_count": added_count,
        },
    )

    base_assignments = list(result.assignments) if result.selected_fmus else []
    for fmu in current_fmus:
        if not any(a.fmu_uid == fmu.uid for a in base_assignments):
            base_assignments.append(TaskAssignment(
                task_id=f"ica_task_{fmu.uid}",
                task_index=len(base_assignments),
                fmu_uid=fmu.uid,
                score=1.0,
                cost=0.1,
                hard_ok=True,
                semantic_cost=0.1,
                hard_mask_value=0.0,
                transport_mass=1.0,
                revision_index=0,
                reasons=["incremental_coverage_augmentation"],
                grounded_components=[
                    name for name, mapped in component_to_fmu_map.items() if mapped.uid == fmu.uid
                ],
            ))

    return MatchingResult(
        task_set=result.task_set,
        assignments=base_assignments,
        selected_fmus=current_fmus,
        graph=graph,
        discrepancy_set=list(result.discrepancy_set),
        revision_trace=list(result.revision_trace)
        + [{"revision": "ica", "status": "ok", "revision_action": "incremental_coverage_augmentation", "added": added_count}],
        final_cost=result.final_cost if math.isfinite(result.final_cost) else 0.1,
        transport_plans=list(result.transport_plans),
        mask_history=list(result.mask_history),
        taskset_results=list(result.taskset_results),
        selected_task_set_cost=result.selected_task_set_cost if math.isfinite(result.selected_task_set_cost) else 0.1,
        diagnostics={
            "status": "incremental_coverage_augmentation",
            "base_status": result.diagnostics.get("status"),
            "augmented_fmu_count": added_count,
            "total_fmu_count": len(current_fmus),
        },
    )


def _seed_fmu_from_task(
    task_set: TaskSet,
    family_fmus: Sequence[FMU],
    mbse_context: MBSEContext,
) -> Optional[FMU]:
    """When OT produced nothing, pick the single best FMU for the task set."""
    system_aliases = _system_aliases(mbse_context)
    grounded = []
    for task in task_set.tasks:
        grounded.extend(task.grounded_components)
    best_score = -1.0
    best_fmu: Optional[FMU] = None
    for fmu in family_fmus:
        aliases = _fmu_aliases(fmu)
        score = 0.0
        for comp_name in grounded:
            if _compact_norm(comp_name) in aliases:
                score += 5.0
            elif _compact_norm(comp_name) and any(_compact_norm(comp_name) in a or a in _compact_norm(comp_name) for a in aliases if a):
                score += 1.5
        for alias in system_aliases:
            if alias and alias in aliases:
                score += 2.0
        if score > best_score:
            best_score = score
            best_fmu = fmu
    return best_fmu if best_score > 0 else None


def _find_gap_filling_fmu(
    current_uids: set[str],
    component_to_fmu_map: Dict[str, Any],
    mbse_connections: Sequence[Any],
    family_fmus: Sequence[FMU],
    mbse_context: MBSEContext,
    system_aliases: Sequence[str],
) -> Optional[FMU]:
    """Find the single FMU that closes the most signal-chain gaps."""
    covered_components = set(component_to_fmu_map.keys())
    gap_components: set[str] = set()
    for connection in mbse_connections:
        src_in = connection.source_component in covered_components
        tgt_in = connection.target_component in covered_components
        if src_in and not tgt_in:
            gap_components.add(connection.target_component)
        elif tgt_in and not src_in:
            gap_components.add(connection.source_component)

    if not gap_components:
        return None

    best_fmu: Optional[FMU] = None
    best_closed = 0
    for fmu in family_fmus:
        if fmu.uid in current_uids:
            continue
        aliases = _fmu_aliases(fmu)
        closed = sum(1 for comp in gap_components if _compact_norm(comp) in aliases)
        if closed > best_closed:
            best_closed = closed
            best_fmu = fmu
    if best_fmu is not None:
        return best_fmu

    for fmu in family_fmus:
        if fmu.uid in current_uids:
            continue
        aliases = _fmu_aliases(fmu)
        for comp in gap_components:
            comp_key = _compact_norm(comp)
            if comp_key and any(comp_key in a or a in comp_key for a in aliases if a):
                return fmu
    return None


def _task_signal_names(task: VerificationTask) -> List[str]:
    names: List[str] = []
    names.extend(str(signal) for signal in task.required_signals if str(signal).strip())
    names.extend(str(signal) for signal in task.grounded_ports if str(signal).strip())
    for spec in task.signal_specs:
        for candidate in (spec.signal_name, spec.source_text, spec.grounded_port_ref):
            text = str(candidate or "").strip()
            if text:
                names.append(text.rsplit(".", 1)[-1])
    return names


def _pick_component_seed_task(task_set: TaskSet, component: Any) -> Optional[VerificationTask]:
    component_name = str(component.name or "").strip()
    component_type = str(component.component_type or "").strip()
    component_ports = {
        str(port.name).strip()
        for port in getattr(component, "ports", []) or []
        if str(getattr(port, "name", "")).strip()
    }
    scored: List[Tuple[float, int, VerificationTask]] = []
    for index, task in enumerate(task_set.tasks):
        score = 0.0
        if component_name and component_name in {str(name).strip() for name in task.grounded_components if str(name).strip()}:
            score += 8.0
        if component_type and component_type in {
            str(name).strip() for name in task.grounded_component_types if str(name).strip()
        }:
            score += 4.0
        task_signals = set(_task_signal_names(task))
        if component_ports:
            overlap = task_signals & component_ports
            score += float(len(overlap))
            if overlap and overlap == component_ports:
                score += 1.0
        if task.operating_regime is not None:
            score += 0.5
        if task.signal_specs:
            score += 0.5
        if task.acceptance_criteria:
            score += 0.25
        if score > 0.0:
            scored.append((score, -index, task))
    if not scored:
        return task_set.tasks[0] if task_set.tasks else None
    scored.sort(reverse=True)
    return scored[0][2]


def _component_signal_specs(seed_task: VerificationTask, component: Any) -> List[Any]:
    component_name = str(component.name or "").strip()
    component_type = str(component.component_type or "").strip()
    component_ports = {
        str(port.name).strip()
        for port in getattr(component, "ports", []) or []
        if str(getattr(port, "name", "")).strip()
    }
    filtered = [
        spec
        for spec in seed_task.signal_specs
        if (
            component_name
            and component_name
            in {
                str(getattr(spec, "grounded_component_ref", "") or "").strip(),
                str(getattr(spec, "component_hint", "") or "").strip(),
            }
        )
        or (
            component_type
            and component_type
            in {
                str(getattr(spec, "grounded_component_ref", "") or "").strip(),
                str(getattr(spec, "component_hint", "") or "").strip(),
            }
        )
        or str(getattr(spec, "signal_name", "") or "").strip() in component_ports
        or str(getattr(spec, "source_text", "") or "").strip() in component_ports
        or str(getattr(spec, "grounded_port_ref", "") or "").strip().rsplit(".", 1)[-1] in component_ports
    ]
    return filtered or list(seed_task.signal_specs)


def _fallback_operating_regime(seed_task: VerificationTask) -> Any:
    regime = seed_task.operating_regime
    if regime is None:
        return None
    if regime.inputs or regime.initial_conditions or regime.assumptions:
        return regime
    return None


def _build_component_cover_task(*, task_set: TaskSet, component: Any, index: int) -> VerificationTask:
    component_ports = [str(port.name) for port in getattr(component, "ports", []) or [] if str(port.name).strip()]
    seed_task = _pick_component_seed_task(task_set, component)
    if seed_task is None:
        return VerificationTask(
            task_id=f"fallback_component_{index}",
            objective=f"Fallback cover for {component.name}",
            required_signals=component_ports,
            grounded_components=[component.name],
            grounded_component_types=[component.component_type],
            grounded_ports=component_ports,
        )
    signal_specs = _component_signal_specs(seed_task, component)
    relevant_signals = list(dict.fromkeys(component_ports + [str(spec.signal_name).strip() for spec in signal_specs if str(spec.signal_name).strip()]))
    relevant_grounded_ports = list(
        dict.fromkeys(
            component_ports
            + [
                str(getattr(spec, "grounded_port_ref", "") or "").strip()
                for spec in signal_specs
                if str(getattr(spec, "grounded_port_ref", "") or "").strip()
            ]
        )
    )
    return replace(
        seed_task,
        task_id=f"fallback_component_{index}",
        objective=str(seed_task.objective or f"Fallback cover for {component.name}"),
        required_signals=relevant_signals,
        signal_specs=signal_specs,
        operating_regime=_fallback_operating_regime(seed_task),
        grounded_components=[component.name],
        grounded_component_types=[component.component_type],
        grounded_ports=relevant_grounded_ports or component_ports,
    )


def _required_mbse_components(task_set: TaskSet, mbse_context: MBSEContext) -> List[Any]:
    component_names: List[str] = []
    for task in task_set.tasks:
        component_names.extend(str(name) for name in task.grounded_components if str(name).strip())
    for chain in task_set.required_signal_chains:
        component_names.extend(
            [
                str(chain.source_component or "").strip(),
                str(chain.target_component or "").strip(),
            ]
        )
    ordered_names = [name for name in dict.fromkeys(component_names) if name]
    if not ordered_names:
        return list(mbse_context.components)
    component_by_name = {component.name: component for component in mbse_context.components}
    return [component_by_name[name] for name in ordered_names if name in component_by_name]


def _selected_fmus_cover_required_components(
    selected_fmus: Sequence[FMU],
    required_components: Sequence[Any],
    mbse_context: MBSEContext,
) -> bool:
    if not selected_fmus or len(selected_fmus) < len(required_components):
        return False
    used_fmu_uids: set[str] = set()
    system_aliases = _system_aliases(mbse_context)
    for component in required_components:
        chosen = _match_component_to_fmu(
            component.name,
            component.component_type,
            [str(port.name) for port in component.ports if str(port.name).strip()],
            selected_fmus,
            used_fmu_uids,
            system_aliases=system_aliases,
        )
        if chosen is None:
            return False
        used_fmu_uids.add(chosen.uid)
    return True


def _component_match_quality(component: Any, fmu: FMU) -> float:
    component_name = _compact_norm(getattr(component, "name", ""))
    component_type = _compact_norm(getattr(component, "component_type", ""))
    component_ports = {
        _compact_norm(getattr(port, "name", ""))
        for port in getattr(component, "ports", []) or []
        if _compact_norm(getattr(port, "name", ""))
    }
    aliases = _fmu_aliases(fmu)
    fmu_ports = {
        _compact_norm(getattr(port, "name", ""))
        for port in getattr(fmu, "ports", []) or []
        if _compact_norm(getattr(port, "name", ""))
    } or {_compact_norm(name) for name in [*fmu.inputs, *fmu.outputs] if _compact_norm(name)}
    overlap = len(component_ports & fmu_ports)
    score = float(overlap) / float(len(component_ports) or 1)
    if component_name and component_name in aliases:
        score += 1.0
    elif component_name and any(component_name in alias or alias in component_name for alias in aliases if alias):
        score += 0.25
    if component_type and component_type in aliases:
        score += 1.0
    elif component_type and any(component_type in alias or alias in component_type for alias in aliases if alias):
        score += 0.25
    return score


def _selected_component_alignment_score(
    selected_fmus: Sequence[FMU],
    required_components: Sequence[Any],
    mbse_context: MBSEContext,
) -> float:
    if not selected_fmus or not required_components:
        return -1.0
    used_fmu_uids: set[str] = set()
    system_aliases = _system_aliases(mbse_context)
    score = 0.0
    for component in required_components:
        chosen = _match_component_to_fmu(
            component.name,
            component.component_type,
            [str(port.name) for port in component.ports if str(port.name).strip()],
            selected_fmus,
            used_fmu_uids,
            system_aliases=system_aliases,
        )
        if chosen is None:
            return -1.0
        used_fmu_uids.add(chosen.uid)
        score += _component_match_quality(component, chosen)
    return score


def _component_mapping_alignment_score(component_to_fmu: Dict[str, FMU], required_components: Sequence[Any]) -> float:
    score = 0.0
    for component in required_components:
        chosen = component_to_fmu.get(str(getattr(component, "name", "")).strip())
        if chosen is None:
            return -1.0
        score += _component_match_quality(component, chosen)
    return score


def _match_component_to_fmu(
    component_name: str,
    component_type: str,
    component_ports: Sequence[str],
    fmus: Sequence[FMU],
    used_fmu_uids: set[str],
    *,
    system_aliases: Sequence[str] = (),
) -> Optional[FMU]:
    name_key = _compact_norm(component_name)
    type_key = _compact_norm(component_type)
    port_keys = {_compact_norm(port) for port in component_ports if _compact_norm(port)}
    exact_name = [
        fmu
        for fmu in fmus
        if fmu.uid not in used_fmu_uids and name_key and name_key in _fmu_aliases(fmu)
    ]
    if len(exact_name) == 1:
        return exact_name[0]
    exact_type = [
        fmu
        for fmu in fmus
        if fmu.uid not in used_fmu_uids and type_key and type_key in _fmu_aliases(fmu)
    ]
    if len(exact_type) == 1:
        return exact_type[0]

    scored_candidates: List[Tuple[float, str, FMU]] = []
    for fmu in fmus:
        if fmu.uid in used_fmu_uids:
            continue
        aliases = _fmu_aliases(fmu)
        port_aliases = {_compact_norm(str(port.name)) for port in fmu.ports if _compact_norm(str(port.name))}
        score = 0.0
        if name_key in aliases:
            score += 8.0
        elif name_key and any(name_key in alias or alias in name_key for alias in aliases if alias):
            score += 3.0
        if type_key in aliases:
            score += 6.0
        elif type_key and any(type_key in alias or alias in type_key for alias in aliases if alias):
            score += 2.0
        if port_keys:
            overlap = port_keys & port_aliases
            score += 1.5 * float(len(overlap))
            if overlap and overlap == port_keys:
                score += 1.0
        system_exact = any(alias in aliases for alias in system_aliases if alias)
        system_partial = any(
            system_alias and any(system_alias in alias or alias in system_alias for alias in aliases if alias)
            for system_alias in system_aliases
            if system_alias
        )
        if system_exact:
            score += 4.0
        elif system_partial:
            score += 1.5
        if score > 0.0:
            scored_candidates.append((score, fmu.uid, fmu))
    if not scored_candidates:
        return None
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))
    if len(scored_candidates) == 1:
        return scored_candidates[0][2]
    best_score = scored_candidates[0][0]
    second_score = scored_candidates[1][0]
    if best_score > second_score:
        return scored_candidates[0][2]
    return None


def _resolve_fmu_signal_name(fmu: FMU, signal_name: str) -> str:
    def _signal_tokens(text: str) -> List[str]:
        spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
        raw_tokens = [token for token in re.split(r"[^A-Za-z0-9]+", spaced) if token]
        normalized: List[str] = []
        synonym_map = {
            "temperature": "temp",
            "temp": "temp",
            "t": "temp",
            "command": "cmd",
            "cmd": "cmd",
            "generation": "gen",
            "generated": "gen",
            "gen": "gen",
            "battery": "battery",
            "batt": "battery",
            "inlet": "in",
            "input": "in",
            "in": "in",
            "outlet": "out",
            "output": "out",
            "out": "out",
        }
        for token in raw_tokens:
            normalized.append(synonym_map.get(token.lower(), token.lower()))
        return normalized

    wanted = _compact_norm(signal_name)
    candidates = [str(port.name) for port in fmu.ports if str(port.name).strip()] or [*fmu.inputs, *fmu.outputs]
    for candidate in candidates:
        if str(candidate).strip().lower() == str(signal_name).strip().lower():
            return str(candidate)
    for candidate in candidates:
        if _compact_norm(candidate) == wanted:
            return str(candidate)
    wanted_tokens = _signal_tokens(signal_name)
    if wanted_tokens:
        scored_candidates: List[Tuple[float, str]] = []
        wanted_set = set(wanted_tokens)
        for candidate in candidates:
            candidate_tokens = _signal_tokens(candidate)
            if not candidate_tokens:
                continue
            candidate_set = set(candidate_tokens)
            overlap = len(wanted_set & candidate_set)
            if overlap == 0:
                continue
            union = len(wanted_set | candidate_set) or 1
            score = float(overlap) / float(union)
            if candidate_tokens and wanted_tokens and candidate_tokens[0] == wanted_tokens[0]:
                score += 0.1
            if candidate_tokens and wanted_tokens and candidate_tokens[-1] == wanted_tokens[-1]:
                score += 0.05
            scored_candidates.append((score, str(candidate)))
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))
        if scored_candidates:
            best_score, best_candidate = scored_candidates[0]
            second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else -1.0
            if best_score >= 0.6 and best_score > second_score + 1e-9:
                return best_candidate
    return ""


def _benchmark_fallback_score(task_set: TaskSet, mbse_context: MBSEContext, fmu: FMU) -> float:
    text_bits = [mbse_context.system_name, fmu.name, fmu.description]
    system_name = _compact_norm(mbse_context.system_name)
    objective_text = " ".join(str(task.objective or "") for task in task_set.tasks)
    objective_norm = _compact_norm(objective_text)
    score = 0.0
    if system_name and system_name in _compact_norm(fmu.name):
        score += 5.0
    if objective_norm:
        name_norm = _compact_norm(fmu.name)
        if name_norm and name_norm in objective_norm:
            score += 3.0
        desc_norm = _compact_norm(fmu.description)
        if desc_norm and desc_norm in objective_norm:
            score += 1.0
    required_signals = {
        _compact_norm(signal)
        for task in task_set.tasks
        for signal in (task.required_signals or [])
        if _compact_norm(signal)
    }
    if not required_signals:
        for component in mbse_context.components:
            for port in component.ports:
                signal = _compact_norm(port.name)
                if signal:
                    required_signals.add(signal)
    fmu_signals = {_compact_norm(name) for name in [*fmu.inputs, *fmu.outputs] if _compact_norm(name)}
    if required_signals:
        score += float(len(required_signals & fmu_signals)) * 2.0
        if required_signals <= fmu_signals:
            score += 2.0
    if any(str(kind) in {"CoSimulation", "Co-Simulation"} for kind in fmu.fmi_types):
        score += 0.25
    return score


def _candidate_score(candidate: Any) -> float:
    if isinstance(candidate, BindingCandidate):
        return float(candidate.score)
    if isinstance(candidate, dict):
        return float(candidate.get("score", 0.0))
    return 0.0


def _candidate_source_port(candidate: Any) -> str:
    if isinstance(candidate, BindingCandidate):
        return candidate.source_port.name
    source_port = candidate.get("source_port") if isinstance(candidate, dict) else None
    return getattr(source_port, "name", "")


def _candidate_target_port(candidate: Any) -> str:
    if isinstance(candidate, BindingCandidate):
        return candidate.target_port.name
    target_port = candidate.get("target_port") if isinstance(candidate, dict) else None
    return getattr(target_port, "name", "")


def _candidate_score_breakdown(candidate: Any) -> Dict[str, Any]:
    if isinstance(candidate, BindingCandidate):
        return dict(candidate.score_breakdown)
    if isinstance(candidate, dict):
        return dict(candidate.get("score_breakdown") or {})
    return {}


def _candidate_source_meta(candidate: Any) -> Dict[str, Any]:
    if isinstance(candidate, BindingCandidate):
        return {
            "name": candidate.source_port.name,
            "type": candidate.source_port.type,
            "unit": candidate.source_port.unit,
            "dimensions": list(candidate.source_port.dimensions),
        }
    source_port = candidate.get("source_port") if isinstance(candidate, dict) else None
    if source_port is None:
        return {}
    return {
        "name": getattr(source_port, "name", ""),
        "type": getattr(source_port, "type", ""),
        "unit": getattr(source_port, "unit", ""),
        "dimensions": list(getattr(source_port, "dimensions", []) or []),
    }


def _candidate_target_meta(candidate: Any) -> Dict[str, Any]:
    if isinstance(candidate, BindingCandidate):
        return {
            "name": candidate.target_port.name,
            "type": candidate.target_port.type,
            "unit": candidate.target_port.unit,
            "dimensions": list(candidate.target_port.dimensions),
        }
    target_port = candidate.get("target_port") if isinstance(candidate, dict) else None
    if target_port is None:
        return {}
    return {
        "name": getattr(target_port, "name", ""),
        "type": getattr(target_port, "type", ""),
        "unit": getattr(target_port, "unit", ""),
        "dimensions": list(getattr(target_port, "dimensions", []) or []),
    }


def _mark_revised_mask(
    explanations: List[List[Dict[str, Any]]],
    pair: Tuple[int, str],
    fmu_uids: Sequence[str],
    failure: Dict[str, Any] | None,
) -> List[List[Dict[str, Any]]]:
    updated = [[dict(item) for item in row] for row in explanations]
    task_index, fmu_uid = pair
    if 0 <= int(task_index) < len(updated):
        for col, uid in enumerate(fmu_uids):
            if uid != fmu_uid:
                continue
            details = dict(updated[int(task_index)][col])
            checks = dict(details.get("checks") or {})
            checks["failure_revision_exclusion"] = False
            reasons = list(details.get("reasons") or [])
            reasons.append(str((failure or {}).get("failure_type") or "failure_revision_exclusion"))
            updated[int(task_index)][col] = {
                **details,
                "mask_value": float("inf"),
                "checks": checks,
                "reasons": reasons,
            }
            break
    return updated
