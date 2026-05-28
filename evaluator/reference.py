from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from dataset.common import read_json
from pipeline.dataset_loader import LoadedCase

from .canonical import canonicalize_solution
from .types import ReferencePack


def _string_list(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _scalar_mapping(mapping: Mapping[str, Any] | None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in (mapping or {}).items():
        name = str(key).strip()
        if not name:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[name] = value
    return out


def _declared_scenario_window(case_payload: Mapping[str, Any], verification_requirement: Mapping[str, Any]) -> Dict[str, Any]:
    requirement = case_payload.get("requirement") if isinstance(case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    scenario_window = (
        verification_requirement.get("scenario_window")
        if isinstance(verification_requirement.get("scenario_window"), dict)
        else {}
    )
    out: Dict[str, Any] = {}
    for key in ("start_time", "stop_time", "step_size"):
        if scenario_window.get(key) is not None:
            out[key] = scenario_window.get(key)
    if out.get("start_time") is None and scenario.get("t_start_s") is not None:
        out["start_time"] = scenario.get("t_start_s")
    if out.get("stop_time") is None and scenario.get("t_end_s") is not None:
        out["stop_time"] = scenario.get("t_end_s")
    return out


def build_reference_pack(loaded: LoadedCase) -> ReferencePack:
    case_payload = loaded.case_payload
    solution_payload = loaded.solution_payload
    evaluation_artifacts = loaded.evaluation_artifacts
    verification_requirement = dict(loaded.verification_requirement_payload)
    verification_result = dict(loaded.verification_result_payload)
    trajectory_manifest = dict(loaded.trajectory_manifest_payload)
    requirement = case_payload.get("requirement") if isinstance(case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    retrieval_reference_relpath = str(evaluation_artifacts.get("retrieval_reference_relpath") or "").strip()
    retrieval_reference_path = (
        (loaded.case_root / retrieval_reference_relpath).resolve() if retrieval_reference_relpath else None
    )

    retrieval_reference: Dict[str, Any]
    if retrieval_reference_path is not None and retrieval_reference_path.exists():
        retrieval_reference = dict(read_json(retrieval_reference_path))
    else:
        selected_asset_ids = _string_list(
            solution_payload.get("selected_asset_ids", case_payload.get("ground_truth_asset_ids", []))
        )
        candidate_asset_ids = _string_list(case_payload.get("candidate_asset_ids", []))
        retrieval_reference = {
            "selected_asset_ids": sorted(set(selected_asset_ids)),
            "ground_truth_asset_ids": sorted(_string_list(case_payload.get("ground_truth_asset_ids", []))),
            "candidate_asset_ids": sorted(set(candidate_asset_ids)),
            "acceptable_asset_sets": [sorted(set(selected_asset_ids))] if selected_asset_ids else [],
            "oracle_mode": "exact_asset_set",
            "equivalence_class_id": "",
            "orchestration_signature": canonicalize_solution(solution_payload),
        }

    return ReferencePack(
        case_id=loaded.case_id,
        retrieval_reference=retrieval_reference,
        solution=dict(solution_payload),
        verification_requirement=verification_requirement,
        verification_result=verification_result,
        trajectory_manifest=trajectory_manifest,
        ground_truth_trajectory_path=(
            loaded.ground_truth_trajectory_path.as_posix() if loaded.ground_truth_trajectory_path else None
        ),
        input_trajectory_path=loaded.input_trajectory_path.as_posix() if loaded.input_trajectory_path else None,
        declared_scenario_window=_declared_scenario_window(case_payload, verification_requirement),
        declared_initial_conditions=_scalar_mapping(
            scenario.get("initial_conditions") if isinstance(scenario.get("initial_conditions"), dict) else {}
        ),
        supports_execution_metrics=bool(evaluation_artifacts.get("supports_execution_metrics")),
        supports_numerical_fidelity=bool(evaluation_artifacts.get("supports_numerical_fidelity")),
        supports_decision_accuracy=bool(evaluation_artifacts.get("supports_decision_accuracy")),
        metadata={
            "source_type": case_payload.get("source_type"),
            "expected_behavior": case_payload.get("expected_behavior"),
            "title": case_payload.get("title"),
            "evaluation_artifacts": dict(evaluation_artifacts),
        },
    )
