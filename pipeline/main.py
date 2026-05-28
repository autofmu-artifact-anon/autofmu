"""Unified entrypoint for the requirement + MBSE -> FMU orchestration pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.dataset_loader import load_case_from_dataset
from pipeline.execution import execute_case
from pipeline.fmu_loader import load_fmu_library
from pipeline.monitoring import build_monitored_outputs
from pipeline.scenario_binding import (
    build_external_input_bindings,
    build_initial_condition_bindings,
    derive_execution_order,
)
from pipeline.stage1_decomposition import decompose as decompose_full
from pipeline.stage1_decomposition import decompose_ablation
from pipeline.stage2_matching import match as match_full
from pipeline.stage2_matching import match_ablation
from pipeline.stage3_composition import compose as compose_full
from pipeline.stage3_composition import compose_ablation
from pipeline.types import FMU, MBSEContext, PipelineResult


def _build_predicted_solution(
    *,
    case_id: Optional[str],
    result: PipelineResult,
    case_payload: Optional[Dict[str, Any]] = None,
    verification_requirement_payload: Optional[Dict[str, Any]] = None,
    trajectory_manifest_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    selected_asset_ids = [fmu.uid for fmu in result.selected_fmus]
    task_signals = []
    for task in result.selected_task_set.tasks:
        task_signals.extend(task.required_signals)
    monitored, monitor_warnings = build_monitored_outputs(
        selected_fmus=result.selected_fmus,
        verification_requirement_payload=verification_requirement_payload or {},
        trajectory_manifest_payload=trajectory_manifest_payload or {},
        fallback_signals=sorted({signal for signal in task_signals if signal}),
    )
    requirement = case_payload.get("requirement") if isinstance((case_payload or {}).get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    external_inputs, input_warnings = build_external_input_bindings(
        selected_fmus=result.selected_fmus,
        selected_task_set=result.selected_task_set,
        scenario_inputs=scenario.get("inputs") if isinstance(scenario.get("inputs"), dict) else {},
        verification_requirement_payload=verification_requirement_payload or {},
    )
    initial_conditions, init_warnings = build_initial_condition_bindings(
        selected_fmus=result.selected_fmus,
        selected_task_set=result.selected_task_set,
        initial_conditions=scenario.get("initial_conditions") if isinstance(scenario.get("initial_conditions"), dict) else {},
        verification_requirement_payload=verification_requirement_payload or {},
    )
    execution_order = derive_execution_order(
        selected_fmus=result.selected_fmus,
        selected_task_set=result.selected_task_set,
    )
    return {
        "schema": "UNIFIED_SOLUTION_V1",
        "case_id": case_id or str(result.simulation_config.meta.get("case_id") or "adhoc"),
        "selected_asset_ids": selected_asset_ids,
        "connections": list(result.simulation_config.connections),
        "external_inputs": external_inputs,
        "initial_conditions": initial_conditions,
        "monitored_outputs": monitored,
        "schedule": dict(result.simulation_config.scheduler),
        "execution_order": execution_order,
        "adapters": [asdict(adapter) for adapter in result.composition_result.adapters],
        "loop_resolution": list(result.composition_result.loop_resolution),
        "notes": [
            f"mode={result.diagnostics.get('mode', 'full')}",
            f"selected_fmu_count={len(selected_asset_ids)}",
        ]
        + monitor_warnings
        + input_warnings
        + init_warnings,
    }


def run_pipeline(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    fmu_library: List[FMU],
    case_id: Optional[str] = None,
    case_payload: Optional[Dict[str, Any]] = None,
    verification_requirement_payload: Optional[Dict[str, Any]] = None,
    trajectory_manifest_payload: Optional[Dict[str, Any]] = None,
    mode: str = "full",
    confidence: float = 0.9,
    max_stage2_revisions: int = 6,
    stage2_top_m_per_task: int = 5,
    stage2_max_tasksets: int = 6,
    stage2_max_port_candidates: int = 8,
) -> PipelineResult:
    mode_norm = (mode or "full").strip().lower()

    if mode_norm in {"ablation_stage1", "ablation_all"}:
        task_candidates = decompose_ablation(requirement, mbse_context=mbse_context, confidence=confidence, max_candidates=1)
    else:
        task_candidates = decompose_full(
            requirement,
            mbse_context=mbse_context,
            confidence=confidence,
            max_candidates=stage2_max_tasksets,
        )

    if mode_norm in {"ablation_stage2", "ablation_all"}:
        matching_result = match_ablation(
            task_candidates,
            mbse_context=mbse_context,
            fmu_library=fmu_library,
        )
    else:
        matching_result = match_full(
            task_candidates[: max(stage2_max_tasksets, 1)],
            mbse_context=mbse_context,
            fmu_library=fmu_library,
            max_revisions=max_stage2_revisions,
            top_m_per_task=stage2_top_m_per_task,
            max_port_candidates=stage2_max_port_candidates,
        )

    if mode_norm in {"ablation_stage3", "ablation_all"}:
        composition_result = compose_ablation(matching_result, mbse_context=mbse_context)
    else:
        scenario_window = (
            verification_requirement_payload.get("scenario_window")
            if isinstance(verification_requirement_payload, dict)
            and isinstance(verification_requirement_payload.get("scenario_window"), dict)
            else None
        )
        composition_result = compose_full(
            matching_result,
            mbse_context=mbse_context,
            scenario_window=scenario_window,
        )

    result = PipelineResult(
        task_candidates=task_candidates,
        selected_task_set=matching_result.task_set,
        selected_fmus=matching_result.selected_fmus,
        matching_result=matching_result,
        composition_result=composition_result,
        simulation_config=composition_result.simulation_config,
        predicted_solution={},
        diagnostics={
            "mode": mode_norm,
            "task_candidate_count": len(task_candidates),
            "selected_fmu_count": len(matching_result.selected_fmus),
        },
    )
    predicted_solution = _build_predicted_solution(
        case_id=case_id or str(mbse_context.metadata.get("case_id") or ""),
        result=result,
        case_payload=case_payload,
        verification_requirement_payload=verification_requirement_payload,
        trajectory_manifest_payload=trajectory_manifest_payload,
    )
    return PipelineResult(
        task_candidates=result.task_candidates,
        selected_task_set=result.selected_task_set,
        selected_fmus=result.selected_fmus,
        matching_result=result.matching_result,
        composition_result=result.composition_result,
        simulation_config=result.simulation_config,
        predicted_solution=predicted_solution,
        diagnostics=result.diagnostics,
    )


def run_case(
    case_id: str,
    *,
    dataset_root: str = "dataset",
    manifest_path: str = "pipeline/resources/fmu_library/manifest.json",
    mode: str = "full",
) -> PipelineResult:
    loaded = load_case_from_dataset(case_id, dataset_root=dataset_root)
    library = load_fmu_library(manifest_path)
    return run_pipeline(
        loaded.requirement_text,
        mbse_context=loaded.mbse_context,
        fmu_library=library,
        case_id=loaded.case_id,
        case_payload=loaded.case_payload,
        verification_requirement_payload=loaded.verification_requirement_payload,
        trajectory_manifest_payload=loaded.trajectory_manifest_payload,
        mode=mode,
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.main")
    parser.add_argument("--case-id", required=True, help="Normalized case ID under dataset/cases.")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument("--manifest-path", default="pipeline/resources/fmu_library/manifest.json", help="FMU library manifest.")
    parser.add_argument("--mode", default="full", help="full|ablation_stage1|ablation_stage2|ablation_stage3|ablation_all")
    parser.add_argument("--out", default=None, help="Optional JSON output path.")
    parser.add_argument("--solution-out", default=None, help="Optional solution-shaped JSON output path.")
    parser.add_argument("--execute-out", default=None, help="Optional execution-result JSON output path.")
    args = parser.parse_args()

    loaded = load_case_from_dataset(args.case_id, dataset_root=args.dataset_root)
    library = load_fmu_library(args.manifest_path)
    result = run_pipeline(
        loaded.requirement_text,
        mbse_context=loaded.mbse_context,
        fmu_library=library,
        case_id=loaded.case_id,
        case_payload=loaded.case_payload,
        verification_requirement_payload=loaded.verification_requirement_payload,
        trajectory_manifest_payload=loaded.trajectory_manifest_payload,
        mode=args.mode,
    )
    payload = asdict(result)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.solution_out:
        solution_path = Path(args.solution_out).expanduser().resolve()
        solution_path.write_text(json.dumps(result.predicted_solution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.execute_out:
        execute_path = Path(args.execute_out).expanduser().resolve()
        execution_payload = execute_case(
            loaded=loaded,
            predicted_solution=result.predicted_solution,
            simulation_config=result.simulation_config,
            artifact_root=execute_path.parent,
        )
        execute_path.write_text(json.dumps(execution_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.out and not args.solution_out and not args.execute_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
