from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from dataset.common import read_json

from .types import CaseRecord

CASE_CATEGORY_SIMPLE = "simple"
CASE_CATEGORY_COMPLEX = "complex"
LEGACY_CASE_CATEGORY_MAP = {
    "single_fmu": CASE_CATEGORY_SIMPLE,
    "multi_fmu": CASE_CATEGORY_COMPLEX,
}


def _normalized_case_category(raw: Any) -> str:
    text = str(raw or "").strip()
    if text in {CASE_CATEGORY_SIMPLE, CASE_CATEGORY_COMPLEX}:
        return text
    return LEGACY_CASE_CATEGORY_MAP.get(text, "")


def _record_from_case_root(case_root: Path) -> CaseRecord:
    payload = read_json(case_root / "case.json")
    evaluation_artifacts = (
        payload.get("evaluation_artifacts") if isinstance(payload.get("evaluation_artifacts"), dict) else {}
    )
    ground_truth_asset_ids = [str(item) for item in payload.get("ground_truth_asset_ids", []) if str(item)]
    ground_truth_fmu_count = len(ground_truth_asset_ids)
    complexity_metrics = payload.get("complexity_metrics") if isinstance(payload.get("complexity_metrics"), dict) else {}
    case_category = _normalized_case_category(payload.get("case_category"))
    if not case_category:
        ground_truth_port_count = int(complexity_metrics.get("ground_truth_port_count") or 0)
        case_category = (
            CASE_CATEGORY_COMPLEX
            if ground_truth_fmu_count > 1 or ground_truth_port_count >= 150
            else CASE_CATEGORY_SIMPLE
        )
    return CaseRecord(
        case_id=str(payload.get("case_id") or case_root.name),
        source_type=str(payload.get("source_type") or "unknown"),
        case_root=case_root.resolve(),
        title=str(payload.get("title") or ""),
        case_category=case_category,
        ground_truth_fmu_count=ground_truth_fmu_count,
        ground_truth_asset_ids=ground_truth_asset_ids,
        candidate_asset_ids=[str(item) for item in payload.get("candidate_asset_ids", []) if str(item)],
        solution_relpath=str(payload.get("solution_relpath") or "solution.json"),
        supports_execution_metrics=bool(evaluation_artifacts.get("supports_execution_metrics")),
        supports_numerical_fidelity=bool(evaluation_artifacts.get("supports_numerical_fidelity")),
        supports_decision_accuracy=bool(evaluation_artifacts.get("supports_decision_accuracy")),
        evaluation_artifacts=dict(evaluation_artifacts),
        extra_metadata={
            "description": payload.get("description"),
            "expected_behavior": payload.get("expected_behavior"),
            "provenance": payload.get("provenance"),
            "complexity_metrics": complexity_metrics,
        },
    )


def _iter_index_rows(index_path: Path) -> Iterable[Dict[str, Any]]:
    for line in index_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        yield json.loads(text)


def list_case_records(dataset_root: str | Path, case_ids: Sequence[str] | None = None) -> List[CaseRecord]:
    root = Path(dataset_root).expanduser().resolve()
    selected = [str(item) for item in case_ids] if case_ids else []
    selected_set = set(selected)
    records_by_id: Dict[str, CaseRecord] = {}

    index_path = root / "indexes" / "cases.jsonl"
    if index_path.exists():
        for row in _iter_index_rows(index_path):
            case_id = str(row.get("case_id") or "").strip()
            if not case_id:
                continue
            if selected_set and case_id not in selected_set:
                continue
            case_root = root / str(row.get("relative_dir") or "") if row.get("relative_dir") else root / "cases" / case_id
            records_by_id[case_id] = _record_from_case_root(case_root)
    else:
        for case_root in sorted((root / "cases").iterdir(), key=lambda path: path.name):
            if not case_root.is_dir():
                continue
            record = _record_from_case_root(case_root)
            if selected_set and record.case_id not in selected_set:
                continue
            records_by_id[record.case_id] = record

    if selected:
        missing = [case_id for case_id in selected if case_id not in records_by_id]
        if missing:
            missing_text = ", ".join(missing)
            raise FileNotFoundError(f"Unknown case ids under dataset {root}: {missing_text}")
        return [records_by_id[case_id] for case_id in selected]

    return [records_by_id[case_id] for case_id in sorted(records_by_id)]
