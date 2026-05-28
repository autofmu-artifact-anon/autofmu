from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .canonical import canonicalize_solution
from .types import ReferencePack


DEFAULT_TOP_K = 5
DEFAULT_DECISION_NRMSE_THRESHOLD = 1e-6
DEFAULT_DECISION_LOOSE_NRMSE_THRESHOLD = 0.05
DEFAULT_ACCEPTANCE_TIME_TOLERANCE = 1e-9
DEFAULT_INITIAL_CONDITION_ABS_TOLERANCE = 1e-6
DEFAULT_NUMERICAL_UPPER_TRIM_RATIO = 0.005
"""NRMSE reporting cap: per-case NRMSE is capped at this value before aggregation,
so reported aggregate NRMSE lies in [0, 2] and is not dominated by outlier cases."""
NRMSE_REPORTING_CAP = 2.0
_MISSING_SIGNAL_NRMSE_PENALTY = 1.0
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _mean(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0


def build_trimmed_metric_summary(
    case_values: Sequence[tuple[str, float]],
    *,
    trim_ratio: float = DEFAULT_NUMERICAL_UPPER_TRIM_RATIO,
    excluded_case_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    normalized_ratio = _maybe_float(trim_ratio)
    effective_ratio = min(max(float(normalized_ratio or 0.0), 0.0), 1.0)
    normalized_items: List[tuple[str, float]] = []
    for case_id, value in case_values:
        case_text = str(case_id or "").strip()
        number = _maybe_float(value)
        if not case_text or number is None:
            continue
        normalized_items.append((case_text, float(number)))
    total = len(normalized_items)
    ordered_desc = sorted(normalized_items, key=lambda item: (-item[1], item[0]))

    if excluded_case_ids is None:
        trim_count = 0 if total <= 1 else min(total - 1, int(math.ceil(total * effective_ratio)))
        excluded_case_id_set = {case_id for case_id, _ in ordered_desc[:trim_count]}
    else:
        excluded_case_id_set = {str(case_id or "").strip() for case_id in excluded_case_ids if str(case_id or "").strip()}
        if total and len(excluded_case_id_set) >= total:
            keep_case_id = min(normalized_items, key=lambda item: (item[1], item[0]))[0]
            excluded_case_id_set.discard(keep_case_id)

    excluded_rows = [item for item in ordered_desc if item[0] in excluded_case_id_set]
    kept_values = [value for case_id, value in normalized_items if case_id not in excluded_case_id_set]
    return {
        "value": _mean(kept_values),
        "upper_trim_ratio": effective_ratio,
        "case_count_before_trim": total,
        "case_count_after_trim": len(kept_values),
        "excluded_case_count": len(excluded_rows),
        "excluded_case_ids": [case_id for case_id, _ in excluded_rows],
    }


def _cap_nrmse_for_reporting(case_values: Sequence[tuple[str, float]], cap: float = NRMSE_REPORTING_CAP) -> List[tuple[str, float]]:
    """Cap per-case NRMSE at `cap` so aggregate stays in [0, cap] and is not pulled by outliers."""
    return [(cid, min(float(v), cap)) for cid, v in case_values if _maybe_float(v) is not None]


def build_trimmed_numerical_fidelity_summary(
    metric_case_values: Mapping[str, Sequence[tuple[str, float]]],
    *,
    trim_ratio: float = DEFAULT_NUMERICAL_UPPER_TRIM_RATIO,
    excluded_case_ids_by_metric: Mapping[str, Sequence[str]] | None = None,
) -> Dict[str, Any]:
    output: Dict[str, Any] = {
        "upper_trim_ratio": min(max(float(_maybe_float(trim_ratio) or 0.0), 0.0), 1.0),
    }
    for metric_name in ("mae", "rmse", "nrmse"):
        raw_values = list(metric_case_values.get(metric_name) or [])
        if metric_name == "nrmse":
            raw_values = _cap_nrmse_for_reporting(raw_values)
        output[metric_name] = build_trimmed_metric_summary(
            raw_values,
            trim_ratio=trim_ratio,
            excluded_case_ids=(
                list((excluded_case_ids_by_metric or {}).get(metric_name) or [])
                if excluded_case_ids_by_metric
                else None
            ),
        )
    return output


def _ordered_unique_text(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _compact(text: str) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    text = str(value).strip()
    if text.lower() == "true":
        return 1.0
    if text.lower() == "false":
        return 0.0
    return float(text)


def _maybe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _terminal_name(text: str) -> str:
    return str(text or "").split(".")[-1].strip()


def _canonical_asset_set(items: Sequence[Any]) -> List[str]:
    return sorted({str(item).strip() for item in items if str(item).strip()})


def _acceptable_asset_sets(reference: ReferencePack) -> List[List[str]]:
    retrieval_reference = reference.retrieval_reference or {}
    acceptable = retrieval_reference.get("acceptable_asset_sets")
    if isinstance(acceptable, list):
        asset_sets = [_canonical_asset_set(item if isinstance(item, list) else []) for item in acceptable]
        asset_sets = [item for item in asset_sets if item]
        if asset_sets:
            return asset_sets
    fallback = retrieval_reference.get("selected_asset_ids") or retrieval_reference.get("ground_truth_asset_ids") or []
    asset_set = _canonical_asset_set(fallback if isinstance(fallback, list) else [])
    return [asset_set] if asset_set else []


def _taskset_candidate_sets(stage2_result: Any) -> List[List[str]]:
    taskset_results = list(getattr(stage2_result, "taskset_results", []) or [])

    def _sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        status = str(item.get("status") or "")
        final_cost = item.get("final_cost")
        task_cost = item.get("selected_task_set_cost")
        try:
            final_cost_value = float(final_cost)
        except (TypeError, ValueError):
            final_cost_value = float("inf")
        try:
            task_cost_value = float(task_cost)
        except (TypeError, ValueError):
            task_cost_value = float("inf")
        return (
            0 if status == "ok" else 1,
            final_cost_value,
            task_cost_value,
            str(item.get("task_set_id") or ""),
        )

    candidates: List[List[str]] = []
    for item in sorted((row for row in taskset_results if isinstance(row, dict)), key=_sort_key):
        candidate = _canonical_asset_set(item.get("selected_fmus", []) if isinstance(item.get("selected_fmus"), list) else [])
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def score_retrieval(stage2_result: Any, predicted_solution: Dict[str, Any], reference: ReferencePack) -> Dict[str, Any]:
    predicted_assets = canonicalize_solution(predicted_solution).get("selected_asset_ids", [])
    top1_assets = _canonical_asset_set(predicted_assets)
    acceptable_asset_sets = _acceptable_asset_sets(reference)
    candidate_sets = [top1_assets] if top1_assets else []
    for item in _taskset_candidate_sets(stage2_result):
        if item not in candidate_sets:
            candidate_sets.append(item)
    topk_candidates = candidate_sets[:DEFAULT_TOP_K]
    return {
        "top_k": DEFAULT_TOP_K,
        "oracle_mode": str((reference.retrieval_reference or {}).get("oracle_mode") or ""),
        "equivalence_class_id": str((reference.retrieval_reference or {}).get("equivalence_class_id") or ""),
        "acceptable_asset_set_count": len(acceptable_asset_sets),
        "acceptable_asset_sets": acceptable_asset_sets,
        "top1_asset_ids": top1_assets,
        "candidate_asset_sets": topk_candidates,
        "top1_hit": top1_assets in acceptable_asset_sets if top1_assets else False,
        "topk_hit": any(candidate in acceptable_asset_sets for candidate in topk_candidates),
    }


def _read_csv_table(path: str | Path) -> Dict[str, Any]:
    csv_path = Path(path).expanduser().resolve()
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = list(reader.fieldnames or [])
    return {
        "path": csv_path,
        "headers": headers,
        "rows": rows,
    }


def _signal_aliases(reference: ReferencePack, signal_name: str) -> List[str]:
    requirement_aliases = (
        reference.verification_requirement.get("signal_aliases")
        if isinstance(reference.verification_requirement.get("signal_aliases"), dict)
        else {}
    )
    manifest_aliases = (
        reference.trajectory_manifest.get("signal_aliases")
        if isinstance(reference.trajectory_manifest.get("signal_aliases"), dict)
        else {}
    )
    return _ordered_unique_text(
        [signal_name]
        + list(requirement_aliases.get(signal_name, []) if isinstance(requirement_aliases.get(signal_name), list) else [])
        + list(manifest_aliases.get(signal_name, []) if isinstance(manifest_aliases.get(signal_name), list) else [])
    )


def _resolve_column(headers: Sequence[str], canonical: str, aliases: Sequence[str]) -> str:
    names = _ordered_unique_text([canonical] + list(aliases))
    if not names:
        return ""
    for candidate in names:
        if candidate in headers:
            return candidate
    lowered = {header.lower(): header for header in headers}
    for candidate in names:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    terminal = {_terminal_name(header): header for header in headers}
    for candidate in names:
        exact_terminal = terminal.get(_terminal_name(candidate))
        if exact_terminal:
            return exact_terminal
    compact_headers = {_compact(header): header for header in headers}
    for candidate in names:
        exact_compact = compact_headers.get(_compact(candidate))
        if exact_compact:
            return exact_compact
    for candidate in names:
        compact_candidate = _compact(_terminal_name(candidate))
        if not compact_candidate:
            continue
        for header in headers:
            compact_header = _compact(header)
            compact_terminal = _compact(_terminal_name(header))
            if compact_candidate == compact_terminal:
                return header
            if compact_candidate and compact_candidate in compact_header:
                return header
    return ""


def _resolve_time_column(headers: Sequence[str], reference: ReferencePack) -> str:
    manifest = reference.trajectory_manifest if isinstance(reference.trajectory_manifest, dict) else {}
    requirement = reference.verification_requirement if isinstance(reference.verification_requirement, dict) else {}
    manifest_aliases = manifest.get("column_aliases") if isinstance(manifest.get("column_aliases"), dict) else {}
    candidates = _ordered_unique_text(
        [manifest.get("time_column")]
        + list(requirement.get("time_column_aliases", []) if isinstance(requirement.get("time_column_aliases"), list) else [])
        + list(manifest_aliases.get("time", []) if isinstance(manifest_aliases.get("time"), list) else [])
        + ["time", "Time", "t"]
    )
    return _resolve_column(headers, str(manifest.get("time_column") or "time"), candidates)


def _timeseries_for_signals(
    path: str | Path,
    *,
    reference: ReferencePack,
    canonical_signals: Sequence[str],
) -> Dict[str, Any]:
    table = _read_csv_table(path)
    headers = table["headers"]
    time_column = _resolve_time_column(headers, reference)
    unresolved_signals: List[str] = []
    signal_map: Dict[str, str] = {}
    if not time_column:
        return {
            "time_column": "",
            "time": [],
            "signals": {},
            "signal_map": {},
            "unresolved_signals": list(canonical_signals),
        }
    times: List[float] = []
    for row in table["rows"]:
        raw = row.get(time_column)
        if raw in {None, ""}:
            continue
        times.append(_coerce_float(raw))
    signals: Dict[str, List[float]] = {}
    for signal in canonical_signals:
        column = _resolve_column(headers, signal, _signal_aliases(reference, signal))
        if not column:
            unresolved_signals.append(signal)
            continue
        values: List[float] = []
        for row in table["rows"]:
            raw = row.get(column)
            if raw in {None, ""}:
                continue
            values.append(_coerce_float(raw))
        if len(values) == len(times):
            signal_map[signal] = column
            signals[signal] = values
        else:
            unresolved_signals.append(signal)
    return {
        "time_column": time_column,
        "time": times,
        "signals": signals,
        "signal_map": signal_map,
        "unresolved_signals": unresolved_signals,
    }


def _interp(times: Sequence[float], values: Sequence[float], target: float) -> float:
    if not times or not values:
        raise ValueError("cannot interpolate empty timeseries")
    if target <= times[0]:
        return float(values[0])
    if target >= times[-1]:
        return float(values[-1])
    for index in range(1, len(times)):
        left_t = float(times[index - 1])
        right_t = float(times[index])
        if target > right_t:
            continue
        left_v = float(values[index - 1])
        right_v = float(values[index])
        if math.isclose(left_t, right_t):
            return right_v
        ratio = (target - left_t) / (right_t - left_t)
        return left_v + ratio * (right_v - left_v)
    return float(values[-1])


def _interp_many(times: Sequence[float], values: Sequence[float], targets: Sequence[float]) -> List[float]:
    if not times or not values:
        raise ValueError("cannot interpolate empty timeseries")
    if len(times) != len(values):
        raise ValueError("times and values length mismatch")
    out: List[float] = []
    index = 0
    last_index = len(times) - 1
    for target in targets:
        if target <= times[0]:
            out.append(float(values[0]))
            continue
        if target >= times[-1]:
            out.append(float(values[-1]))
            continue
        while index < last_index - 1 and float(times[index + 1]) < float(target):
            index += 1
        left_t = float(times[index])
        right_t = float(times[index + 1])
        left_v = float(values[index])
        right_v = float(values[index + 1])
        if math.isclose(left_t, right_t):
            out.append(right_v)
            continue
        ratio = (float(target) - left_t) / (right_t - left_t)
        out.append(left_v + ratio * (right_v - left_v))
    return out


def score_execution(execution_result: Dict[str, Any], reference: ReferencePack) -> Dict[str, Any]:
    return {
        "supported": reference.supports_execution_metrics,
        "success": bool(execution_result.get("success")),
        "backend": str(execution_result.get("backend") or ""),
        "execution_time_seconds": float(execution_result.get("execution_time_seconds") or 0.0),
        "generated_trajectory_path": str(execution_result.get("generated_trajectory_path") or ""),
        "error": execution_result.get("error"),
        "warnings": list(execution_result.get("warnings") or []),
    }


def score_numerical_fidelity(execution_result: Dict[str, Any], reference: ReferencePack) -> Dict[str, Any]:
    generated_path = str(execution_result.get("generated_trajectory_path") or "").strip()
    metrics = {
        "supported": bool(generated_path and reference.ground_truth_trajectory_path),
        "mae": None,
        "rmse": None,
        "nrmse": None,
        "max_abs_error": None,
        "aligned_sample_count": 0,
        "signal_count": 0,
        "signals": [],
        "generated_time_column": "",
        "reference_time_column": "",
        "generated_signal_map": {},
        "reference_signal_map": {},
        "unresolved_generated_signals": [],
        "unresolved_reference_signals": [],
    }
    if not metrics["supported"]:
        return metrics

    decision_rule = (
        reference.verification_requirement.get("decision_rule")
        if isinstance(reference.verification_requirement.get("decision_rule"), dict)
        else {}
    )
    manifest = reference.trajectory_manifest if isinstance(reference.trajectory_manifest, dict) else {}
    canonical_signals = _ordered_unique_text(
        list(decision_rule.get("signals", []) if isinstance(decision_rule.get("signals"), list) else [])
        + list(manifest.get("signal_columns", []) if isinstance(manifest.get("signal_columns"), list) else [])
        + list(reference.verification_requirement.get("signals", []) if isinstance(reference.verification_requirement.get("signals"), list) else [])
    )
    generated = _timeseries_for_signals(generated_path, reference=reference, canonical_signals=canonical_signals)
    reference_ts = _timeseries_for_signals(reference.ground_truth_trajectory_path, reference=reference, canonical_signals=canonical_signals)

    metrics["generated_time_column"] = generated["time_column"]
    metrics["reference_time_column"] = reference_ts["time_column"]
    metrics["generated_signal_map"] = dict(generated["signal_map"])
    metrics["reference_signal_map"] = dict(reference_ts["signal_map"])
    metrics["unresolved_generated_signals"] = list(generated["unresolved_signals"])
    metrics["unresolved_reference_signals"] = list(reference_ts["unresolved_signals"])
    if not generated["time_column"] or not reference_ts["time_column"]:
        return metrics

    evaluable_signals = [
        signal
        for signal in canonical_signals
        if signal in reference_ts["signals"]
    ]
    common_signals = [
        signal
        for signal in evaluable_signals
        if signal in generated["signals"]
    ]
    missing_signals = [
        signal
        for signal in evaluable_signals
        if signal not in generated["signals"]
    ]
    if not evaluable_signals:
        return metrics

    unified_grid = sorted({*generated["time"], *reference_ts["time"]})
    absolute_errors: List[float] = []
    squared_errors: List[float] = []
    normalized_rmse: List[float] = []
    penalized_normalized_rmse: List[float] = []
    max_abs_error = 0.0
    for signal in common_signals:
        gen_values = generated["signals"][signal]
        ref_values = reference_ts["signals"][signal]
        ref_interp = _interp_many(reference_ts["time"], ref_values, unified_grid)
        gen_interp = _interp_many(generated["time"], gen_values, unified_grid)
        signal_errors = [abs(gen - ref) for gen, ref in zip(gen_interp, ref_interp)]
        absolute_errors.extend(signal_errors)
        squared_errors.extend(error * error for error in signal_errors)
        max_abs_error = max(max_abs_error, max(signal_errors) if signal_errors else 0.0)
        signal_rmse = math.sqrt(sum(error * error for error in signal_errors) / len(signal_errors))
        ref_range = max(ref_interp) - min(ref_interp)
        if ref_range <= 0.0:
            ref_range = max(max(abs(value) for value in ref_interp), 1.0)
        nrmse_value = signal_rmse / ref_range
        normalized_rmse.append(nrmse_value)
        penalized_normalized_rmse.append(nrmse_value)

    for signal in missing_signals:
        ref_values = reference_ts["signals"][signal]
        ref_interp = _interp_many(reference_ts["time"], ref_values, unified_grid)
        ref_range = max(ref_interp) - min(ref_interp)
        if ref_range <= 0.0:
            ref_range = max(max(abs(value) for value in ref_interp), 1.0)
        penalized_normalized_rmse.append(_MISSING_SIGNAL_NRMSE_PENALTY)
        absolute_errors.extend([ref_range] * len(unified_grid))
        squared_errors.extend([ref_range * ref_range] * len(unified_grid))
        max_abs_error = max(max_abs_error, ref_range)

    metrics["mae"] = sum(absolute_errors) / len(absolute_errors)
    metrics["rmse"] = math.sqrt(sum(squared_errors) / len(squared_errors))
    metrics["nrmse"] = _mean(penalized_normalized_rmse)
    metrics["nrmse_common_only"] = _mean(normalized_rmse) if normalized_rmse else None
    metrics["max_abs_error"] = max_abs_error
    metrics["aligned_sample_count"] = len(unified_grid)
    metrics["signal_count"] = len(evaluable_signals)
    metrics["common_signal_count"] = len(common_signals)
    metrics["missing_signal_count"] = len(missing_signals)
    metrics["signals"] = evaluable_signals
    metrics["common_signals"] = common_signals
    metrics["missing_signals"] = missing_signals
    return metrics


def _load_trajectory_table(path: str | Path, reference: ReferencePack) -> Dict[str, Any]:
    table = _read_csv_table(path)
    time_column = _resolve_time_column(table["headers"], reference)
    times = []
    if time_column:
        for row in table["rows"]:
            raw = row.get(time_column)
            if raw not in {None, ""}:
                times.append(_coerce_float(raw))
    return {
        "headers": table["headers"],
        "rows": table["rows"],
        "time_column": time_column,
        "time": times,
        "cache": {},
    }


def _series_for_signal(table: Dict[str, Any], reference: ReferencePack, signal_name: str) -> Sequence[float] | None:
    cache = table["cache"]
    if signal_name in cache:
        return cache[signal_name]
    column = _resolve_column(table["headers"], signal_name, _signal_aliases(reference, signal_name))
    if not column:
        cache[signal_name] = None
        return None
    values = [_coerce_float(row[column]) for row in table["rows"] if row.get(column) not in {None, ""}]
    if len(values) != len(table["time"]):
        cache[signal_name] = None
        return None
    cache[signal_name] = values
    return values


def _constant_series(value: float, count: int) -> List[float]:
    return [float(value)] * count


def _series_for_term(table: Dict[str, Any], reference: ReferencePack, term: str) -> Sequence[float] | None:
    text = str(term or "").strip()
    if _NUMBER_RE.match(text):
        return _constant_series(float(text), len(table["time"]))
    return _series_for_signal(table, reference, text)


def _derivative(values: Sequence[float], times: Sequence[float]) -> List[float]:
    if not values or not times or len(values) != len(times):
        return []
    if len(values) == 1:
        return [0.0]
    out = [0.0]
    for index in range(1, len(values)):
        dt = float(times[index] - times[index - 1])
        out.append((float(values[index]) - float(values[index - 1])) / dt if dt else 0.0)
    return out


def _wrap_to_pi(value: float) -> float:
    return ((float(value) + math.pi) % (2.0 * math.pi)) - math.pi


def _expression_series(table: Dict[str, Any], reference: ReferencePack, expr: str) -> Sequence[float] | None:
    text = str(expr or "").strip()
    if not text:
        return None
    if text.startswith("abs(") and text.endswith(")"):
        inner = _expression_series(table, reference, text[4:-1])
        return [abs(float(value)) for value in inner] if inner is not None else None
    if text.startswith("wrap_to_pi(") and text.endswith(")"):
        inner = _expression_series(table, reference, text[len("wrap_to_pi(") : -1])
        return [_wrap_to_pi(float(value)) for value in inner] if inner is not None else None
    derivative_match = re.fullmatch(r"d\(([^)]+)\)/dt", text)
    if derivative_match:
        base = _expression_series(table, reference, derivative_match.group(1))
        return _derivative(base, table["time"]) if base is not None else None
    if " - " in text:
        left, right = text.split(" - ", 1)
        left_values = _series_for_term(table, reference, left)
        right_values = _series_for_term(table, reference, right)
        if left_values is None or right_values is None:
            return None
        return [float(l) - float(r) for l, r in zip(left_values, right_values)]
    term_values = _series_for_term(table, reference, text)
    if term_values is not None:
        return term_values
    return None


def _window_values(values: Sequence[float], times: Sequence[float], *, after_t: float | None = None, during: tuple[float, float] | None = None) -> List[float]:
    out: List[float] = []
    for time_value, item in zip(times, values):
        if after_t is not None and float(time_value) < float(after_t):
            continue
        if during is not None and not (float(during[0]) <= float(time_value) <= float(during[1])):
            continue
        out.append(float(item))
    return out


def _criterion_result(metric: str, passed: bool, observed: Any, criterion: Mapping[str, Any], *, error: str = "") -> Dict[str, Any]:
    return {
        "metric": metric,
        "operator": str(criterion.get("operator") or ""),
        "expected": criterion.get("value"),
        "observed": observed,
        "passed": passed,
        "error": error,
    }


def _time_coverage_summary(table: Dict[str, Any], reference: ReferencePack) -> Dict[str, Any]:
    times = list(table.get("time") or [])
    declared = reference.declared_scenario_window if isinstance(reference.declared_scenario_window, dict) else {}
    return {
        "observed_start_time": float(times[0]) if times else None,
        "observed_stop_time": float(times[-1]) if times else None,
        "declared_start_time": declared.get("start_time"),
        "declared_stop_time": declared.get("stop_time"),
        "sample_count": len(times),
    }


def _covers_time(times: Sequence[float], target: float) -> bool:
    return bool(times) and float(times[0]) <= float(target) <= float(times[-1])


def _covers_window(times: Sequence[float], start: float, stop: float) -> bool:
    return bool(times) and float(times[0]) <= float(start) and float(times[-1]) >= float(stop)


def _evaluate_initial_conditions(table: Dict[str, Any], reference: ReferencePack) -> tuple[List[Dict[str, Any]], List[str], bool]:
    declared = reference.declared_initial_conditions if isinstance(reference.declared_initial_conditions, dict) else {}
    if not declared:
        return [], [], True
    times = list(table.get("time") or [])
    if not times:
        return [], ["initial_conditions:missing_time_samples"], False

    scenario_window = reference.declared_scenario_window if isinstance(reference.declared_scenario_window, dict) else {}
    start_time = scenario_window.get("start_time")
    if start_time is None:
        start_time = float(times[0])
    if not _covers_time(times, float(start_time)):
        return [], [f"initial_conditions:missing_start_time:{start_time}"], False

    results: List[Dict[str, Any]] = []
    tolerance = 1e-3
    all_passed = True
    for signal_name, expected in declared.items():
        if not isinstance(expected, (int, float)):
            continue
        series = _series_for_signal(table, reference, str(signal_name))
        if series is None:
            continue
        observed = _interp(times, series, float(start_time))
        passed = abs(float(observed) - float(expected)) <= tolerance
        results.append(
            {
                "signal": str(signal_name),
                "expected": float(expected),
                "observed": float(observed),
                "tolerance": tolerance,
                "passed": passed,
                "error": "" if passed else "initial_condition_mismatch",
            }
        )
        all_passed = all_passed and passed
    return results, [], all_passed


def _compare_observed(observed: float, operator: str, expected: Any) -> bool:
    if operator == "<=":
        return float(observed) <= float(expected)
    if operator == ">=":
        return float(observed) >= float(expected)
    if operator == "in" and isinstance(expected, list) and len(expected) == 2:
        low, high = float(expected[0]), float(expected[1])
        return low <= float(observed) <= high
    return False


def _evaluate_acceptance_criteria(path: str | Path, reference: ReferencePack) -> Dict[str, Any]:
    requirement = reference.verification_requirement if isinstance(reference.verification_requirement, dict) else {}
    criteria = requirement.get("criteria") if isinstance(requirement.get("criteria"), list) else []
    table = _load_trajectory_table(path, reference)
    coverage = _time_coverage_summary(table, reference)
    if not table["time_column"]:
        return {
            "supported": False,
            "conclusion": "unknown",
            "criterion_results": [],
            "unsupported_criteria": ["missing_time_column"],
            "time_coverage": coverage,
            "initial_condition_results": [],
            "coverage_failures": ["missing_time_column"],
        }
    unsupported: List[str] = []
    coverage_failures: List[str] = []
    results: List[Dict[str, Any]] = []
    initial_condition_results, initial_condition_failures, initial_conditions_passed = _evaluate_initial_conditions(table, reference)
    coverage_failures.extend(initial_condition_failures)
    all_passed = initial_conditions_passed

    for criterion in criteria:
        if not isinstance(criterion, dict):
            continue
        metric = str(criterion.get("metric") or "").strip()
        operator = str(criterion.get("operator") or "").strip()
        value = criterion.get("value")
        observed: Any = None
        passed = False
        error = ""

        max_window_match = re.fullmatch(r"max\((.+)\)_after_t=([-0-9.]+)s", metric)
        during_match = re.fullmatch(r"max\((.+)\)_during_t=\[([-0-9.]+)s,([-0-9.]+)s\]", metric)
        point_match = re.fullmatch(r"abs\((.+)\) at t=([-0-9.]+)s", metric)
        max_all_match = re.fullmatch(r"max\((.+)\)(?:_over_all)?", metric)
        min_match = re.fullmatch(r"min\((.+)\)", metric)
        range_match = re.fullmatch(r"within_range\((.+)\)", metric)

        if max_window_match:
            expr = max_window_match.group(1).strip()
            after_t = float(max_window_match.group(2))
            declared_stop = coverage.get("declared_stop_time")
            required_stop = float(declared_stop) if isinstance(declared_stop, (int, float)) else after_t
            if not _covers_window(table["time"], after_t, required_stop):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            window_values = _window_values(
                _expression_series(table, reference, expr) or [],
                table["time"],
                after_t=after_t,
            )
            if not window_values:
                error = "unresolved_expression"
            else:
                observed = max(window_values)
                passed = _compare_observed(observed, operator, value)
        elif during_match:
            expr = during_match.group(1).strip()
            window_start = float(during_match.group(2))
            window_stop = float(during_match.group(3))
            if not _covers_window(table["time"], window_start, window_stop):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            window_values = _window_values(
                _expression_series(table, reference, expr) or [],
                table["time"],
                during=(window_start, window_stop),
            )
            if not window_values:
                error = "unresolved_expression"
            else:
                observed = max(window_values)
                passed = _compare_observed(observed, operator, value)
        elif point_match:
            expr = point_match.group(1).strip()
            target_time = float(point_match.group(2))
            if not _covers_time(table["time"], target_time):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            series = _expression_series(table, reference, expr)
            if not series:
                error = "unresolved_expression"
            else:
                observed = abs(_interp(table["time"], series, target_time))
                passed = _compare_observed(observed, operator, value)
        elif range_match:
            declared_start = coverage.get("declared_start_time")
            declared_stop = coverage.get("declared_stop_time")
            if isinstance(declared_start, (int, float)) and isinstance(declared_stop, (int, float)) and not _covers_window(table["time"], float(declared_start), float(declared_stop)):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            series = _expression_series(table, reference, range_match.group(1).strip())
            if not series:
                error = "unresolved_expression"
            elif not isinstance(value, list) or len(value) != 2:
                error = "invalid_range"
            else:
                low = min(float(item) for item in series)
                high = max(float(item) for item in series)
                observed = [low, high]
                passed = float(value[0]) <= low and high <= float(value[1])
        elif min_match:
            declared_start = coverage.get("declared_start_time")
            declared_stop = coverage.get("declared_stop_time")
            if isinstance(declared_start, (int, float)) and isinstance(declared_stop, (int, float)) and not _covers_window(table["time"], float(declared_start), float(declared_stop)):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            series = _expression_series(table, reference, min_match.group(1).strip())
            if not series:
                error = "unresolved_expression"
            else:
                observed = min(float(item) for item in series)
                passed = _compare_observed(observed, operator, value)
        elif max_all_match:
            declared_start = coverage.get("declared_start_time")
            declared_stop = coverage.get("declared_stop_time")
            if isinstance(declared_start, (int, float)) and isinstance(declared_stop, (int, float)) and not _covers_window(table["time"], float(declared_start), float(declared_stop)):
                error = "insufficient_time_coverage"
                coverage_failures.append(metric)
                results.append(_criterion_result(metric, False, None, criterion, error=error))
                all_passed = False
                continue
            series = _expression_series(table, reference, max_all_match.group(1).strip())
            if not series:
                error = "unresolved_expression"
            else:
                observed = max(float(item) for item in series)
                passed = _compare_observed(observed, operator, value)
        else:
            unsupported.append(metric)
            results.append(_criterion_result(metric, False, None, criterion, error="unsupported_criterion"))
            all_passed = False
            continue

        if error:
            unsupported.append(metric)
            results.append(_criterion_result(metric, False, observed, criterion, error=error))
            all_passed = False
            continue
        results.append(_criterion_result(metric, passed, observed, criterion))
        all_passed = all_passed and passed

    supported = len(unsupported) == 0
    conclusion = "pass" if supported and all_passed else ("fail" if supported else "unknown")
    return {
        "supported": supported,
        "conclusion": conclusion,
        "criterion_results": results,
        "unsupported_criteria": unsupported,
        "time_coverage": coverage,
        "initial_condition_results": initial_condition_results,
        "coverage_failures": _ordered_unique_text(coverage_failures),
    }


def score_decision(
    *,
    reference: ReferencePack,
    execution_result: Dict[str, Any],
    numerical_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    decision_rule = (
        reference.verification_requirement.get("decision_rule")
        if isinstance(reference.verification_requirement.get("decision_rule"), dict)
        else {}
    )
    rule_kind = str(decision_rule.get("kind") or "").strip()
    reference_status = str(reference.verification_result.get("status") or "").strip()
    reference_conclusion = str(reference.verification_result.get("conclusion") or "").strip()
    generated_path = str(execution_result.get("generated_trajectory_path") or "").strip()
    evidence: Dict[str, Any] = {"rule_kind": rule_kind}
    predicted_conclusion = "unknown"
    supported = False
    passed = None

    if bool(execution_result.get("success")) and generated_path:
        if rule_kind == "trajectory_tolerance":
            nrmse = numerical_metrics.get("nrmse")
            if isinstance(nrmse, (int, float)) and math.isfinite(float(nrmse)):
                passed = float(nrmse) <= DEFAULT_DECISION_LOOSE_NRMSE_THRESHOLD
                predicted_conclusion = "pass" if passed else "fail"
                supported = True
                evidence["decision_policy"] = "loose_pass_rate"
                evidence["policy_threshold_kind"] = "nrmse"
                evidence["policy_threshold"] = DEFAULT_DECISION_LOOSE_NRMSE_THRESHOLD
                evidence["nrmse"] = float(nrmse)
                max_abs_error = numerical_metrics.get("max_abs_error")
                if isinstance(max_abs_error, (int, float)) and math.isfinite(float(max_abs_error)):
                    evidence["max_abs_error"] = float(max_abs_error)
            else:
                evidence["error"] = "missing_numerical_alignment"
        elif rule_kind == "acceptance_criteria":
            evaluated = _evaluate_acceptance_criteria(generated_path, reference)
            predicted_conclusion = str(evaluated.get("conclusion") or "unknown")
            supported = bool(evaluated.get("supported"))
            evidence.update(evaluated)
            if supported:
                passed = predicted_conclusion == "pass"
                evidence["decision_policy"] = "acceptance_criteria_pass"
        else:
            nrmse = numerical_metrics.get("nrmse")
            if isinstance(nrmse, (int, float)) and math.isfinite(float(nrmse)):
                passed = float(nrmse) <= DEFAULT_DECISION_LOOSE_NRMSE_THRESHOLD
                predicted_conclusion = "pass" if passed else "fail"
                supported = True
                evidence["decision_policy"] = "loose_pass_rate"
                evidence["policy_threshold_kind"] = "nrmse"
                evidence["policy_threshold"] = DEFAULT_DECISION_LOOSE_NRMSE_THRESHOLD
                evidence["nrmse"] = float(nrmse)
    elif reference_status == "available" and reference_conclusion in {"pass", "fail"}:
        predicted_conclusion = "fail"
        supported = True
        evidence["error"] = execution_result.get("error")
        passed = False

    evaluable_without_reference_label = supported and passed is not None
    strict_reference_supported = reference_status == "available" and reference_conclusion in {"pass", "fail"} and supported

    correct = None
    if strict_reference_supported:
        correct = predicted_conclusion == reference_conclusion
    elif evaluable_without_reference_label:
        correct = passed
        evidence["reference_label_missing"] = True
        evidence["decision_policy_mode"] = "rule_evaluable_without_reference_label"

    return {
        "supported": strict_reference_supported or evaluable_without_reference_label,
        "predicted_conclusion": predicted_conclusion,
        "reference_conclusion": reference_conclusion,
        "passed": passed,
        "correct": correct,
        "evidence": evidence,
    }


def _row_execution_succeeded(row: Dict[str, Any]) -> bool:
    metrics = row.get("metrics") or {}
    execution = metrics.get("execution") or {}
    return bool(row.get("ok")) and bool(execution.get("supported")) and bool(execution.get("success"))


def aggregate_experiment_metrics(
    case_rows: List[Dict[str, Any]],
    *,
    case_id_filter: Sequence[str] | None = None,
) -> Dict[str, Any]:
    allowed_case_ids = {str(case_id) for case_id in list(case_id_filter or []) if str(case_id).strip()}
    scoped_rows = [
        row for row in case_rows if row.get("metrics") and (not allowed_case_ids or str(row.get("case_id") or "") in allowed_case_ids)
    ]
    total_cases = len(scoped_rows)
    retrieval_rows = list(scoped_rows)
    execution_rows = [
        row
        for row in retrieval_rows
        if (row.get("metrics") or {}).get("execution", {}).get("supported")
    ]
    successful_execution_rows = [row for row in execution_rows if _row_execution_succeeded(row)]
    numerical_rows = [
        row
        for row in retrieval_rows
        if (row.get("metrics") or {}).get("numerical_fidelity", {}).get("supported")
        and isinstance((row.get("metrics") or {}).get("numerical_fidelity", {}).get("mae"), (int, float))
    ]
    decision_rows = [
        row
        for row in retrieval_rows
        if (row.get("metrics") or {}).get("decision", {}).get("supported")
    ]
    numerical_case_values = {
        metric_name: [
            (
                str(row.get("case_id") or ""),
                float((row.get("metrics") or {}).get("numerical_fidelity", {}).get(metric_name, 0.0)),
            )
            for row in numerical_rows
            if _maybe_float((row.get("metrics") or {}).get("numerical_fidelity", {}).get(metric_name)) is not None
        ]
        for metric_name in ("mae", "rmse", "nrmse")
    }
    trimmed_numerical = build_trimmed_numerical_fidelity_summary(numerical_case_values)

    return {
        "cases_scored": total_cases,
        "supported_case_count": len(retrieval_rows),
        "scored_case_count": len(retrieval_rows),
        "success_count": sum(1 for row in retrieval_rows if row.get("ok")),
        "top1_hit_rate": _safe_div(
            sum(1 for row in retrieval_rows if (row.get("metrics") or {}).get("retrieval", {}).get("top1_hit")),
            len(retrieval_rows),
        ),
        "topk_hit_rate": _safe_div(
            sum(1 for row in retrieval_rows if (row.get("metrics") or {}).get("retrieval", {}).get("topk_hit")),
            len(retrieval_rows),
        ),
        "execution_cases": len(execution_rows),
        "execution_success_count": sum(
            1 for row in execution_rows if (row.get("metrics") or {}).get("execution", {}).get("success")
        ),
        "execution_success_rate": _safe_div(
            sum(1 for row in execution_rows if (row.get("metrics") or {}).get("execution", {}).get("success")),
            total_cases,
        ),
        "mean_execution_time_seconds": _mean(
            float((row.get("metrics") or {}).get("execution", {}).get("execution_time_seconds", 0.0))
            for row in successful_execution_rows
        ),
        "numerical_cases": len(numerical_rows),
        "mae": _mean(float((row.get("metrics") or {}).get("numerical_fidelity", {}).get("mae", 0.0)) for row in numerical_rows),
        "rmse": _mean(float((row.get("metrics") or {}).get("numerical_fidelity", {}).get("rmse", 0.0)) for row in numerical_rows),
        "nrmse": _mean(
            min(
                float((row.get("metrics") or {}).get("numerical_fidelity", {}).get("nrmse", 0.0)),
                NRMSE_REPORTING_CAP,
            )
            for row in numerical_rows
        ),
        "trimmed_mae": float((trimmed_numerical.get("mae") or {}).get("value", 0.0)),
        "trimmed_rmse": float((trimmed_numerical.get("rmse") or {}).get("value", 0.0)),
        "trimmed_nrmse": float((trimmed_numerical.get("nrmse") or {}).get("value", 0.0)),
        "trimmed_numerical_fidelity": trimmed_numerical,
        "decision_cases": len(decision_rows),
        "decision_accuracy": _safe_div(
            sum(1 for row in decision_rows if (row.get("metrics") or {}).get("decision", {}).get("correct")),
            len(decision_rows),
        ),
    }
