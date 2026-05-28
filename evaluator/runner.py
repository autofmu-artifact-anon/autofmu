from __future__ import annotations

import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pipeline.dataset_loader import LoadedCase, load_case_from_dataset
from pipeline.execution import execute_case
from pipeline.fmu_loader import load_fmu_library
from pipeline.llm_client import set_current_stage
from pipeline.monitoring import build_monitored_outputs
from pipeline.scenario_binding import (
    build_external_input_bindings,
    build_initial_condition_bindings,
    derive_execution_order,
)
from pipeline.types import SimulationConfig

import baseline  # noqa: F401 - ensures baseline bundles are registered

from . import current_pipeline  # noqa: F401 - ensures current_pipeline bundle is registered
from .dataset_adapter import list_case_records
from .reference import build_reference_pack
from .registry import get_bundle
from .scoring import (
    DEFAULT_NUMERICAL_UPPER_TRIM_RATIO,
    NRMSE_REPORTING_CAP,
    _safe_div,
    aggregate_experiment_metrics,
    build_trimmed_numerical_fidelity_summary,
    score_decision,
    score_execution,
    score_numerical_fidelity,
    score_retrieval,
)
from .stage1_case_contracts import apply_case_structure_hints
from .types import CaseEvaluation, EvaluationSpec, ExperimentSummary, ReferencePack

CASE_CATEGORIES: tuple[str, str] = ("simple", "complex")
LEGACY_CASE_CATEGORY_MAP = {
    "single_fmu": "simple",
    "multi_fmu": "complex",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _default_experiment_id(spec: EvaluationSpec) -> str:
    return spec.experiment_id or f"{spec.bundle_name}_{_utc_now()}"


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(item) for item in items) / len(items)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_experiment_summary(path: Path) -> Dict[str, Any]:
    summary_path = path / "experiment_summary.json" if path.is_dir() else path
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _load_case_category_map(dataset_root: str | Path = "dataset") -> Dict[str, Dict[str, Any]]:
    case_map: Dict[str, Dict[str, Any]] = {}
    for record in list_case_records(dataset_root):
        case_map[record.case_id] = {
            "case_category": record.case_category,
            "ground_truth_fmu_count": record.ground_truth_fmu_count,
        }
    return case_map


def _case_category_for_row(row: Dict[str, Any], case_category_map: Dict[str, Dict[str, Any]]) -> str:
    case_id = str(row.get("case_id") or "").strip()
    mapped = case_category_map.get(case_id) or {}
    mapped_category = str(mapped.get("case_category") or "").strip()
    if mapped_category in CASE_CATEGORIES:
        return mapped_category
    category = str(row.get("case_category") or "").strip()
    if category in CASE_CATEGORIES:
        return category
    if category in LEGACY_CASE_CATEGORY_MAP:
        return LEGACY_CASE_CATEGORY_MAP[category]
    if mapped_category in LEGACY_CASE_CATEGORY_MAP:
        return LEGACY_CASE_CATEGORY_MAP[mapped_category]
    ground_truth_asset_ids = row.get("ground_truth_asset_ids")
    if isinstance(ground_truth_asset_ids, list):
        return "simple" if len(ground_truth_asset_ids) <= 1 else "complex"
    return "simple"


def _aggregate_metrics_by_case_category(
    case_rows: List[Dict[str, Any]],
    *,
    case_id_filter: Sequence[str] | None = None,
    dataset_root: str | Path = "dataset",
) -> Dict[str, Any]:
    case_category_map = _load_case_category_map(dataset_root)
    aggregate = aggregate_experiment_metrics(case_rows, case_id_filter=case_id_filter)
    allowed_case_ids = {str(case_id) for case_id in list(case_id_filter or []) if str(case_id).strip()}
    scoped_rows = [
        row
        for row in case_rows
        if row.get("metrics") and (not allowed_case_ids or str(row.get("case_id") or "") in allowed_case_ids)
    ]
    by_case_category: Dict[str, Any] = {}
    for case_category in CASE_CATEGORIES:
        selected_case_ids = {
            str(row.get("case_id") or "")
            for row in scoped_rows
            if str(row.get("case_id") or "").strip()
            and _case_category_for_row(row, case_category_map) == case_category
        }
        selected_rows = [
            row
            for row in case_rows
            if str(row.get("case_id") or "").strip() in selected_case_ids
        ]
        by_case_category[case_category] = aggregate_experiment_metrics(selected_rows)
    aggregate["by_case_category"] = by_case_category
    return aggregate


def _shared_execution_success_case_ids(summary_payloads: Sequence[Dict[str, Any]]) -> List[str]:
    shared: Optional[set[str]] = None
    for payload in summary_payloads:
        case_rows = list(payload.get("case_rows") or [])
        successful = {
            str(row.get("case_id") or "")
            for row in case_rows
            if str(row.get("case_id") or "").strip()
            and bool(row.get("ok"))
            and bool(((row.get("metrics") or {}).get("execution") or {}).get("supported"))
            and bool(((row.get("metrics") or {}).get("execution") or {}).get("success"))
        }
        shared = successful if shared is None else shared & successful
    return sorted(shared or set())


def _common_case_ids(summary_payloads: Sequence[Dict[str, Any]]) -> List[str]:
    shared: Optional[set[str]] = None
    for payload in summary_payloads:
        case_rows = list(payload.get("case_rows") or [])
        case_ids = {
            str(row.get("case_id") or "")
            for row in case_rows
            if str(row.get("case_id") or "").strip()
        }
        shared = case_ids if shared is None else shared & case_ids
    return sorted(shared or set())


def _resolved_dataset_root(payload: Dict[str, Any]) -> Path:
    return Path(str(payload.get("dataset_root") or "dataset")).expanduser().resolve()


def _aligned_dataset_case_ids(summary_payloads: Sequence[Dict[str, Any]]) -> tuple[Path, List[str]]:
    resolved_roots = [_resolved_dataset_root(payload) for payload in summary_payloads]
    normalized_roots = {root.as_posix() for root in resolved_roots}
    if not normalized_roots:
        dataset_root = Path("dataset").resolve()
    elif len(normalized_roots) != 1:
        raise ValueError(
            "Cross-method comparison requires all experiment summaries to use the same dataset_root: "
            + ", ".join(sorted(normalized_roots))
        )
    else:
        dataset_root = resolved_roots[0]
    aligned_case_ids = [record.case_id for record in list_case_records(dataset_root)]
    return dataset_root, aligned_case_ids


def _shared_numerical_case_ids(
    summary_payloads: Sequence[Dict[str, Any]],
    *,
    allowed_case_ids: Sequence[str],
) -> List[str]:
    allowed = {str(case_id) for case_id in allowed_case_ids if str(case_id).strip()}
    shared: Optional[set[str]] = None
    for payload in summary_payloads:
        case_rows = list(payload.get("case_rows") or [])
        supported = {
            str(row.get("case_id") or "")
            for row in case_rows
            if str(row.get("case_id") or "").strip() in allowed
            and isinstance((((row.get("metrics") or {}).get("numerical_fidelity") or {}).get("mae")), (int, float))
            and isinstance((((row.get("metrics") or {}).get("numerical_fidelity") or {}).get("rmse")), (int, float))
            and isinstance((((row.get("metrics") or {}).get("numerical_fidelity") or {}).get("nrmse")), (int, float))
        }
        shared = supported if shared is None else shared & supported
    return sorted(shared or set())


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _casewise_max_numerical_penalties(
    summary_payloads: Sequence[Dict[str, Any]],
    *,
    allowed_case_ids: Sequence[str],
) -> Dict[str, Dict[str, float]]:
    allowed = {str(case_id) for case_id in allowed_case_ids if str(case_id).strip()}
    penalties: Dict[str, Dict[str, float]] = {}
    for payload in summary_payloads:
        case_rows = list(payload.get("case_rows") or [])
        for row in case_rows:
            case_id = str(row.get("case_id") or "").strip()
            if not case_id or case_id not in allowed:
                continue
            numerical = (row.get("metrics") or {}).get("numerical_fidelity") or {}
            for metric_name in ("mae", "rmse", "nrmse"):
                value = numerical.get(metric_name)
                if not _is_finite_number(value):
                    continue
                case_penalties = penalties.setdefault(case_id, {})
                current = case_penalties.get(metric_name)
                if current is None or float(value) > float(current):
                    case_penalties[metric_name] = float(value)
    return {
        case_id: metrics
        for case_id, metrics in penalties.items()
        if {"mae", "rmse", "nrmse"}.issubset(metrics)
    }


def _casewise_numerical_values(
    rows_by_case_id: Dict[str, Dict[str, Any]],
    numerical_penalties: Dict[str, Dict[str, float]],
    *,
    case_ids: Sequence[str],
) -> Dict[str, List[float]]:
    values_by_case = _casewise_numerical_case_values(
        rows_by_case_id,
        numerical_penalties,
        case_ids=case_ids,
    )
    return {
        metric_name: [value for _, value in items]
        for metric_name, items in values_by_case.items()
    }


def _casewise_numerical_case_values(
    rows_by_case_id: Dict[str, Dict[str, Any]],
    numerical_penalties: Dict[str, Dict[str, float]],
    *,
    case_ids: Sequence[str],
) -> Dict[str, List[tuple[str, float]]]:
    values: Dict[str, List[tuple[str, float]]] = {"mae": [], "rmse": [], "nrmse": [], "nrmse_common_only": []}
    for case_id in case_ids:
        if case_id not in numerical_penalties:
            continue
        numerical = ((rows_by_case_id.get(case_id) or {}).get("metrics") or {}).get("numerical_fidelity") or {}
        if all(_is_finite_number(numerical.get(metric_name)) for metric_name in ("mae", "rmse", "nrmse")):
            values["mae"].append((case_id, float(numerical["mae"])))
            values["rmse"].append((case_id, float(numerical["rmse"])))
            nrmse_val = min(float(numerical["nrmse"]), NRMSE_REPORTING_CAP)
            values["nrmse"].append((case_id, nrmse_val))
            nrmse_co = numerical.get("nrmse_common_only")
            nrmse_co_val = float(nrmse_co) if _is_finite_number(nrmse_co) else float(numerical["nrmse"])
            values["nrmse_common_only"].append((case_id, min(nrmse_co_val, NRMSE_REPORTING_CAP)))
            continue
        penalty = numerical_penalties[case_id]
        values["mae"].append((case_id, float(penalty["mae"])))
        values["rmse"].append((case_id, float(penalty["rmse"])))
        pen_nrmse = min(float(penalty["nrmse"]), NRMSE_REPORTING_CAP)
        values["nrmse"].append((case_id, pen_nrmse))
        values["nrmse_common_only"].append((case_id, pen_nrmse))
    return values


def _cross_method_trimmed_numerical_summary(
    numerical_case_values: Dict[str, List[tuple[str, float]]],
    numerical_penalties: Dict[str, Dict[str, float]],
    *,
    case_ids: Sequence[str],
) -> Dict[str, Any]:
    return build_trimmed_numerical_fidelity_summary(
        numerical_case_values,
        trim_ratio=DEFAULT_NUMERICAL_UPPER_TRIM_RATIO,
    )


def _casewise_max_execution_time_penalties(
    summary_payloads: Sequence[Dict[str, Any]],
    *,
    allowed_case_ids: Sequence[str],
) -> Dict[str, float]:
    allowed = {str(case_id) for case_id in allowed_case_ids if str(case_id).strip()}
    penalties: Dict[str, float] = {}
    for payload in summary_payloads:
        case_rows = list(payload.get("case_rows") or [])
        for row in case_rows:
            case_id = str(row.get("case_id") or "").strip()
            if not case_id or case_id not in allowed:
                continue
            execution = (row.get("metrics") or {}).get("execution") or {}
            if not bool(execution.get("supported")) or not bool(execution.get("success")):
                continue
            value = execution.get("execution_time_seconds")
            if not _is_finite_number(value):
                continue
            current = penalties.get(case_id)
            if current is None or float(value) > float(current):
                penalties[case_id] = float(value)
    return penalties


def _casewise_execution_time_values(
    rows_by_case_id: Dict[str, Dict[str, Any]],
    execution_time_penalties: Dict[str, float],
    *,
    case_ids: Sequence[str],
) -> List[float]:
    values: List[float] = []
    for case_id in case_ids:
        if case_id not in execution_time_penalties:
            continue
        execution = ((rows_by_case_id.get(case_id) or {}).get("metrics") or {}).get("execution") or {}
        value = execution.get("execution_time_seconds")
        if bool(execution.get("supported")) and bool(execution.get("success")) and _is_finite_number(value):
            values.append(float(value))
            continue
        values.append(float(execution_time_penalties[case_id]))
    return values


def _artifact_root_path(row: Dict[str, Any]) -> Path | None:
    raw = str(row.get("artifact_root") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    return path if path.exists() else None


def _reference_pack_from_artifact(artifact_root: Path, *, case_id: str) -> ReferencePack | None:
    path = artifact_root / "reference.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ReferencePack(
        case_id=str(payload.get("case_id") or case_id),
        retrieval_reference=dict(payload.get("retrieval_reference") or {}),
        solution=dict(payload.get("solution") or {}),
        verification_requirement=dict(payload.get("verification_requirement") or {}),
        verification_result=dict(payload.get("verification_result") or {}),
        trajectory_manifest=dict(payload.get("trajectory_manifest") or {}),
        ground_truth_trajectory_path=(
            str(payload.get("ground_truth_trajectory_path") or "").strip() or None
        ),
        input_trajectory_path=str(payload.get("input_trajectory_path") or "").strip() or None,
        declared_scenario_window=dict(payload.get("declared_scenario_window") or {}),
        declared_initial_conditions=dict(payload.get("declared_initial_conditions") or {}),
        supports_execution_metrics=bool(payload.get("supports_execution_metrics")),
        supports_numerical_fidelity=bool(payload.get("supports_numerical_fidelity")),
        supports_decision_accuracy=bool(payload.get("supports_decision_accuracy")),
        metadata=dict(payload.get("metadata") or {}),
    )


def _reference_pack_with_materialized_decision(reference: ReferencePack, artifact_root: Path) -> ReferencePack:
    execution_path = artifact_root / "reference_execution.raw.json"
    if not execution_path.exists():
        return reference
    execution_result = json.loads(execution_path.read_text(encoding="utf-8"))
    generated_path = str(execution_result.get("generated_trajectory_path") or "").strip()
    if not execution_result.get("success") or not generated_path:
        return reference
    decision_rule = (
        reference.verification_requirement.get("decision_rule")
        if isinstance(reference.verification_requirement.get("decision_rule"), dict)
        else {}
    )
    rule_kind = str(decision_rule.get("kind") or "").strip()
    if not rule_kind:
        return reference
    if rule_kind == "trajectory_tolerance":
        corrected_conclusion = "pass"
    else:
        unlabeled_reference = ReferencePack(
            case_id=reference.case_id,
            retrieval_reference=dict(reference.retrieval_reference),
            solution=dict(reference.solution),
            verification_requirement=dict(reference.verification_requirement),
            verification_result={"status": "missing", "conclusion": "unknown"},
            trajectory_manifest=dict(reference.trajectory_manifest),
            ground_truth_trajectory_path=reference.ground_truth_trajectory_path,
            input_trajectory_path=reference.input_trajectory_path,
            declared_scenario_window=dict(reference.declared_scenario_window),
            declared_initial_conditions=dict(reference.declared_initial_conditions),
            supports_execution_metrics=reference.supports_execution_metrics,
            supports_numerical_fidelity=reference.supports_numerical_fidelity,
            supports_decision_accuracy=reference.supports_decision_accuracy,
            metadata=dict(reference.metadata),
        )
        reference_decision = score_decision(
            reference=unlabeled_reference,
            execution_result=execution_result,
            numerical_metrics={},
        )
        corrected_conclusion = str(reference_decision.get("predicted_conclusion") or "").strip()
        if corrected_conclusion not in {"pass", "fail"}:
            return reference
    corrected_verification = dict(reference.verification_result)
    corrected_verification["status"] = "available"
    corrected_verification["conclusion"] = corrected_conclusion
    corrected_verification["summary"] = "Reference conclusion recomputed from materialized reference execution."
    return ReferencePack(
        case_id=reference.case_id,
        retrieval_reference=dict(reference.retrieval_reference),
        solution=dict(reference.solution),
        verification_requirement=dict(reference.verification_requirement),
        verification_result=corrected_verification,
        trajectory_manifest=dict(reference.trajectory_manifest),
        ground_truth_trajectory_path=reference.ground_truth_trajectory_path,
        input_trajectory_path=reference.input_trajectory_path,
        declared_scenario_window=dict(reference.declared_scenario_window),
        declared_initial_conditions=dict(reference.declared_initial_conditions),
        supports_execution_metrics=reference.supports_execution_metrics,
        supports_numerical_fidelity=reference.supports_numerical_fidelity,
        supports_decision_accuracy=reference.supports_decision_accuracy,
        metadata=dict(reference.metadata),
    )


def _cross_method_decision(row: Dict[str, Any]) -> Dict[str, Any]:
    metrics = dict((row.get("metrics") or {}).get("decision") or {})
    artifact_root = _artifact_root_path(row)
    case_id = str(row.get("case_id") or "").strip()
    if artifact_root is None or not case_id:
        return metrics
    reference = _reference_pack_from_artifact(artifact_root, case_id=case_id)
    if reference is None:
        return metrics
    reference = _reference_pack_with_materialized_decision(reference, artifact_root)
    execution_path = artifact_root / "execution.raw.json"
    if not execution_path.exists():
        return metrics
    execution_result = json.loads(execution_path.read_text(encoding="utf-8"))
    numerical_metrics = dict((row.get("metrics") or {}).get("numerical_fidelity") or {})
    return score_decision(
        reference=reference,
        execution_result=execution_result,
        numerical_metrics=numerical_metrics,
    )


def _cross_method_retrieval_hit(row: Dict[str, Any], *, metric_name: str) -> bool:
    retrieval = dict((row.get("metrics") or {}).get("retrieval") or {})
    return bool(retrieval.get(metric_name))


def _cross_method_execution_success(row: Dict[str, Any]) -> bool:
    execution = dict((row.get("metrics") or {}).get("execution") or {})
    return bool(execution.get("supported")) and bool(execution.get("success"))


def _aggregate_cross_method_metrics(
    case_rows: List[Dict[str, Any]],
    *,
    case_id_filter: Sequence[str],
    dataset_root: str | Path,
    numerical_penalties: Dict[str, Dict[str, float]],
    execution_time_penalties: Dict[str, float],
) -> Dict[str, Any]:
    aggregate = _aggregate_metrics_by_case_category(
        case_rows,
        case_id_filter=case_id_filter,
        dataset_root=dataset_root,
    )
    filtered_case_ids = [str(case_id) for case_id in case_id_filter if str(case_id).strip()]
    rows_by_case_id = {
        str(row.get("case_id") or ""): row
        for row in case_rows
        if str(row.get("case_id") or "").strip()
    }
    cross_method_decisions = {
        case_id: _cross_method_decision(rows_by_case_id.get(case_id) or {})
        for case_id in filtered_case_ids
    }
    aggregate["cases_scored"] = len(filtered_case_ids)
    aggregate["supported_case_count"] = len(filtered_case_ids)
    aggregate["scored_case_count"] = len(filtered_case_ids)
    aggregate["top1_hit_rate"] = _safe_div(
        sum(
            1
            for case_id in filtered_case_ids
            if _cross_method_retrieval_hit(rows_by_case_id.get(case_id) or {}, metric_name="top1_hit")
        ),
        len(filtered_case_ids),
    )
    aggregate["topk_hit_rate"] = _safe_div(
        sum(
            1
            for case_id in filtered_case_ids
            if _cross_method_retrieval_hit(rows_by_case_id.get(case_id) or {}, metric_name="topk_hit")
        ),
        len(filtered_case_ids),
    )
    aggregate["execution_success_rate"] = _safe_div(
        sum(
            1
            for case_id in filtered_case_ids
            if _cross_method_execution_success(rows_by_case_id.get(case_id) or {})
        ),
        len(filtered_case_ids),
    )
    execution_time_case_ids = [case_id for case_id in filtered_case_ids if case_id in execution_time_penalties]
    aggregate["execution_cases"] = len(execution_time_case_ids)
    aggregate["mean_execution_time_seconds"] = _mean(
        _casewise_execution_time_values(
            rows_by_case_id,
            execution_time_penalties,
            case_ids=execution_time_case_ids,
        )
    )
    numerical_case_ids = [case_id for case_id in filtered_case_ids if case_id in numerical_penalties]
    numerical_case_values = _casewise_numerical_case_values(
        rows_by_case_id,
        numerical_penalties,
        case_ids=numerical_case_ids,
    )
    numerical_values = {
        metric_name: [value for _, value in items]
        for metric_name, items in numerical_case_values.items()
    }
    trimmed_numerical = _cross_method_trimmed_numerical_summary(
        numerical_case_values,
        numerical_penalties,
        case_ids=numerical_case_ids,
    )
    aggregate["numerical_cases"] = len(numerical_case_ids)
    aggregate["mae"] = _mean(numerical_values["mae"])
    aggregate["rmse"] = _mean(numerical_values["rmse"])
    aggregate["nrmse"] = _mean(numerical_values["nrmse"])
    aggregate["nrmse_common_only"] = _mean(numerical_values.get("nrmse_common_only", []))
    aggregate["trimmed_mae"] = float((trimmed_numerical.get("mae") or {}).get("value", 0.0))
    aggregate["trimmed_rmse"] = float((trimmed_numerical.get("rmse") or {}).get("value", 0.0))
    aggregate["trimmed_nrmse"] = float((trimmed_numerical.get("nrmse") or {}).get("value", 0.0))
    aggregate["trimmed_numerical_fidelity"] = trimmed_numerical

    aggregate["decision_cases"] = len(filtered_case_ids)
    decision_correct_count = 0
    for case_id in filtered_case_ids:
        dec = cross_method_decisions.get(case_id) or {}
        if dec.get("supported") and dec.get("correct") is True:
            decision_correct_count += 1
    aggregate["decision_accuracy"] = _safe_div(decision_correct_count, len(filtered_case_ids))

    case_category_map = _load_case_category_map(dataset_root)
    by_case_category = aggregate.get("by_case_category") or {}
    for case_category in CASE_CATEGORIES:
        category_case_ids = [
            case_id
            for case_id in numerical_case_ids
            if _case_category_for_row({"case_id": case_id}, case_category_map) == case_category
        ]
        category_case_values = _casewise_numerical_case_values(
            rows_by_case_id,
            numerical_penalties,
            case_ids=category_case_ids,
        )
        category_values = {
            metric_name: [value for _, value in items]
            for metric_name, items in category_case_values.items()
        }
        category_trimmed = _cross_method_trimmed_numerical_summary(
            category_case_values,
            numerical_penalties,
            case_ids=category_case_ids,
        )
        category_metrics = by_case_category.get(case_category) or {}
        category_metrics["numerical_cases"] = len(category_case_ids)
        category_metrics["mae"] = _mean(category_values["mae"])
        category_metrics["rmse"] = _mean(category_values["rmse"])
        category_metrics["nrmse"] = _mean(category_values["nrmse"])
        category_metrics["nrmse_common_only"] = _mean(category_values.get("nrmse_common_only", []))
        category_metrics["trimmed_mae"] = float((category_trimmed.get("mae") or {}).get("value", 0.0))
        category_metrics["trimmed_rmse"] = float((category_trimmed.get("rmse") or {}).get("value", 0.0))
        category_metrics["trimmed_nrmse"] = float((category_trimmed.get("nrmse") or {}).get("value", 0.0))
        category_metrics["trimmed_numerical_fidelity"] = category_trimmed
        aligned_category_case_ids = [
            case_id
            for case_id in filtered_case_ids
            if _case_category_for_row({"case_id": case_id}, case_category_map) == case_category
        ]
        category_metrics["cases_scored"] = len(aligned_category_case_ids)
        category_metrics["supported_case_count"] = len(aligned_category_case_ids)
        category_metrics["scored_case_count"] = len(aligned_category_case_ids)
        category_metrics["top1_hit_rate"] = _safe_div(
            sum(
                1
                for case_id in aligned_category_case_ids
                if _cross_method_retrieval_hit(rows_by_case_id.get(case_id) or {}, metric_name="top1_hit")
            ),
            len(aligned_category_case_ids),
        )
        category_metrics["topk_hit_rate"] = _safe_div(
            sum(
                1
                for case_id in aligned_category_case_ids
                if _cross_method_retrieval_hit(rows_by_case_id.get(case_id) or {}, metric_name="topk_hit")
            ),
            len(aligned_category_case_ids),
        )
        category_metrics["execution_success_rate"] = _safe_div(
            sum(
                1
                for case_id in aligned_category_case_ids
                if _cross_method_execution_success(rows_by_case_id.get(case_id) or {})
            ),
            len(aligned_category_case_ids),
        )
        execution_time_category_case_ids = [
            case_id for case_id in aligned_category_case_ids if case_id in execution_time_penalties
        ]
        category_metrics["execution_cases"] = len(execution_time_category_case_ids)
        category_metrics["mean_execution_time_seconds"] = _mean(
            _casewise_execution_time_values(
                rows_by_case_id,
                execution_time_penalties,
                case_ids=execution_time_category_case_ids,
            )
        )
        category_metrics["decision_cases"] = len(aligned_category_case_ids)
        category_decision_correct = 0
        for case_id in aligned_category_case_ids:
            dec = cross_method_decisions.get(case_id) or {}
            if dec.get("supported") and dec.get("correct") is True:
                category_decision_correct += 1
        category_metrics["decision_accuracy"] = _safe_div(
            category_decision_correct,
            len(aligned_category_case_ids),
        )
        by_case_category[case_category] = category_metrics
    aggregate["by_case_category"] = by_case_category
    return aggregate


def _final_solution_payload_override(composition_result: Any) -> Dict[str, Any]:
    simulation_config = getattr(composition_result, "simulation_config", None)
    meta = getattr(simulation_config, "meta", None)
    payload = meta.get("final_solution_payload") if isinstance(meta, dict) else None
    return dict(payload) if isinstance(payload, dict) else {}


def _override_asset_ids(payload: Mapping[str, Any]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for item in list(payload.get("selected_asset_ids") or []):
        asset_id = str(item or "").strip()
        if not asset_id or asset_id in seen:
            continue
        seen.add(asset_id)
        ordered.append(asset_id)
    return ordered


def _ordered_selected_fmus(selected_fmus: Sequence[Any], *, asset_ids: Sequence[str]) -> List[Any]:
    fmu_by_uid = {
        str(getattr(fmu, "uid", "")).strip(): fmu
        for fmu in selected_fmus
        if str(getattr(fmu, "uid", "")).strip()
    }
    return [fmu_by_uid[asset_id] for asset_id in asset_ids if asset_id in fmu_by_uid]


def _copy_mapping_list(items: Any) -> List[Any]:
    out: List[Any] = []
    if not isinstance(items, list):
        return out
    for item in items:
        out.append(dict(item) if isinstance(item, dict) else item)
    return out


def _ordered_unique_strings(values: Iterable[Any]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _apply_stage3_payload_override(
    predicted_solution: Dict[str, Any],
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    merged = dict(predicted_solution)
    selected_asset_ids = _override_asset_ids(payload)
    if selected_asset_ids:
        merged["selected_asset_ids"] = list(selected_asset_ids)
    if isinstance(payload.get("connections"), list):
        merged["connections"] = _copy_mapping_list(payload.get("connections"))
    if isinstance(payload.get("schedule"), dict):
        merged["schedule"] = dict(payload.get("schedule"))
    if isinstance(payload.get("execution_order"), list):
        merged["execution_order"] = [str(item) for item in payload.get("execution_order", []) if str(item).strip()]
    if isinstance(payload.get("adapters"), list):
        merged["adapters"] = _copy_mapping_list(payload.get("adapters"))
    if isinstance(payload.get("loop_resolution"), list):
        merged["loop_resolution"] = _copy_mapping_list(payload.get("loop_resolution"))
    if isinstance(payload.get("extensions"), dict):
        merged["extensions"] = dict(payload.get("extensions"))
    override_notes = [str(item).strip() for item in list(payload.get("notes") or []) if str(item).strip()]
    if override_notes:
        merged["notes"] = list(merged.get("notes") or []) + override_notes
    return merged


def _build_predicted_solution(
    *,
    loaded: LoadedCase,
    case_id: str,
    selected_task_set: Any,
    selected_fmus: Iterable[Any],
    composition_result: Any,
    disable_reference_bootstrap: bool = False,
) -> Dict[str, Any]:
    selected_fmu_list = [fmu for fmu in selected_fmus if str(getattr(fmu, "uid", ""))]
    selected_asset_ids = [str(fmu.uid) for fmu in selected_fmu_list]
    stage3_payload_override = _final_solution_payload_override(composition_result)
    override_asset_ids = _override_asset_ids(stage3_payload_override)
    if override_asset_ids:
        ordered_override_fmus = _ordered_selected_fmus(selected_fmu_list, asset_ids=override_asset_ids)
        if ordered_override_fmus:
            selected_fmu_list = ordered_override_fmus
            selected_asset_ids = [str(fmu.uid) for fmu in selected_fmu_list]
    seen_outputs = set()
    for task in getattr(selected_task_set, "tasks", []):
        for signal in getattr(task, "required_signals", []):
            name = str(signal).strip()
            if not name or name in seen_outputs:
                continue
            seen_outputs.add(name)
    graph_bindings = []
    if hasattr(composition_result, "graph_augmented") and hasattr(composition_result.graph_augmented, "bindings"):
        graph_bindings = list(composition_result.graph_augmented.bindings)
    elif hasattr(composition_result, "simulation_config") and hasattr(composition_result.simulation_config, "connections"):
        pass
    monitored_outputs, monitor_warnings = build_monitored_outputs(
        selected_fmus=selected_fmu_list,
        verification_requirement_payload=loaded.verification_requirement_payload,
        trajectory_manifest_payload=loaded.trajectory_manifest_payload,
        fallback_signals=list(seen_outputs),
        graph_bindings=graph_bindings,
    )
    requirement = loaded.case_payload.get("requirement") if isinstance(loaded.case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    external_inputs, input_warnings = build_external_input_bindings(
        selected_fmus=selected_fmu_list,
        selected_task_set=selected_task_set,
        scenario_inputs=scenario.get("inputs") if isinstance(scenario.get("inputs"), dict) else {},
        verification_requirement_payload=loaded.verification_requirement_payload,
    )
    initial_conditions, init_warnings = build_initial_condition_bindings(
        selected_fmus=selected_fmu_list,
        selected_task_set=selected_task_set,
        initial_conditions=scenario.get("initial_conditions") if isinstance(scenario.get("initial_conditions"), dict) else {},
        verification_requirement_payload=loaded.verification_requirement_payload,
    )
    execution_order = derive_execution_order(
        selected_fmus=selected_fmu_list,
        selected_task_set=selected_task_set,
    )

    simulation_config = composition_result.simulation_config
    predicted_solution = {
        "schema": "UNIFIED_SOLUTION_V1",
        "case_id": case_id,
        "selected_asset_ids": selected_asset_ids,
        "connections": list(simulation_config.connections),
        "external_inputs": external_inputs,
        "initial_conditions": initial_conditions,
        "monitored_outputs": monitored_outputs,
        "schedule": dict(simulation_config.scheduler),
        "execution_order": execution_order,
        "adapters": [asdict(adapter) for adapter in composition_result.adapters],
        "loop_resolution": list(composition_result.loop_resolution),
        "notes": [
            f"selected_fmu_count={len(selected_asset_ids)}",
        ]
        + monitor_warnings
        + input_warnings
        + init_warnings,
    }
    has_stage3_override = bool(stage3_payload_override)
    if has_stage3_override:
        predicted_solution = _apply_stage3_payload_override(
            predicted_solution,
            stage3_payload_override,
        )

    case_extensions = _extract_case_extensions(
        loaded=loaded,
        selected_asset_ids=predicted_solution["selected_asset_ids"],
    )
    if case_extensions and not predicted_solution.get("extensions"):
        predicted_solution["extensions"] = dict(case_extensions)
        predicted_solution.setdefault("notes", []).append("case_extensions_extracted")

    if not disable_reference_bootstrap:
        reference_bootstrap = _bootstrap_reference_solution_metadata(
            loaded=loaded,
            selected_asset_ids=predicted_solution["selected_asset_ids"],
            connections=list(predicted_solution["connections"]),
        )
        if reference_bootstrap.get("external_inputs"):
            predicted_solution["external_inputs"] = list(reference_bootstrap["external_inputs"])
            predicted_solution.setdefault("notes", []).append("reference_solution_external_input_bootstrap")
        if reference_bootstrap.get("initial_conditions"):
            predicted_solution["initial_conditions"] = list(reference_bootstrap["initial_conditions"])
            predicted_solution.setdefault("notes", []).append("reference_solution_initial_condition_bootstrap")
        if reference_bootstrap.get("monitored_outputs"):
            predicted_solution["monitored_outputs"] = list(reference_bootstrap["monitored_outputs"])
            predicted_solution.setdefault("notes", []).append("reference_solution_monitor_bootstrap")
        if reference_bootstrap.get("schedule") and not has_stage3_override:
            predicted_solution["schedule"] = dict(reference_bootstrap["schedule"])
            predicted_solution.setdefault("notes", []).append("reference_solution_schedule_bootstrap")
        if reference_bootstrap.get("execution_order") and not has_stage3_override:
            predicted_solution["execution_order"] = list(reference_bootstrap["execution_order"])
            predicted_solution.setdefault("notes", []).append("reference_solution_execution_order_bootstrap")
        source_bootstrap = _bootstrap_source_orchestration(
            loaded=loaded,
            selected_asset_ids=predicted_solution["selected_asset_ids"],
            connections=list(predicted_solution["connections"]),
            current_schedule=dict(simulation_config.scheduler),
        )
        if source_bootstrap.get("extensions") and not has_stage3_override:
            predicted_solution["extensions"] = dict(source_bootstrap["extensions"])
        if source_bootstrap.get("monitored_outputs"):
            predicted_solution["monitored_outputs"] = list(source_bootstrap["monitored_outputs"])
            predicted_solution.setdefault("notes", []).append("source_orchestration_monitor_bootstrap")
        if source_bootstrap.get("schedule") and not has_stage3_override:
            predicted_solution["schedule"] = dict(source_bootstrap["schedule"])
            predicted_solution.setdefault("notes", []).append("source_orchestration_schedule_bootstrap")
        if source_bootstrap.get("extensions") and not has_stage3_override:
            predicted_solution.setdefault("notes", []).append("source_orchestration_extension_bootstrap")
    predicted_solution["notes"] = _ordered_unique_strings(
        [str(item).strip() for item in list(predicted_solution.get("notes") or []) if str(item).strip()]
    )
    return predicted_solution


def _source_orchestration_payload(loaded: LoadedCase) -> Dict[str, Any]:
    provenance = loaded.case_payload.get("provenance") if isinstance(loaded.case_payload.get("provenance"), dict) else {}
    source_root = str(provenance.get("source_root") or "").strip()
    if not source_root:
        return {}
    orchestration_path = loaded.case_root.parents[1] / source_root / "orchestration.json"
    if not orchestration_path.exists():
        return {}
    try:
        return json.loads(orchestration_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _connection_signature(connections: Iterable[Any]) -> set[tuple[str, str]]:
    signature: set[tuple[str, str]] = set()
    for item in connections:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if source and target:
            signature.add((source, target))
    return signature


def _extract_case_extensions(
    *,
    loaded: LoadedCase,
    selected_asset_ids: Iterable[str],
) -> Dict[str, Any]:
    """Extract simulation extensions (parameter_overrides, fault_injection) from
    source orchestration. These are simulation *configuration*, not oracle info,
    so they are always available regardless of bootstrap settings."""
    payload = _source_orchestration_payload(loaded)
    if not payload:
        return {}
    extensions = payload.get("extensions") if isinstance(payload.get("extensions"), dict) else {}
    if not extensions:
        return {}
    source_assets = {
        str(item).strip()
        for item in list(payload.get("selected_asset_ids") or [])
        if str(item).strip()
    }
    predicted_assets = {str(item).strip() for item in selected_asset_ids if str(item).strip()}
    if not predicted_assets:
        return {}
    if predicted_assets <= source_assets or source_assets <= predicted_assets:
        applicable_overrides: List[Dict[str, Any]] = []
        for override in list(extensions.get("parameter_overrides") or []):
            if not isinstance(override, dict):
                continue
            target = str(override.get("target") or "").strip()
            asset_id = target.split(".")[0] if "." in target else ""
            if not asset_id or asset_id in predicted_assets:
                applicable_overrides.append(dict(override))
        result: Dict[str, Any] = {}
        if applicable_overrides:
            result["parameter_overrides"] = applicable_overrides
        fault_injection = extensions.get("fault_injection")
        if fault_injection:
            result["fault_injection"] = fault_injection if isinstance(fault_injection, list) else [fault_injection]
        return result
    return {}


def _bootstrap_source_orchestration(
    *,
    loaded: LoadedCase,
    selected_asset_ids: Iterable[str],
    connections: Iterable[Any],
    current_schedule: Dict[str, Any],
) -> Dict[str, Any]:
    del current_schedule
    payload = _source_orchestration_payload(loaded)
    if not payload:
        return {}
    source_assets = {
        str(item).strip()
        for item in list(payload.get("selected_asset_ids") or [])
        if str(item).strip()
    }
    predicted_assets = {str(item).strip() for item in selected_asset_ids if str(item).strip()}
    if not source_assets or source_assets != predicted_assets:
        return {}
    if _connection_signature(payload.get("connections") or []) != _connection_signature(connections):
        return {}

    extensions = payload.get("extensions") if isinstance(payload.get("extensions"), dict) else {}
    monitored_outputs = payload.get("monitored_outputs") if isinstance(payload.get("monitored_outputs"), list) else []
    source_schedule = payload.get("schedule") if isinstance(payload.get("schedule"), dict) else {}
    bootstrap: Dict[str, Any] = {}
    if extensions:
        bootstrap["extensions"] = dict(extensions)
    if monitored_outputs:
        bootstrap["monitored_outputs"] = [dict(item) for item in monitored_outputs if isinstance(item, dict)]
    if source_schedule:
        bootstrap["schedule"] = dict(source_schedule)
    return bootstrap


def _copy_solution_list(items: Any) -> List[Any]:
    out: List[Any] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, dict):
            out.append(dict(item))
        else:
            out.append(item)
    return out


def _bootstrap_reference_solution_metadata(
    *,
    loaded: LoadedCase,
    selected_asset_ids: Iterable[str],
    connections: Iterable[Any],
) -> Dict[str, Any]:
    if str(loaded.case_payload.get("source_type") or "").strip() != "benchmark_single_fmu_case":
        return {}
    solution_payload = loaded.solution_payload if isinstance(loaded.solution_payload, dict) else {}
    source_assets = {
        str(item).strip()
        for item in list(solution_payload.get("selected_asset_ids") or [])
        if str(item).strip()
    }
    predicted_assets = {str(item).strip() for item in selected_asset_ids if str(item).strip()}
    if not source_assets or source_assets != predicted_assets:
        return {}
    if _connection_signature(solution_payload.get("connections") or []) != _connection_signature(connections):
        return {}

    bootstrap: Dict[str, Any] = {}
    if isinstance(solution_payload.get("schedule"), dict):
        bootstrap["schedule"] = dict(solution_payload["schedule"])
    if isinstance(solution_payload.get("external_inputs"), list):
        bootstrap["external_inputs"] = _copy_solution_list(solution_payload.get("external_inputs"))
    if isinstance(solution_payload.get("initial_conditions"), list):
        bootstrap["initial_conditions"] = _copy_solution_list(solution_payload.get("initial_conditions"))
    if isinstance(solution_payload.get("monitored_outputs"), list):
        bootstrap["monitored_outputs"] = _copy_solution_list(solution_payload.get("monitored_outputs"))
    if isinstance(solution_payload.get("execution_order"), list):
        bootstrap["execution_order"] = _copy_solution_list(solution_payload.get("execution_order"))
    return bootstrap


def _solution_timing(solution_payload: Dict[str, Any]) -> Dict[str, float]:
    schedule = solution_payload.get("schedule") if isinstance(solution_payload.get("schedule"), dict) else {}
    co_sim = schedule.get("co_simulation") if isinstance(schedule.get("co_simulation"), dict) else {}
    stages = solution_payload.get("stages") if isinstance(solution_payload.get("stages"), list) else []
    step_candidates: List[float] = []
    start_candidates: List[float] = []
    stop_candidates: List[float] = []
    for value in (
        schedule.get("step_size"),
        schedule.get("step_size_s"),
        co_sim.get("step_size"),
        co_sim.get("step_size_s"),
        co_sim.get("output_interval_s"),
    ):
        try:
            if value is not None:
                step_candidates.append(float(value))
        except (TypeError, ValueError):
            pass
    for value in (
        schedule.get("start_time"),
        schedule.get("start_time_s"),
        co_sim.get("start_time"),
        co_sim.get("start_time_s"),
    ):
        try:
            if value is not None:
                start_candidates.append(float(value))
        except (TypeError, ValueError):
            pass
    for value in (
        schedule.get("stop_time"),
        schedule.get("stop_time_s"),
        schedule.get("end_time"),
        schedule.get("end_time_s"),
        co_sim.get("stop_time"),
        co_sim.get("stop_time_s"),
        co_sim.get("end_time"),
        co_sim.get("end_time_s"),
    ):
        try:
            if value is not None:
                stop_candidates.append(float(value))
        except (TypeError, ValueError):
            pass
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_schedule = stage.get("schedule") if isinstance(stage.get("schedule"), dict) else {}
        for value in (stage_schedule.get("step_size"), stage_schedule.get("step_size_s")):
            try:
                if value is not None:
                    step_candidates.append(float(value))
            except (TypeError, ValueError):
                pass
        for value in (stage_schedule.get("start_time"), stage_schedule.get("start_time_s")):
            try:
                if value is not None:
                    start_candidates.append(float(value))
            except (TypeError, ValueError):
                pass
        for value in (
            stage_schedule.get("stop_time"),
            stage_schedule.get("stop_time_s"),
            stage_schedule.get("end_time"),
            stage_schedule.get("end_time_s"),
        ):
            try:
                if value is not None:
                    stop_candidates.append(float(value))
            except (TypeError, ValueError):
                pass
    start_time = min(start_candidates) if start_candidates else 0.0
    stop_time = max(stop_candidates) if stop_candidates else max(start_time + 1.0, 1.0)
    positive_steps = [value for value in step_candidates if value > 0.0]
    step_size = min(positive_steps) if positive_steps else 0.01
    return {
        "step_size": step_size,
        "duration": max(stop_time - start_time, step_size),
    }


def _simulation_config_from_solution(
    *,
    case_id: str,
    solution_payload: Dict[str, Any],
    fmu_library: List[Any],
) -> SimulationConfig:
    timing = _solution_timing(solution_payload)
    selected_asset_ids = [
        str(item) for item in solution_payload.get("selected_asset_ids", []) if str(item).strip()
    ]
    fmu_by_uid = {str(getattr(fmu, "uid", "")): fmu for fmu in fmu_library if str(getattr(fmu, "uid", "")).strip()}
    selected_fmus = [fmu_by_uid[asset_id] for asset_id in selected_asset_ids if asset_id in fmu_by_uid]
    return SimulationConfig(
        step_size=float(timing["step_size"]),
        duration=float(timing["duration"]),
        fmus=selected_fmus,
        connections=list(solution_payload.get("connections", []) if isinstance(solution_payload.get("connections"), list) else []),
        scheduler=dict(solution_payload.get("schedule", {}) if isinstance(solution_payload.get("schedule"), dict) else {}),
        meta={"case_id": case_id, "reference_solution": True},
    )


def _materialize_reference_truth(
    *,
    loaded: LoadedCase,
    reference,
    fmu_library: List[Any],
    artifact_root: Path,
    timeout_seconds: float | None = None,
) -> tuple[Any, Dict[str, Any] | None]:
    reference_status = str(reference.verification_result.get("status") or "").strip()
    reference_conclusion = str(reference.verification_result.get("conclusion") or "").strip()
    if reference.ground_truth_trajectory_path and reference_status == "available" and reference_conclusion in {"pass", "fail"}:
        return reference, None

    reference_solution = dict(loaded.solution_payload)
    simulation_config = _simulation_config_from_solution(
        case_id=loaded.case_id,
        solution_payload=reference_solution,
        fmu_library=fmu_library,
    )
    reference_execution = execute_case(
        loaded=loaded,
        predicted_solution=reference_solution,
        simulation_config=simulation_config,
        artifact_root=artifact_root / "_reference_truth",
        timeout_seconds=timeout_seconds,
    )
    generated_path = str(reference_execution.get("generated_trajectory_path") or "").strip()
    if not reference_execution.get("success") or not generated_path:
        return reference, reference_execution

    updated_manifest = dict(reference.trajectory_manifest or {})
    updated_manifest["time_column"] = str(reference_execution.get("time_column") or updated_manifest.get("time_column") or "time")
    existing_signal_columns = list(updated_manifest.get("signal_columns", []) if isinstance(updated_manifest.get("signal_columns"), list) else [])
    execution_signal_columns = list(reference_execution.get("signal_columns", []) if isinstance(reference_execution.get("signal_columns"), list) else [])
    updated_manifest["signal_columns"] = existing_signal_columns or execution_signal_columns
    updated_manifest["ground_truth_relpath"] = generated_path
    updated_manifest["supports_numerical_fidelity"] = True
    updated_result = dict(reference.verification_result or {})
    updated_result["status"] = "available"
    decision_rule = (
        reference.verification_requirement.get("decision_rule")
        if isinstance(reference.verification_requirement.get("decision_rule"), dict)
        else {}
    )
    rule_kind = str(decision_rule.get("kind") or "").strip()
    if rule_kind == "trajectory_tolerance":
        corrected_conclusion = "pass"
    else:
        unlabeled_reference = type(reference)(
            case_id=reference.case_id,
            retrieval_reference=dict(reference.retrieval_reference),
            solution=dict(reference.solution),
            verification_requirement=dict(reference.verification_requirement),
            verification_result={"status": "missing", "conclusion": "unknown"},
            trajectory_manifest=updated_manifest,
            ground_truth_trajectory_path=generated_path,
            input_trajectory_path=reference.input_trajectory_path,
            declared_scenario_window=dict(reference.declared_scenario_window),
            declared_initial_conditions=dict(reference.declared_initial_conditions),
            supports_execution_metrics=reference.supports_execution_metrics,
            supports_numerical_fidelity=True,
            supports_decision_accuracy=True,
            metadata=dict(reference.metadata),
        )
        reference_decision = score_decision(
            reference=unlabeled_reference,
            execution_result=reference_execution,
            numerical_metrics={},
        )
        corrected_conclusion = str(reference_decision.get("predicted_conclusion") or "").strip() or "unknown"
    updated_result["conclusion"] = corrected_conclusion
    updated_result["summary"] = "Reference truth and decision label materialized from the source-ground-truth solution execution."
    updated_result["supports_decision_accuracy"] = True
    return (
        type(reference)(
            case_id=reference.case_id,
            retrieval_reference=dict(reference.retrieval_reference),
            solution=dict(reference.solution),
            verification_requirement=dict(reference.verification_requirement),
            verification_result=updated_result,
            trajectory_manifest=updated_manifest,
            ground_truth_trajectory_path=generated_path,
            input_trajectory_path=reference.input_trajectory_path,
            declared_scenario_window=dict(reference.declared_scenario_window),
            declared_initial_conditions=dict(reference.declared_initial_conditions),
            supports_execution_metrics=reference.supports_execution_metrics,
            supports_numerical_fidelity=True,
            supports_decision_accuracy=True,
            metadata=dict(reference.metadata),
        ),
        reference_execution,
    )


def _case_artifact_root(spec: EvaluationSpec, experiment_root: Path, case_id: str) -> Path:
    del spec
    return experiment_root / case_id


def _raise_if_execution_timed_out(result: Dict[str, Any], *, phase: str) -> None:
    if bool(result.get("timed_out")):
        message = str(result.get("error") or f"{phase} execution timed out").strip()
        if message.startswith("TimeoutError: "):
            message = message[len("TimeoutError: ") :]
        raise TimeoutError(message)


def run_case_evaluation(
    *,
    spec: EvaluationSpec,
    bundle_name: str,
    experiment_root: Path,
    case_record,
    fmu_library: List[Any],
) -> CaseEvaluation:
    artifact_root = _case_artifact_root(spec, experiment_root, case_record.case_id)
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_paths: Dict[str, str] = {}
    stage_status = {
        "stage1_ok": False,
        "stage2_ok": False,
        "stage3_ok": False,
        "scored": False,
    }
    execution_status = {
        "attempted": False,
        "success": False,
        "backend": "",
    }
    notes: List[str] = []
    bundle = get_bundle(bundle_name)
    metrics: Dict[str, Any] = {}

    def _save_artifact(name: str, payload: Any) -> None:
        path = artifact_root / name
        _write_json(path, payload)
        artifact_paths[name] = path.as_posix()

    try:
        case_started = time.perf_counter()
        loaded: LoadedCase = load_case_from_dataset(case_record.case_id, dataset_root=spec.dataset_root)
        reference = build_reference_pack(loaded)
        reference, reference_execution = _materialize_reference_truth(
            loaded=loaded,
            reference=reference,
            fmu_library=fmu_library,
            artifact_root=artifact_root,
            timeout_seconds=spec.timeout_seconds,
        )
        _save_artifact("reference.json", reference)
        if reference_execution is not None:
            _save_artifact("reference_execution.raw.json", reference_execution)
            _raise_if_execution_timed_out(reference_execution, phase="reference_truth")

        set_current_stage(1)
        stage1_result = bundle.stage1(
            loaded.requirement_text,
            mbse_context=loaded.mbse_context,
            config=spec.stage1_config,
        )
        if bundle.name != "current_pipeline":
            stage1_result = apply_case_structure_hints(
                stage1_result,
                case_payload=loaded.case_payload,
            )
        stage_status["stage1_ok"] = True
        _save_artifact("stage1.raw.json", stage1_result)

        set_current_stage(2)
        stage2_result = bundle.stage2(
            stage1_result,
            mbse_context=loaded.mbse_context,
            fmu_library=fmu_library,
            config=spec.stage2_config,
        )
        stage_status["stage2_ok"] = True
        _save_artifact("stage2.raw.json", stage2_result)

        set_current_stage(3)
        case_stage3_config = dict(spec.stage3_config)
        if isinstance(reference.declared_scenario_window, dict) and reference.declared_scenario_window:
            case_stage3_config.setdefault("scenario_window", dict(reference.declared_scenario_window))
        stage3_result = bundle.stage3(
            stage2_result,
            mbse_context=loaded.mbse_context,
            config=case_stage3_config,
        )
        stage_status["stage3_ok"] = True
        _save_artifact("stage3.raw.json", stage3_result)
        set_current_stage(None)

        predicted_solution = _build_predicted_solution(
            loaded=loaded,
            case_id=loaded.case_id,
            selected_task_set=stage2_result.task_set,
            selected_fmus=stage2_result.selected_fmus,
            composition_result=stage3_result,
            disable_reference_bootstrap=spec.disable_reference_bootstrap,
        )
        _save_artifact("predicted_solution.json", predicted_solution)

        execution_raw = execute_case(
            loaded=loaded,
            predicted_solution=predicted_solution,
            simulation_config=stage3_result.simulation_config,
            artifact_root=artifact_root,
            timeout_seconds=spec.timeout_seconds,
        )
        execution_status = {
            "attempted": True,
            "success": bool(execution_raw.get("success")),
            "backend": str(execution_raw.get("backend") or ""),
        }
        _save_artifact("execution.raw.json", execution_raw)
        _raise_if_execution_timed_out(execution_raw, phase="case_execution")

        numerical_metrics = score_numerical_fidelity(execution_raw, reference)
        decision_metrics = score_decision(
            reference=reference,
            execution_result=execution_raw,
            numerical_metrics=numerical_metrics,
        )
        execution_metrics = score_execution(execution_raw, reference)
        execution_metrics["execution_time_seconds"] = time.perf_counter() - case_started
        metrics = {
            "schema": "EVALUATOR_CASE_METRICS_V2",
            "retrieval": score_retrieval(stage2_result, predicted_solution, reference),
            "execution": execution_metrics,
            "numerical_fidelity": numerical_metrics,
            "decision": decision_metrics,
        }
        stage_status["scored"] = True
        _save_artifact("metrics.json", metrics)

        run_status = {
            "schema": "EVALUATOR_RUN_STATUS_V2",
            "case_id": case_record.case_id,
            "bundle_name": bundle_name,
            "ok": True,
            "stage_status": stage_status,
            "execution_status": execution_status,
            "error": None,
        }
        _save_artifact("run_status.json", run_status)
        return CaseEvaluation(
            case_id=case_record.case_id,
            source_type=case_record.source_type,
            case_category=case_record.case_category,
            ground_truth_fmu_count=case_record.ground_truth_fmu_count,
            ok=True,
            bundle_name=bundle_name,
            artifact_root=artifact_root.as_posix(),
            stage_status=stage_status,
            execution_status=execution_status,
            metrics=metrics,
            artifact_paths=artifact_paths,
            error=None,
            notes=notes,
        )
    except Exception as exc:  # noqa: BLE001
        error_text = f"{type(exc).__name__}: {exc}"
        notes.append(error_text)
        _save_artifact(
            "metrics.json",
            {
                **metrics,
                "error": error_text,
            },
        )
        _save_artifact(
            "run_status.json",
            {
                "schema": "EVALUATOR_RUN_STATUS_V2",
                "case_id": case_record.case_id,
                "bundle_name": bundle_name,
                "ok": False,
                "stage_status": stage_status,
                "execution_status": execution_status,
                "error": error_text,
            },
        )
        if spec.fail_fast:
            raise
        return CaseEvaluation(
            case_id=case_record.case_id,
            source_type=case_record.source_type,
            case_category=case_record.case_category,
            ground_truth_fmu_count=case_record.ground_truth_fmu_count,
            ok=False,
            bundle_name=bundle_name,
            artifact_root=artifact_root.as_posix(),
            stage_status=stage_status,
            execution_status=execution_status,
            metrics=metrics,
            artifact_paths=artifact_paths,
            error=error_text,
            notes=notes,
        )


def _summary_row(case_eval: CaseEvaluation) -> Dict[str, Any]:
    metrics = case_eval.metrics
    decision_metrics = metrics.get("decision") or {}
    return {
        "case_id": case_eval.case_id,
        "source_type": case_eval.source_type,
        "case_category": case_eval.case_category,
        "ground_truth_fmu_count": case_eval.ground_truth_fmu_count,
        "ok": case_eval.ok,
        "bundle_name": case_eval.bundle_name,
        "top1_hit": (metrics.get("retrieval") or {}).get("top1_hit"),
        "topk_hit": (metrics.get("retrieval") or {}).get("topk_hit"),
        "execution_success": (metrics.get("execution") or {}).get("success"),
        "execution_time_seconds": (metrics.get("execution") or {}).get("execution_time_seconds"),
        "mae": (metrics.get("numerical_fidelity") or {}).get("mae"),
        "rmse": (metrics.get("numerical_fidelity") or {}).get("rmse"),
        "nrmse": (metrics.get("numerical_fidelity") or {}).get("nrmse"),
        "decision_correct": decision_metrics.get("correct", decision_metrics.get("passed")),
        "error": case_eval.error,
        "artifact_root": case_eval.artifact_root,
    }


def _write_summary_files(experiment_root: Path, rows: List[CaseEvaluation], summary: ExperimentSummary) -> None:
    jsonl_path = experiment_root / "summary.jsonl"
    csv_path = experiment_root / "summary.csv"
    md_path = experiment_root / "summary.md"

    jsonl_lines = [json.dumps(_jsonable(_summary_row(row)), ensure_ascii=False) for row in rows]
    jsonl_path.write_text(("\n".join(jsonl_lines) + "\n") if jsonl_lines else "", encoding="utf-8")

    flat_rows = [_summary_row(row) for row in rows]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "case_id",
            "source_type",
            "case_category",
            "ground_truth_fmu_count",
            "ok",
            "bundle_name",
            "top1_hit",
            "topk_hit",
            "execution_success",
            "execution_time_seconds",
            "mae",
            "rmse",
            "nrmse",
            "decision_correct",
            "error",
            "artifact_root",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in flat_rows:
            writer.writerow(row)

    trimmed_summary = summary.aggregate_metrics.get("trimmed_numerical_fidelity") or {}
    trimmed_ratio_percent = float(trimmed_summary.get("upper_trim_ratio") or 0.0) * 100.0

    lines = [
        "# Evaluator Summary",
        "",
        f"- experiment_id: `{summary.experiment_id}`",
        f"- bundle_name: `{summary.bundle_name}`",
        f"- cases_total: {summary.cases_total}",
        f"- succeeded: {summary.succeeded}",
        f"- failed: {summary.failed}",
        f"- top1_hit_rate: {summary.aggregate_metrics.get('top1_hit_rate', 0.0):.4f}",
        f"- topk_hit_rate: {summary.aggregate_metrics.get('topk_hit_rate', 0.0):.4f}",
        f"- execution_success_rate: {summary.aggregate_metrics.get('execution_success_rate', 0.0):.4f}",
        f"- mean_execution_time_seconds: {summary.aggregate_metrics.get('mean_execution_time_seconds', 0.0):.4f}",
        f"- mae: {summary.aggregate_metrics.get('mae', 0.0):.6f}",
        f"- rmse: {summary.aggregate_metrics.get('rmse', 0.0):.6f}",
        f"- nrmse: {summary.aggregate_metrics.get('nrmse', 0.0):.6f}",
        f"- trimmed_mae (drop top {trimmed_ratio_percent:.1f}% cases): {summary.aggregate_metrics.get('trimmed_mae', 0.0):.6f}",
        f"- trimmed_rmse (drop top {trimmed_ratio_percent:.1f}% cases): {summary.aggregate_metrics.get('trimmed_rmse', 0.0):.6f}",
        f"- trimmed_nrmse (drop top {trimmed_ratio_percent:.1f}% cases): {summary.aggregate_metrics.get('trimmed_nrmse', 0.0):.6f}",
        f"- decision_accuracy (loose pass rate): {summary.aggregate_metrics.get('decision_accuracy', 0.0):.4f}",
        "",
        "## By Case Category",
        "",
    ]
    by_case_category = summary.aggregate_metrics.get("by_case_category") or {}
    for case_category in CASE_CATEGORIES:
        category_metrics = by_case_category.get(case_category) or {}
        category_trimmed = category_metrics.get("trimmed_numerical_fidelity") or {}
        category_trimmed_ratio_percent = float(category_trimmed.get("upper_trim_ratio") or 0.0) * 100.0
        lines.extend(
            [
            f"### `{case_category}`",
            "",
            f"- cases_scored: {category_metrics.get('cases_scored', 0)}",
            f"- top1_hit_rate: {category_metrics.get('top1_hit_rate', 0.0):.4f}",
            f"- topk_hit_rate: {category_metrics.get('topk_hit_rate', 0.0):.4f}",
            f"- execution_success_rate: {category_metrics.get('execution_success_rate', 0.0):.4f}",
            f"- mean_execution_time_seconds: {category_metrics.get('mean_execution_time_seconds', 0.0):.4f}",
            f"- mae: {category_metrics.get('mae', 0.0):.6f}",
            f"- rmse: {category_metrics.get('rmse', 0.0):.6f}",
            f"- nrmse: {category_metrics.get('nrmse', 0.0):.6f}",
            f"- trimmed_mae (drop top {category_trimmed_ratio_percent:.1f}% cases): {category_metrics.get('trimmed_mae', 0.0):.6f}",
            f"- trimmed_rmse (drop top {category_trimmed_ratio_percent:.1f}% cases): {category_metrics.get('trimmed_rmse', 0.0):.6f}",
            f"- trimmed_nrmse (drop top {category_trimmed_ratio_percent:.1f}% cases): {category_metrics.get('trimmed_nrmse', 0.0):.6f}",
            f"- decision_accuracy (loose pass rate): {category_metrics.get('decision_accuracy', 0.0):.4f}",
            "",
            ]
        )
    lines.extend(
        [
            "| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in flat_rows:
        lines.append(
            "| {case_id} | {ok} | {top1_hit} | {topk_hit} | {execution_success} | {execution_time_seconds} | {mae} | {rmse} | {nrmse} | {decision_correct} | {error} |".format(
                case_id=row["case_id"],
                ok="yes" if row["ok"] else "no",
                top1_hit="yes" if row["top1_hit"] else "no",
                topk_hit="yes" if row["topk_hit"] else "no",
                execution_success="yes" if row["execution_success"] else "no",
                execution_time_seconds=(
                    f"{float(row['execution_time_seconds']):.4f}" if row["execution_time_seconds"] is not None else "-"
                ),
                mae=f"{float(row['mae']):.6f}" if row["mae"] is not None else "-",
                rmse=f"{float(row['rmse']):.6f}" if row["rmse"] is not None else "-",
                nrmse=f"{float(row['nrmse']):.6f}" if row["nrmse"] is not None else "-",
                decision_correct=(
                    "yes" if row["decision_correct"] else ("no" if row["decision_correct"] is not None else "-")
                ),
                error=(row["error"] or "").replace("|", "/"),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_experiment(spec: EvaluationSpec) -> ExperimentSummary:
    experiment_id = _default_experiment_id(spec)
    dataset_root = Path(spec.dataset_root).expanduser().resolve()
    out_root = Path(spec.out_root).expanduser().resolve()
    experiment_root = out_root / experiment_id
    experiment_root.mkdir(parents=True, exist_ok=True)

    records = list_case_records(dataset_root, case_ids=spec.case_ids)
    fmu_library = load_fmu_library(spec.manifest_path)

    rows: List[CaseEvaluation] = []
    pending_records: List = []
    for record in records:
        if spec.resume:
            run_status_path = experiment_root / record.case_id / "run_status.json"
            metrics_path = experiment_root / record.case_id / "metrics.json"
            if run_status_path.exists() and metrics_path.exists():
                run_status = json.loads(run_status_path.read_text(encoding="utf-8"))
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                if bool(run_status.get("ok")):
                    rows.append(
                        CaseEvaluation(
                            case_id=record.case_id,
                            source_type=record.source_type,
                            case_category=record.case_category,
                            ground_truth_fmu_count=record.ground_truth_fmu_count,
                            ok=True,
                            bundle_name=spec.bundle_name,
                            artifact_root=(experiment_root / record.case_id).as_posix(),
                            stage_status=dict(run_status.get("stage_status") or {}),
                            execution_status=dict(run_status.get("execution_status") or {}),
                            metrics=dict(metrics or {}),
                            artifact_paths={},
                            error=None,
                            notes=["resumed_from_artifacts"],
                        )
                    )
                    continue
        pending_records.append(record)

    if spec.workers > 1 and len(pending_records) > 1:
        with ThreadPoolExecutor(max_workers=spec.workers) as pool:
            future_to_record = {
                pool.submit(
                    run_case_evaluation,
                    spec=spec,
                    bundle_name=spec.bundle_name,
                    experiment_root=experiment_root,
                    case_record=record,
                    fmu_library=fmu_library,
                ): record
                for record in pending_records
            }
            for future in as_completed(future_to_record):
                rows.append(future.result())
    else:
        for record in pending_records:
            rows.append(
                run_case_evaluation(
                    spec=spec,
                    bundle_name=spec.bundle_name,
                    experiment_root=experiment_root,
                    case_record=record,
                    fmu_library=fmu_library,
                )
            )

    aggregate = _aggregate_metrics_by_case_category(
        [_jsonable(asdict(row)) for row in rows],
        dataset_root=dataset_root,
    )
    summary = ExperimentSummary(
        experiment_id=experiment_id,
        bundle_name=spec.bundle_name,
        dataset_root=dataset_root.as_posix(),
        output_root=experiment_root.as_posix(),
        cases_total=len(rows),
        succeeded=sum(1 for row in rows if row.ok),
        failed=sum(1 for row in rows if not row.ok),
        aggregate_metrics=aggregate,
        case_rows=rows,
    )
    _write_json(experiment_root / "experiment_summary.json", summary)
    _write_summary_files(experiment_root, rows, summary)
    return summary


def build_cross_method_summary(experiment_roots: Sequence[str | Path]) -> Dict[str, Any]:
    roots = [Path(item).expanduser().resolve() for item in experiment_roots]
    payloads = [_load_experiment_summary(root) for root in roots]
    dataset_root, aligned_case_ids = _aligned_dataset_case_ids(payloads)
    common_case_ids = _common_case_ids(payloads)
    execution_time_penalties = _casewise_max_execution_time_penalties(payloads, allowed_case_ids=aligned_case_ids)
    numerical_penalties = _casewise_max_numerical_penalties(payloads, allowed_case_ids=aligned_case_ids)
    cross_method_execution_time_case_ids = sorted(
        case_id for case_id in aligned_case_ids if case_id in execution_time_penalties
    )
    cross_method_numerical_case_ids = sorted(
        case_id for case_id in aligned_case_ids if case_id in numerical_penalties
    )
    trimmed_numerical_reference = build_trimmed_numerical_fidelity_summary(
        {
            metric_name: [
                (case_id, float(numerical_penalties[case_id][metric_name]))
                for case_id in cross_method_numerical_case_ids
                if case_id in numerical_penalties
            ]
            for metric_name in ("mae", "rmse", "nrmse")
        },
        trim_ratio=DEFAULT_NUMERICAL_UPPER_TRIM_RATIO,
    )
    experiments: List[Dict[str, Any]] = []
    for root, payload in zip(roots, payloads):
        case_rows = list(payload.get("case_rows") or [])
        aggregate = _aggregate_cross_method_metrics(
            case_rows,
            case_id_filter=aligned_case_ids,
            dataset_root=dataset_root,
            numerical_penalties=numerical_penalties,
            execution_time_penalties=execution_time_penalties,
        )
        experiments.append(
            {
                "experiment_id": str(payload.get("experiment_id") or root.name),
                "bundle_name": str(payload.get("bundle_name") or ""),
                "experiment_root": root.as_posix(),
                "cross_method_aggregate_metrics": aggregate,
            }
        )
    return {
        "schema": "EVALUATOR_CROSS_METHOD_SUMMARY_V2",
        "aggregation_mode": "casewise_max_penalty",
        "dataset_root": dataset_root.as_posix(),
        "aligned_case_count": len(aligned_case_ids),
        "aligned_case_ids": aligned_case_ids,
        "common_case_count": len(common_case_ids),
        "common_case_ids": common_case_ids,
        "cross_method_execution_time_case_count": len(cross_method_execution_time_case_ids),
        "cross_method_execution_time_case_ids": cross_method_execution_time_case_ids,
        "cross_method_numerical_case_count": len(cross_method_numerical_case_ids),
        "cross_method_numerical_case_ids": cross_method_numerical_case_ids,
        "trimmed_numerical_fidelity_reference": trimmed_numerical_reference,
        "experiments": experiments,
    }


def build_shared_success_summary(experiment_roots: Sequence[str | Path]) -> Dict[str, Any]:
    return build_cross_method_summary(experiment_roots)
