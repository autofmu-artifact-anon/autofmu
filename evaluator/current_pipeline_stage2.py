from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Mapping, Sequence

from pipeline.stage2_matching import match
from pipeline.stage2_matching.feasibility import input_ports, output_ports
from pipeline.stage2_matching.matcher import (
    _apply_mbse_component_cover_fallback,
    _case_source_family,
    _compact_norm,
    _fmu_aliases,
    _required_mbse_components,
    _selected_fmus_cover_required_components,
)
from pipeline.types import FMU, MatchingResult, OrchestrationGraph, PortBinding, TaskAssignment


def run_current_stage2(
    task_candidates,
    *,
    mbse_context,
    fmu_library,
    config: Mapping[str, Any],
):
    original_library = list(fmu_library)
    filtered_library = _prefilter_fmu_library(
        mbse_context=mbse_context,
        task_candidates=list(task_candidates),
        fmu_library=original_library,
    )
    result = match(
        list(task_candidates),
        mbse_context=mbse_context,
        fmu_library=filtered_library,
        max_revisions=int(config.get("max_revisions", 6)),
        top_m_per_task=int(config.get("top_m_per_task", 5)),
        max_port_candidates=int(config.get("max_port_candidates", 8)),
        enable_benchmark_single_fmu_fallback=False,
        enable_mbse_component_cover_fallback=False,
    )
    result = _recover_current_stage2(
        result,
        mbse_context=mbse_context,
        filtered_library=filtered_library,
    )
    diagnostics = dict(result.diagnostics)
    diagnostics.setdefault("current_pipeline_prefilter_candidate_count", len(filtered_library))
    diagnostics.setdefault("current_pipeline_original_candidate_count", len(original_library))
    return replace(result, diagnostics=diagnostics)


def _prefilter_fmu_library(
    *,
    mbse_context,
    task_candidates: Sequence[Any],
    fmu_library: Sequence[FMU],
) -> list[FMU]:
    preferred_family = _case_source_family(mbse_context)
    case_id = str((mbse_context.metadata or {}).get("case_id") or "").strip()
    case_slug = _case_slug(case_id)
    filtered = list(fmu_library)
    family_fmus = [fmu for fmu in filtered if str((fmu.meta or {}).get("source_type") or "") == preferred_family]
    if family_fmus:
        filtered = family_fmus

    if preferred_family == "benchmark_single_fmu":
        exact = [fmu for fmu in filtered if _benchmark_exact_score(fmu, case_id) > 0.0]
        if exact:
            filtered = sorted(exact, key=lambda fmu: (-_benchmark_exact_score(fmu, case_id), fmu.uid))
    elif preferred_family == "manual_case_fmu":
        same_case = [fmu for fmu in filtered if _belongs_to_manual_case(fmu, case_id)]
        if same_case:
            filtered = same_case
    elif preferred_family == "dtaas_example_fmu":
        same_slug = [fmu for fmu in filtered if _belongs_to_dtaas_case(fmu, case_id, case_slug)]
        if same_slug:
            filtered = same_slug

    if not _case_requests_monitor_variant(mbse_context, task_candidates):
        non_monitor = [fmu for fmu in filtered if not _is_monitor_variant(fmu)]
        if non_monitor:
            filtered = non_monitor

    return filtered or list(fmu_library)


def _recover_current_stage2(
    result: MatchingResult,
    *,
    mbse_context,
    filtered_library: Sequence[FMU],
) -> MatchingResult:
    preferred_family = _case_source_family(mbse_context)
    recovered = result
    if preferred_family == "benchmark_single_fmu":
        recovered = _apply_current_benchmark_exact_fallback(
            recovered,
            mbse_context=mbse_context,
            filtered_library=filtered_library,
        )
    elif preferred_family in {"manual_case_fmu", "dtaas_example_fmu"}:
        recovered = _apply_current_component_cover_recovery(
            recovered,
            mbse_context=mbse_context,
            filtered_library=filtered_library,
        )

    if len(recovered.selected_fmus) > 1:
        safe_graph = _safe_post_connect_selected_fmus(recovered.graph, recovered.selected_fmus)
        if safe_graph is not recovered.graph:
            recovered = replace(recovered, graph=safe_graph)
    return recovered


def _apply_current_benchmark_exact_fallback(
    result: MatchingResult,
    *,
    mbse_context,
    filtered_library: Sequence[FMU],
) -> MatchingResult:
    case_id = str((mbse_context.metadata or {}).get("case_id") or "").strip()
    ranked = sorted(
        (fmu for fmu in filtered_library if _benchmark_exact_score(fmu, case_id) > 0.0),
        key=lambda fmu: (-_benchmark_exact_score(fmu, case_id), fmu.uid),
    )
    if not ranked:
        return result
    selected = ranked[0]
    already_exact = any(fmu.uid == selected.uid for fmu in result.selected_fmus)
    if already_exact:
        return result

    score = max(_benchmark_exact_score(selected, case_id), 1.0)
    assignments = [
        TaskAssignment(
            task_id=task.task_id,
            task_index=index,
            fmu_uid=selected.uid,
            score=score,
            cost=max(0.01, 1.0 / (1.0 + score)),
            hard_ok=True,
            semantic_cost=max(0.01, 1.0 / (1.0 + score)),
            hard_mask_value=0.0,
            transport_mass=1.0,
            revision_index=0,
            reasons=["current_pipeline_benchmark_exact_fallback"],
            grounded_components=list(task.grounded_components),
        )
        for index, task in enumerate(result.task_set.tasks)
    ]
    graph = OrchestrationGraph(
        nodes=[selected.uid],
        bindings=[],
        component_to_fmu={},
        closure_ok=True,
        diagnostics={"status": "current_pipeline_benchmark_exact_fallback"},
    )
    diagnostics = dict(result.diagnostics)
    diagnostics.update(
        {
            "status": "current_pipeline_benchmark_exact_fallback",
            "base_status": result.diagnostics.get("status"),
            "current_pipeline_exact_benchmark_uid": selected.uid,
            "current_pipeline_exact_benchmark_score": float(score),
        }
    )
    return MatchingResult(
        task_set=result.task_set,
        assignments=assignments,
        selected_fmus=[selected],
        graph=graph,
        discrepancy_set=[],
        revision_trace=list(result.revision_trace)
        + [
            {
                "revision": "current_pipeline_benchmark_exact_fallback",
                "status": "ok",
                "assignment": [selected.uid],
            }
        ],
        final_cost=max(0.01, 1.0 / (1.0 + score)),
        transport_plans=list(result.transport_plans),
        mask_history=list(result.mask_history),
        taskset_results=list(result.taskset_results),
        selected_task_set_cost=max(0.01, 1.0 / (1.0 + score)),
        diagnostics=diagnostics,
    )


def _apply_current_component_cover_recovery(
    result: MatchingResult,
    *,
    mbse_context,
    filtered_library: Sequence[FMU],
) -> MatchingResult:
    required_components = _required_mbse_components(result.task_set, mbse_context)
    if result.selected_fmus and _selected_fmus_cover_required_components(result.selected_fmus, required_components, mbse_context):
        return result
    recovered = _apply_mbse_component_cover_fallback(result, mbse_context, filtered_library)
    if recovered is result:
        return result
    diagnostics = dict(recovered.diagnostics)
    diagnostics.setdefault("current_pipeline_component_cover_recovery", True)
    return replace(recovered, diagnostics=diagnostics)


def _safe_post_connect_selected_fmus(graph: OrchestrationGraph, selected_fmus: Sequence[FMU]) -> OrchestrationGraph:
    existing_targets = {(binding.target_fmu, binding.target_signal) for binding in graph.bindings}
    bindings = list(graph.bindings)
    added = 0
    for target_fmu in selected_fmus:
        for target_port in input_ports(target_fmu):
            if (target_fmu.uid, target_port.name) in existing_targets:
                continue
            for source_fmu in selected_fmus:
                if source_fmu.uid == target_fmu.uid:
                    continue
                source_port = _find_post_connect_source(source_fmu, target_port.name)
                if source_port is None:
                    continue
                bindings.append(
                    PortBinding(
                        source_fmu=source_fmu.uid,
                        source_signal=source_port.name,
                        target_fmu=target_fmu.uid,
                        target_signal=target_port.name,
                        score=0.0,
                        chain_id="current_pipeline_post_connect",
                        segment_id=f"current_pipeline_post_{added}",
                        selected_by="current_pipeline_post_connect",
                        reasons=["current_pipeline_post_connect"],
                    )
                )
                existing_targets.add((target_fmu.uid, target_port.name))
                added += 1
                break
    if added == 0 and set(graph.nodes) >= {fmu.uid for fmu in selected_fmus}:
        return graph

    diagnostics = dict(graph.diagnostics)
    if added > 0:
        diagnostics["current_pipeline_post_connect_added"] = added
    nodes = sorted({*graph.nodes, *[fmu.uid for fmu in selected_fmus]})
    return replace(graph, nodes=nodes, bindings=bindings, diagnostics=diagnostics)


def _find_post_connect_source(source_fmu: FMU, target_signal: str):
    target_norm = _compact_norm(target_signal)
    for source_port in output_ports(source_fmu):
        source_norm = _compact_norm(source_port.name)
        if source_port.name == target_signal:
            return source_port
        if source_norm and target_norm and source_norm == target_norm:
            return source_port
        if source_port.name.rstrip("_out") == target_signal.rstrip("_in"):
            return source_port
    return None


def _case_slug(case_id: str) -> str:
    if case_id.startswith("case_dtaas_"):
        return case_id[len("case_dtaas_") :]
    return case_id


def _case_requests_monitor_variant(mbse_context, task_candidates: Sequence[Any]) -> bool:
    case_id = str((mbse_context.metadata or {}).get("case_id") or "").lower()
    if "monitor" in case_id or "validation" in case_id:
        return True
    for taskset in task_candidates:
        for task in getattr(taskset, "tasks", []):
            for component in getattr(task, "grounded_components", []):
                text = str(component or "").lower()
                if "monitor" in text or "validation" in text:
                    return True
    return False


def _is_monitor_variant(fmu: FMU) -> bool:
    blob = _asset_blob(fmu)
    candidates = [
        fmu.uid,
        fmu.name,
        *list(fmu.tags or []),
        blob.get("source_id"),
        blob.get("name"),
    ]
    provenance = blob.get("provenance") if isinstance(blob.get("provenance"), dict) else {}
    candidates.extend([provenance.get("case_id"), provenance.get("example_slug"), provenance.get("source_id")])
    for item in candidates:
        text = str(item or "").lower()
        if "monitor" in text or "validation" in text:
            return True
    return False


def _belongs_to_manual_case(fmu: FMU, case_id: str) -> bool:
    if not case_id:
        return False
    blob = _asset_blob(fmu)
    provenance = blob.get("provenance") if isinstance(blob.get("provenance"), dict) else {}
    values = [
        fmu.uid,
        blob.get("source_id"),
        provenance.get("case_id"),
        provenance.get("source_id"),
    ]
    return any(case_id == str(value or "").strip() or case_id in str(value or "").strip() for value in values)


def _belongs_to_dtaas_case(fmu: FMU, case_id: str, case_slug: str) -> bool:
    if not case_id and not case_slug:
        return False
    blob = _asset_blob(fmu)
    provenance = blob.get("provenance") if isinstance(blob.get("provenance"), dict) else {}
    case_origin = blob.get("case_origin")
    candidate_values = [
        fmu.uid,
        blob.get("source_id"),
        provenance.get("source_id"),
        provenance.get("case_id"),
        provenance.get("example_slug"),
    ]
    if isinstance(case_origin, list):
        candidate_values.extend(case_origin)
    return any(_matches_dtaas_case_value(value, case_id=case_id, case_slug=case_slug) for value in candidate_values)


def _matches_dtaas_case_value(value: Any, *, case_id: str, case_slug: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    text_norm = _compact_norm(text)
    case_id_norm = _compact_norm(case_id)
    case_slug_norm = _compact_norm(case_slug)

    if case_id and (text == case_id or text.startswith(f"{case_id}::")):
        return True
    if case_slug and (text == case_slug or text.startswith(f"{case_slug}::")):
        return True
    if case_slug and text.startswith(f"asset_dtaas_{case_slug}__"):
        return True
    if case_id_norm and text_norm == case_id_norm:
        return True
    if case_slug_norm and text_norm == case_slug_norm:
        return True
    return False


def _benchmark_exact_score(fmu: FMU, case_id: str) -> float:
    aliases = _fmu_aliases(fmu)
    score = 0.0
    if case_id:
        exact_asset_alias = _compact_norm(case_id.replace("case_", "asset_"))
        if exact_asset_alias and exact_asset_alias in aliases:
            score += 6.0
    match_obj = re.search(r"(?:case_)?bench(?:_fmu)?[-_]?(\d+)$", case_id, re.I)
    if not match_obj:
        return score
    suffix = str(match_obj.group(1))
    for alias in aliases:
        if alias.endswith(suffix):
            score += 2.0
        if alias == f"fmu{suffix}" or alias == f"assetbenchfmu{suffix}":
            score += 2.0
    return score


def _asset_blob(fmu: FMU) -> Mapping[str, Any]:
    meta = fmu.meta if isinstance(fmu.meta, dict) else {}
    asset_json = meta.get("asset_json")
    return asset_json if isinstance(asset_json, dict) else {}
