from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from pipeline.stage3_composition import compose
from pipeline.types import CompositionResult, MatchingResult


def run_current_stage3(
    matching_result: MatchingResult,
    *,
    mbse_context,
    config: Mapping[str, Any],
) -> CompositionResult:
    scenario_window = config.get("scenario_window") if isinstance(config.get("scenario_window"), dict) else None
    result = compose(matching_result, mbse_context=mbse_context, scenario_window=scenario_window)
    if _should_disable_loop_wrappers(mbse_context, result):
        result = _strip_loop_wrappers(result)
        result = _annotate_policy(result, "compose_no_loops")
    return result


def _strip_loop_wrappers(result: CompositionResult) -> CompositionResult:
    schedule = dict(result.schedule)
    schedule["loop_wrappers"] = []
    if isinstance(schedule.get("execution_plan"), list):
        schedule["execution_plan"] = [_strip_loop_entry(item) for item in schedule["execution_plan"] if isinstance(item, dict)]

    scheduler = dict(result.simulation_config.scheduler)
    scheduler["loop_wrappers"] = []
    if isinstance(scheduler.get("execution_plan"), list):
        scheduler["execution_plan"] = [_strip_loop_entry(item) for item in scheduler["execution_plan"] if isinstance(item, dict)]

    meta = dict(result.simulation_config.meta)
    payload = dict(meta.get("final_solution_payload") or {})
    payload["loop_resolution"] = []
    meta["final_solution_payload"] = payload
    meta["current_pipeline_stage3_loop_wrappers_disabled"] = True

    simulation_config = replace(result.simulation_config, scheduler=scheduler, meta=meta)
    diagnostics = dict(result.diagnostics)
    diagnostics["current_pipeline_stage3_loop_wrappers_disabled"] = True
    diagnostics["loop_count"] = 0
    return replace(
        result,
        schedule=schedule,
        loop_resolution=[],
        simulation_config=simulation_config,
        diagnostics=diagnostics,
    )


def _strip_loop_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = dict(entry)
    cleaned["loop_ids"] = []
    cleaned["active_loops"] = []
    cleaned["requires_fixed_point_iteration"] = False
    return cleaned


def _should_disable_loop_wrappers(mbse_context, result: CompositionResult) -> bool:
    if not result.loop_resolution:
        return False
    source_type = str((mbse_context.metadata or {}).get("source_type") or "")
    if source_type in {"manual_multi_fmu_case", "dtaas_multi_fmu_case"}:
        return True
    case_id = str((mbse_context.metadata or {}).get("case_id") or "").lower()
    return case_id.startswith("case_manual_") or case_id.startswith("case_dtaas_")


def _annotate_policy(result: CompositionResult, policy: str) -> CompositionResult:
    meta = dict(result.simulation_config.meta)
    meta["current_pipeline_stage3_policy"] = policy
    simulation_config = replace(result.simulation_config, meta=meta)
    diagnostics = dict(result.diagnostics)
    diagnostics["current_pipeline_stage3_policy"] = policy
    return replace(result, simulation_config=simulation_config, diagnostics=diagnostics)
