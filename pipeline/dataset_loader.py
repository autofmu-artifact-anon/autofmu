"""Load normalized cases from dataset/ for pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataset.common import parse_sysml_model, read_json

from .types import MBSEComponent, MBSEConnection, MBSEContext, MBSEPort


@dataclass(frozen=True)
class LoadedCase:
    case_id: str
    case_root: Path
    case_payload: Dict[str, Any]
    requirement_text: str
    mbse_context: MBSEContext
    solution_payload: Dict[str, Any]
    evaluation_artifacts: Dict[str, Any]
    verification_requirement_payload: Dict[str, Any]
    verification_result_payload: Dict[str, Any]
    trajectory_manifest_payload: Dict[str, Any]
    ground_truth_trajectory_path: Optional[Path]
    input_trajectory_path: Optional[Path]


def _port_from_payload(component_name: str, payload: Dict[str, Any]) -> MBSEPort:
    return MBSEPort(
        component=component_name,
        name=str(payload.get("name") or ""),
        direction=str(payload.get("direction") or "unknown"),
        type_hint=str(payload.get("type") or ""),
        qualified_name=str(payload.get("qualified_name") or payload.get("name") or ""),
    )


def _resolve_sysml_path(case_root: Path, payload: Dict[str, Any], sysml_rel: str) -> Path:
    direct = case_root / sysml_rel
    if direct.exists():
        return direct
    provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    source_root = str(provenance.get("source_root") or "").strip()
    if source_root:
        candidate = case_root.parent.parent / source_root / sysml_rel
        if candidate.exists():
            return candidate
    return direct


def _mbse_context_from_payload(case_root: Path, payload: Dict[str, Any]) -> MBSEContext:
    mbse_blob = payload.get("mbse") if isinstance(payload.get("mbse"), dict) else {}
    sysml_rel = str(mbse_blob.get("sysml_relpath") or "system.sysml")
    sysml_path = _resolve_sysml_path(case_root, payload, sysml_rel)
    parsed = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name) if sysml_path.exists() else {}

    merged = {
        # Prefer a fresh SysML parse when the source model is available; the serialized
        # mbse blob in case.json can become stale when the parser improves.
        "package_name": parsed.get("package_name") or mbse_blob.get("package_name") or case_root.name,
        "system_name": parsed.get("system_name") or mbse_blob.get("system_name") or case_root.name,
        "components": parsed.get("components") or mbse_blob.get("components") or [],
        "adjacency": parsed.get("adjacency") or mbse_blob.get("adjacency") or {},
        "connections": parsed.get("connections") or mbse_blob.get("connections") or [],
        "constraints": parsed.get("constraints") or mbse_blob.get("constraints") or [],
    }

    components: List[MBSEComponent] = []
    for component in merged["components"]:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name") or "")
        comp_type = str(component.get("component_type") or name)
        ports_blob = component.get("ports") if isinstance(component.get("ports"), list) else []
        ports = [_port_from_payload(name, port) for port in ports_blob if isinstance(port, dict)]
        components.append(MBSEComponent(name=name, component_type=comp_type, ports=ports))

    connections: List[MBSEConnection] = []
    for connection in merged["connections"]:
        if not isinstance(connection, dict):
            continue
        connections.append(
            MBSEConnection(
                source_component=str(connection.get("source_component") or ""),
                source_signal=str(connection.get("source_signal") or ""),
                target_component=str(connection.get("target_component") or ""),
                target_signal=str(connection.get("target_signal") or ""),
            )
        )

    return MBSEContext(
        package_name=str(merged["package_name"]),
        system_name=str(merged["system_name"]),
        components=components,
        adjacency={str(k): [str(v) for v in values] for k, values in (merged["adjacency"] or {}).items()},
        connections=connections,
        constraints=[str(x) for x in merged["constraints"]],
        metadata={
            "case_root": str(case_root),
            "sysml_path": str(sysml_path),
            "case_id": str(payload.get("case_id") or case_root.name),
            "source_type": str(payload.get("source_type") or ""),
        },
    )


def load_case(case_dir: str) -> LoadedCase:
    case_root = Path(case_dir).expanduser().resolve()
    case_payload = read_json(case_root / "case.json")
    solution_payload = read_json(case_root / str(case_payload.get("solution_relpath") or "solution.json"))
    evaluation_artifacts = (
        case_payload.get("evaluation_artifacts") if isinstance(case_payload.get("evaluation_artifacts"), dict) else {}
    )
    verification_requirement_relpath = str(evaluation_artifacts.get("verification_requirement_relpath") or "").strip()
    verification_result_relpath = str(evaluation_artifacts.get("verification_result_relpath") or "").strip()
    trajectory_manifest_relpath = str(evaluation_artifacts.get("trajectory_manifest_relpath") or "").strip()
    ground_truth_relpath = str(evaluation_artifacts.get("ground_truth_trajectory_relpath") or "").strip()
    input_relpath = str(evaluation_artifacts.get("input_trajectory_relpath") or "").strip()
    verification_requirement_payload = (
        read_json(case_root / verification_requirement_relpath) if verification_requirement_relpath else {}
    )
    verification_result_payload = read_json(case_root / verification_result_relpath) if verification_result_relpath else {}
    trajectory_manifest_payload = read_json(case_root / trajectory_manifest_relpath) if trajectory_manifest_relpath else {}
    requirement_blob = case_payload.get("requirement") if isinstance(case_payload.get("requirement"), dict) else {}
    requirement_text = str(
        verification_requirement_payload.get("text")
        or requirement_blob.get("text")
        or requirement_blob.get("description")
        or case_payload.get("description")
        or case_payload.get("title")
        or case_root.name
    )
    mbse_context = _mbse_context_from_payload(case_root, case_payload)
    return LoadedCase(
        case_id=str(case_payload.get("case_id") or case_root.name),
        case_root=case_root,
        case_payload=case_payload,
        requirement_text=requirement_text,
        mbse_context=mbse_context,
        solution_payload=solution_payload,
        evaluation_artifacts=dict(evaluation_artifacts),
        verification_requirement_payload=dict(verification_requirement_payload),
        verification_result_payload=dict(verification_result_payload),
        trajectory_manifest_payload=dict(trajectory_manifest_payload),
        ground_truth_trajectory_path=(case_root / ground_truth_relpath).resolve() if ground_truth_relpath else None,
        input_trajectory_path=(case_root / input_relpath).resolve() if input_relpath else None,
    )


def load_case_from_dataset(case_id: str, dataset_root: str = "dataset") -> LoadedCase:
    case_root = Path(dataset_root).expanduser().resolve() / "cases" / case_id
    return load_case(str(case_root))
