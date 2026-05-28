"""Helpers for emitting evaluator-driven dataset artifacts."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from dataset.common import ensure_symlink, slugify, write_json


def ordered_unique(items: Iterable[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for item in items:
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def ordered_unique_text(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def read_csv_columns(path: Path) -> List[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        try:
            header = next(csv.reader(handle))
        except StopIteration:
            return []
    return [str(item or "").strip().strip('"') for item in header if str(item or "").strip()]


def choose_benchmark_trajectory_source(*, source_dir: Path, stem: str) -> Dict[str, Any]:
    ref_path = source_dir / f"{stem}_ref.csv"
    series_path = source_dir / f"{stem}.timeseries.csv"
    input_path = source_dir / f"{stem}_in.csv"
    if ref_path.exists():
        ground_truth = ref_path
        source_kind = "benchmark_ref_csv"
    elif series_path.exists():
        ground_truth = series_path
        source_kind = "benchmark_timeseries_csv"
    else:
        ground_truth = None
        source_kind = "none"
    return {
        "ground_truth_source": ground_truth,
        "input_source": input_path if input_path.exists() else None,
        "source_kind": source_kind,
    }


def schedule_window(case_payload: Mapping[str, Any], solution_payload: Mapping[str, Any]) -> Dict[str, Any]:
    requirement = case_payload.get("requirement") if isinstance(case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    window: Dict[str, Any] = {}
    if scenario.get("t_start_s") is not None:
        window["start_time"] = scenario.get("t_start_s")
    if scenario.get("t_end_s") is not None:
        window["stop_time"] = scenario.get("t_end_s")

    schedule = solution_payload.get("schedule") if isinstance(solution_payload.get("schedule"), dict) else {}
    co_sim = schedule.get("co_simulation") if isinstance(schedule.get("co_simulation"), dict) else {}
    if window.get("start_time") is None and schedule.get("start_time") is not None:
        window["start_time"] = schedule.get("start_time")
    if window.get("stop_time") is None and schedule.get("stop_time") is not None:
        window["stop_time"] = schedule.get("stop_time")
    if window.get("start_time") is None and co_sim.get("start_time") is not None:
        window["start_time"] = co_sim.get("start_time")
    if window.get("stop_time") is None and co_sim.get("stop_time") is not None:
        window["stop_time"] = co_sim.get("stop_time")
    if schedule.get("step_size") is not None:
        window["step_size"] = schedule.get("step_size")
    elif co_sim.get("step_size") is not None:
        window["step_size"] = co_sim.get("step_size")
    return {key: value for key, value in window.items() if value is not None}


def monitored_signal_names(solution_payload: Mapping[str, Any]) -> List[str]:
    monitored = solution_payload.get("monitored_outputs") if isinstance(solution_payload.get("monitored_outputs"), list) else []
    names: List[str] = []
    for item in monitored:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("signal") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.append(name)
    return ordered_unique_text(names)


def retrieval_asset_sets(solution_payload: Mapping[str, Any]) -> List[List[str]]:
    selected = solution_payload.get("selected_asset_ids") if isinstance(solution_payload.get("selected_asset_ids"), list) else []
    ordered = ordered_unique_text(selected)
    return [ordered] if ordered else []


def benchmark_equivalence_class_id(*, title: str, inputs: Sequence[str], outputs: Sequence[str]) -> str:
    signature = "|".join(
        [
            slugify(title),
            ",".join(ordered_unique_text(inputs)),
            ",".join(ordered_unique_text(outputs)),
        ]
    )
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
    return f"bench_eq_{digest}"


def stage_segments(solution_payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    stages = solution_payload.get("stages") if isinstance(solution_payload.get("stages"), list) else []
    segments: List[Dict[str, Any]] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        schedule = stage.get("schedule") if isinstance(stage.get("schedule"), dict) else {}
        start_time = schedule.get("start_time")
        stop_time = schedule.get("stop_time")
        if start_time is None and stop_time is None:
            continue
        segments.append(
            {
                "stage_id": str(stage.get("stage_id") or f"stage_{index + 1}"),
                "start_time": start_time,
                "stop_time": stop_time,
            }
        )
    return segments


def default_signal_aliases(
    *,
    signal_columns: Sequence[str],
    monitored_signals: Sequence[str],
    extra_aliases: Mapping[str, Sequence[str]] | None = None,
) -> Dict[str, List[str]]:
    aliases: Dict[str, List[str]] = {}
    for signal in ordered_unique_text(list(signal_columns) + list(monitored_signals)):
        aliases[signal] = ordered_unique_text([signal])
    for key, values in (extra_aliases or {}).items():
        signal = str(key or "").strip()
        if not signal:
            continue
        aliases[signal] = ordered_unique_text(list(aliases.get(signal, [])) + list(values))
    return aliases


def default_time_column_aliases(time_column: str, extra_aliases: Sequence[str] = ()) -> List[str]:
    canonical = str(time_column or "").strip()
    aliases = list(extra_aliases)
    if canonical:
        aliases = [canonical, canonical.lower(), canonical.upper(), "Time", "t", *aliases]
    return ordered_unique_text(aliases)


def remove_if_exists(path: Path) -> None:
    if path.exists() or path.is_symlink():
        path.unlink()


def write_retrieval_reference(
    *,
    case_dir: Path,
    case_id: str,
    solution_payload: Mapping[str, Any],
    oracle_mode: str = "exact_asset_set",
    equivalence_class_id: str = "",
    equivalence_reason: str = "",
    acceptable_asset_sets: Sequence[Sequence[str]] | None = None,
) -> str:
    payload = {
        "schema": "CASE_RETRIEVAL_REFERENCE_V1",
        "case_id": case_id,
        "oracle_mode": str(oracle_mode or "exact_asset_set"),
        "acceptable_asset_sets": [
            ordered_unique_text(asset_set)
            for asset_set in (acceptable_asset_sets or retrieval_asset_sets(solution_payload))
            if ordered_unique_text(asset_set)
        ],
        "equivalence_class_id": str(equivalence_class_id or ""),
        "equivalence_reason": str(equivalence_reason or ""),
    }
    write_json(case_dir / "retrieval_reference.json", payload)
    return "retrieval_reference.json"


def write_case_evaluation_artifacts(
    *,
    case_dir: Path,
    case_payload: Mapping[str, Any],
    solution_payload: Mapping[str, Any],
    verification_title: str,
    verification_text: str,
    judgement_policy: str,
    derivation_basis: Mapping[str, Any],
    verification_status: str,
    verification_conclusion: str,
    verification_summary: str,
    missing_requirements: Sequence[str] = (),
    retrieval_oracle_mode: str = "exact_asset_set",
    retrieval_equivalence_class_id: str = "",
    retrieval_equivalence_reason: str = "",
    retrieval_acceptable_asset_sets: Sequence[Sequence[str]] | None = None,
    ground_truth_source: Path | None = None,
    input_source: Path | None = None,
    trajectory_source_kind: str = "none",
    trajectory_signal_columns: Sequence[str] = (),
    criteria: Sequence[Mapping[str, Any]] = (),
    decision_rule: Mapping[str, Any] | None = None,
    tolerances: Mapping[str, Any] | None = None,
    time_column: str = "",
    time_column_aliases: Sequence[str] = (),
    signal_aliases: Mapping[str, Sequence[str]] | None = None,
    stage_segment_rows: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    case_id = str(case_payload.get("case_id") or case_dir.name)
    monitored_signals = monitored_signal_names(solution_payload)
    signal_columns = ordered_unique_text(trajectory_signal_columns) or monitored_signals
    ground_truth_relpath = ""
    input_relpath = ""
    ground_truth_link = case_dir / "ground_truth_trajectory.csv"
    input_link = case_dir / "input_trajectory.csv"
    if ground_truth_source is not None and ground_truth_source.exists():
        ensure_symlink(ground_truth_source.resolve(), ground_truth_link)
        ground_truth_relpath = ground_truth_link.name
        if not signal_columns:
            header = read_csv_columns(ground_truth_source)
            if header:
                signal_columns = ordered_unique_text(header[1:])
    else:
        remove_if_exists(ground_truth_link)
    if input_source is not None and input_source.exists():
        ensure_symlink(input_source.resolve(), input_link)
        input_relpath = input_link.name
    else:
        remove_if_exists(input_link)

    supports_execution_metrics = bool(solution_payload.get("schedule"))
    supports_numerical_fidelity = bool(ground_truth_relpath and signal_columns)
    supports_decision_accuracy = verification_status == "available" and verification_conclusion in {"pass", "fail"}
    resolved_time_column = str(time_column or ("time" if ground_truth_relpath else "")).strip()
    retrieval_reference_relpath = write_retrieval_reference(
        case_dir=case_dir,
        case_id=case_id,
        solution_payload=solution_payload,
        oracle_mode=retrieval_oracle_mode,
        equivalence_class_id=retrieval_equivalence_class_id,
        equivalence_reason=retrieval_equivalence_reason,
        acceptable_asset_sets=retrieval_acceptable_asset_sets,
    )
    resolved_stage_segments = [dict(item) for item in stage_segment_rows] if stage_segment_rows else stage_segments(solution_payload)

    requirement_payload = {
        "schema": "CASE_VERIFICATION_REQUIREMENT_V1",
        "case_id": case_id,
        "title": verification_title,
        "text": verification_text,
        "signals": monitored_signals,
        "scenario_window": schedule_window(case_payload, solution_payload),
        "judgement_policy": judgement_policy,
        "derivation_basis": dict(derivation_basis),
        "criteria": [dict(item) for item in criteria if isinstance(item, dict)],
        "decision_rule": dict(decision_rule or {"kind": judgement_policy}),
        "tolerances": dict(tolerances or {}),
        "time_column_aliases": default_time_column_aliases(resolved_time_column, time_column_aliases),
        "signal_aliases": default_signal_aliases(
            signal_columns=signal_columns,
            monitored_signals=monitored_signals,
            extra_aliases=signal_aliases,
        ),
    }
    result_payload = {
        "schema": "CASE_VERIFICATION_RESULT_V1",
        "case_id": case_id,
        "status": verification_status,
        "conclusion": verification_conclusion,
        "summary": verification_summary,
        "evidence_basis": {
            "ground_truth_trajectory_relpath": ground_truth_relpath,
            "input_trajectory_relpath": input_relpath,
            "source_kind": trajectory_source_kind,
        },
        "missing_requirements": ordered_unique_text(missing_requirements),
        "supports_decision_accuracy": supports_decision_accuracy,
    }
    trajectory_payload = {
        "schema": "CASE_TRAJECTORY_MANIFEST_V1",
        "case_id": case_id,
        "source_kind": trajectory_source_kind,
        "time_column": resolved_time_column,
        "signal_columns": signal_columns,
        "ground_truth_relpath": ground_truth_relpath,
        "input_relpath": input_relpath,
        "supports_numerical_fidelity": supports_numerical_fidelity,
        "column_aliases": {
            "time": default_time_column_aliases(resolved_time_column, time_column_aliases),
        },
        "signal_aliases": default_signal_aliases(
            signal_columns=signal_columns,
            monitored_signals=monitored_signals,
            extra_aliases=signal_aliases,
        ),
        "stage_segments": resolved_stage_segments,
        "reference_generation_method": str(trajectory_source_kind or "none"),
    }
    write_json(case_dir / "verification_requirement.json", requirement_payload)
    write_json(case_dir / "verification_result.json", result_payload)
    write_json(case_dir / "trajectory_manifest.json", trajectory_payload)
    return {
        "retrieval_reference_relpath": retrieval_reference_relpath,
        "verification_requirement_relpath": "verification_requirement.json",
        "verification_result_relpath": "verification_result.json",
        "trajectory_manifest_relpath": "trajectory_manifest.json",
        "ground_truth_trajectory_relpath": ground_truth_relpath,
        "input_trajectory_relpath": input_relpath,
        "supports_execution_metrics": supports_execution_metrics,
        "supports_numerical_fidelity": supports_numerical_fidelity,
        "supports_decision_accuracy": supports_decision_accuracy,
    }
