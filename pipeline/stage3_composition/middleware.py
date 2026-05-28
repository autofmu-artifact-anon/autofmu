"""Middleware synthesis and graph rewriting for Stage 3."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pipeline.llm_guidance import build_strict_json_system_prompt, goal_is_aligned, unique_strings
from pipeline.llm_client import chat_json
from pipeline.types import AdapterSpec, DiscrepancyEdge, FMU, MBSEContext, OrchestrationGraph, PortBinding

from .adapter_artifact import build_adapter_artifact
from .ports import infer_adapter_transform, normalize_transform


_ALLOWED_ADAPTER_KINDS = {
    "dimension_adapter",
    "unit_transform_adapter",
    "mode_signal_adapter",
    "type_adapter",
}
_ALLOWED_TRANSFORM_KEYS = {
    "aggregation",
    "expression",
    "mapping",
    "offset",
    "scale",
    "source_dimension",
    "source_dimensions",
    "source_mode",
    "source_type",
    "source_unit",
    "target_dimension",
    "target_dimensions",
    "target_mode",
    "target_type",
    "target_unit",
    "transform_kind",
}


def synthesize_adapter_spec(
    discrepancy: DiscrepancyEdge,
    binding: PortBinding,
    source_fmu: FMU,
    target_fmu: FMU,
    mbse_context: MBSEContext,
) -> AdapterSpec:
    fallback_transform = normalize_transform(infer_adapter_transform(discrepancy.kind, discrepancy.details))
    payload = _llm_adapter_payload(discrepancy, binding, source_fmu, target_fmu, mbse_context)
    transform = normalize_transform(payload.get("transform")) if isinstance(payload.get("transform"), dict) else fallback_transform
    stateful = bool(payload.get("stateful")) if "stateful" in payload else discrepancy.kind == "mode_signal_adapter"
    adapter_id = f"adapter_{discrepancy.chain_id or 'chainless'}_{binding.source_fmu}_{binding.target_fmu}_{binding.source_signal}_{binding.target_signal}"
    inserted_node_id = adapter_id
    source_meta = dict(discrepancy.source_port_meta)
    target_meta = dict(discrepancy.target_port_meta)
    return AdapterSpec(
        adapter_id=adapter_id,
        kind=str(payload.get("kind") or discrepancy.kind),
        source=f"{binding.source_fmu}.{binding.source_signal}",
        target=f"{binding.target_fmu}.{binding.target_signal}",
        transform=transform,
        stateful=stateful,
        artifact_kind="",
        artifact_path="",
        inserted_node_id=inserted_node_id,
        io_contract={
            "inputs": _contract_ports_for_binding(
                prefix="input",
                signal_name=binding.source_signal,
                endpoint=binding.source_fmu,
                port_meta=source_meta,
                fallback_dimensions=discrepancy.details.get("source_dimensions"),
            ),
            "outputs": _contract_ports_for_binding(
                prefix="output",
                signal_name=binding.target_signal,
                endpoint=binding.target_fmu,
                port_meta=target_meta,
                fallback_dimensions=discrepancy.details.get("target_dimensions"),
            ),
            "stateful": stateful,
            "transform_kind": transform.get("transform_kind", "pass_through"),
        },
        generation_source="llm" if payload else "deterministic",
        notes=payload.get(
            "notes",
            [
                f"generated_for={binding.source_fmu}->{binding.target_fmu}",
                f"chain_id={discrepancy.chain_id or 'chainless'}",
            ],
        ),
    )


def materialize_adapter_artifact(adapter_spec: AdapterSpec, *, out_dir: Path) -> AdapterSpec:
    artifact = build_adapter_artifact(adapter_spec, out_dir=out_dir)
    artifact_path = artifact.get("fmu_path") or artifact.get("glue_py")
    artifact_kind = "proxy_fmu" if artifact.get("fmu_path") else "glue_code"
    return replace(adapter_spec, artifact_kind=artifact_kind, artifact_path=str(artifact_path or ""))
def rewrite_graph_with_adapters(graph: OrchestrationGraph, adapters: List[AdapterSpec]) -> Tuple[OrchestrationGraph, List[Dict[str, object]]]:
    adapter_map = {(adapter.source, adapter.target): adapter for adapter in adapters}
    bindings: List[PortBinding] = []
    connection_records: List[Dict[str, object]] = []
    nodes = set(graph.nodes)
    for binding in graph.bindings:
        key = (f"{binding.source_fmu}.{binding.source_signal}", f"{binding.target_fmu}.{binding.target_signal}")
        adapter = adapter_map.get(key)
        if adapter is None:
            bindings.append(binding)
            connection_records.append(
                {
                    "source": f"{binding.source_fmu}.{binding.source_signal}",
                    "target": f"{binding.target_fmu}.{binding.target_signal}",
                    "kind": "direct",
                    "chain_id": binding.chain_id,
                    "segment_id": binding.segment_id,
                }
            )
            continue
        nodes.add(adapter.inserted_node_id)
        input_name = _primary_contract_name(adapter.io_contract, "inputs", "input")
        output_name = _primary_contract_name(adapter.io_contract, "outputs", "output")
        bindings.extend(
            [
                PortBinding(
                    source_fmu=binding.source_fmu,
                    source_signal=binding.source_signal,
                    target_fmu=adapter.inserted_node_id,
                    target_signal=input_name,
                    score=binding.score,
                    reasons=list(binding.reasons) + ["adapter_inserted"],
                ),
                PortBinding(
                    source_fmu=adapter.inserted_node_id,
                    source_signal=output_name,
                    target_fmu=binding.target_fmu,
                    target_signal=binding.target_signal,
                    score=binding.score,
                    reasons=list(binding.reasons) + ["adapter_inserted"],
                ),
            ]
        )
        connection_records.extend(
            [
                {
                    "source": f"{binding.source_fmu}.{binding.source_signal}",
                    "target": f"{adapter.inserted_node_id}.{input_name}",
                    "kind": "adapter_in",
                    "adapter_id": adapter.adapter_id,
                    "transform_kind": adapter.transform.get("transform_kind", "pass_through"),
                    "chain_id": binding.chain_id,
                    "segment_id": binding.segment_id,
                },
                {
                    "source": f"{adapter.inserted_node_id}.{output_name}",
                    "target": f"{binding.target_fmu}.{binding.target_signal}",
                    "kind": "adapter_out",
                    "adapter_id": adapter.adapter_id,
                    "transform_kind": adapter.transform.get("transform_kind", "pass_through"),
                    "chain_id": binding.chain_id,
                    "segment_id": binding.segment_id,
                },
            ]
        )
    return (
        OrchestrationGraph(
            nodes=sorted(nodes),
            port_nodes=list(graph.port_nodes),
            bindings=bindings,
            component_to_fmu=dict(graph.component_to_fmu),
            required_signal_chains=list(graph.required_signal_chains),
            binding_candidates=list(graph.binding_candidates),
            closure_ok=graph.closure_ok,
            closure_failures=list(graph.closure_failures),
            routing_failures=list(graph.routing_failures),
            diagnostics={**dict(graph.diagnostics), "adapter_count": len(adapters)},
        ),
        connection_records,
    )


def _contract_ports_for_binding(
    *,
    prefix: str,
    signal_name: str,
    endpoint: str,
    port_meta: Dict[str, Any],
    fallback_dimensions: object,
) -> List[Dict[str, object]]:
    dimensions = _normalize_dimensions(port_meta.get("dimensions") if isinstance(port_meta, dict) else fallback_dimensions)
    count = max(_dimension_width(dimensions), 1)
    names = [prefix] + [f"{prefix}_{index}" for index in range(1, count)]
    return [
        {
            "name": name,
            "channel_index": index,
            "signal_name": signal_name,
            "endpoint": endpoint,
            "port_meta": dict(port_meta),
            "dtype": port_meta.get("type", "Real"),
            "unit": port_meta.get("unit", ""),
            "dimensions": list(dimensions),
            "semantic_role": "channelized" if count > 1 else "primary",
        }
        for index, name in enumerate(names)
    ]


def _normalize_dimensions(raw: object) -> List[int]:
    if isinstance(raw, list):
        dims: List[int] = []
        for item in raw:
            try:
                dims.append(int(item))
            except (TypeError, ValueError):
                continue
        return dims
    try:
        if raw is None or raw == "":
            return []
        return [int(raw)]
    except (TypeError, ValueError):
        return []


def _dimension_width(dimensions: List[int]) -> int:
    width = 1
    for dim in dimensions:
        if dim > 0:
            width *= dim
    return width


def _primary_contract_name(io_contract: Dict[str, object], key: str, fallback: str) -> str:
    items = io_contract.get(key) if isinstance(io_contract, dict) else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name:
                    return name
    return fallback


def _contract_ports(items: object, *, causality: str) -> List[PortMeta]:
    ports: List[PortMeta] = []
    if not isinstance(items, list):
        return ports
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        ports.append(
            PortMeta(
                name=name,
                causality=causality,
                type=str(item.get("dtype") or "Real"),
                unit=str(item.get("unit") or ""),
                dimensions=[int(x) for x in item.get("dimensions", []) if isinstance(x, int)],
                description=str(item.get("target") or item.get("source") or ""),
            )
        )
    return ports


def _llm_adapter_payload(
    discrepancy: DiscrepancyEdge,
    binding: PortBinding,
    source_fmu: FMU,
    target_fmu: FMU,
    mbse_context: MBSEContext,
) -> Dict[str, object]:
    task_goal = (
        f"Synthesize the minimal valid adapter spec that repairs discrepancy "
        f"{discrepancy.kind} on edge {binding.source_fmu}.{binding.source_signal} -> "
        f"{binding.target_fmu}.{binding.target_signal} without changing the task intent."
    )
    fallback_transform = normalize_transform(infer_adapter_transform(discrepancy.kind, discrepancy.details))
    system_prompt = build_strict_json_system_prompt(
        role="an FMI middleware synthesis assistant",
        task_goal=task_goal,
        output_contract=[
            'Top-level keys: "task_goal_summary", "kind", "transform", "stateful", and "notes".',
            f'"kind" must be one of: {", ".join(sorted(_ALLOWED_ADAPTER_KINDS))}.',
            '"transform" must be a JSON object that only contains fields supported by the discrepancy details.',
            '"stateful" must be a boolean.',
            '"notes" must be a short list of implementation notes.',
        ],
        validity_rules=[
            "Do not invent new signals, units, dimensions, or execution semantics not present in the discrepancy details.",
            "The adapter must solve only the current edge mismatch, not redesign the model.",
            "If uncertain, keep the discrepancy kind and reuse the conservative fallback transform.",
            "Return compact notes and avoid generic explanations.",
        ],
    )
    user_prompt = json.dumps(
        {
            "current_task_goal": task_goal,
            "mbse_system": mbse_context.system_name,
            "source_fmu": {"uid": source_fmu.uid, "name": source_fmu.name, "description": source_fmu.description},
            "target_fmu": {"uid": target_fmu.uid, "name": target_fmu.name, "description": target_fmu.description},
            "edge": {
                "chain_id": discrepancy.chain_id,
                "segment_id": discrepancy.segment_id,
                "source_signal": binding.source_signal,
                "target_signal": binding.target_signal,
                "discrepancy_kind": discrepancy.kind,
                "details": discrepancy.details,
                "preservation_evidence": discrepancy.preservation_evidence,
                "source_port_meta": discrepancy.source_port_meta,
                "target_port_meta": discrepancy.target_port_meta,
                "local_mbse_context": discrepancy.local_mbse_context,
                "binding_score_breakdown": binding.score_breakdown,
            },
            "allowed_kinds": sorted(_ALLOWED_ADAPTER_KINDS),
            "fallback_transform": fallback_transform,
        },
        ensure_ascii=False,
    )
    response = chat_json(system_prompt, user_prompt, temperature=0.15, max_tokens=900)
    return _sanitize_adapter_payload(
        response,
        task_goal=task_goal,
        discrepancy_kind=discrepancy.kind,
        fallback_transform=fallback_transform,
    )


def _sanitize_adapter_payload(
    response: object,
    *,
    task_goal: str,
    discrepancy_kind: str,
    fallback_transform: Dict[str, object],
) -> Dict[str, object]:
    if not isinstance(response, dict):
        return {}
    goal_summary = str(response.get("task_goal_summary") or "").strip()
    if not goal_is_aligned(goal_summary, task_goal, min_common_tokens=2, min_overlap=0.15):
        return {}
    kind = str(response.get("kind") or "").strip()
    if kind not in _ALLOWED_ADAPTER_KINDS:
        kind = discrepancy_kind if discrepancy_kind in _ALLOWED_ADAPTER_KINDS else ""
    transform = _sanitize_transform(response.get("transform"), fallback_transform)
    stateful = bool(response.get("stateful")) if "stateful" in response else discrepancy_kind == "mode_signal_adapter"
    notes = unique_strings(response.get("notes", []) if isinstance(response.get("notes"), list) else [])
    return {
        "kind": kind or discrepancy_kind,
        "transform": transform,
        "stateful": stateful,
        "notes": notes[:3] or [f"llm_goal={goal_summary}"],
    }


def _sanitize_transform(raw_transform: object, fallback_transform: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(raw_transform, dict):
        return dict(fallback_transform)
    cleaned = dict(fallback_transform)
    for key, value in raw_transform.items():
        name = str(key or "").strip()
        if not name or name not in _ALLOWED_TRANSFORM_KEYS:
            continue
        normalized = _sanitize_json_value(value)
        if normalized is None:
            continue
        cleaned[name] = normalized
    return normalize_transform(cleaned)


def _sanitize_json_value(value: object) -> object | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        cleaned = []
        for item in value[:8]:
            normalized = _sanitize_json_value(item)
            if normalized is not None:
                cleaned.append(normalized)
        return cleaned
    if isinstance(value, dict):
        cleaned_dict: Dict[str, object] = {}
        for key, item in list(value.items())[:16]:
            name = str(key or "").strip()
            if not name:
                continue
            normalized = _sanitize_json_value(item)
            if normalized is not None:
                cleaned_dict[name] = normalized
        return cleaned_dict
    return None
