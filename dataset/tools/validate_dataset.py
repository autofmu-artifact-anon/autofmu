"""Validate the normalized dataset layout and refresh indexes/manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dataset.common import read_json, write_json

CASE_CATEGORY_SIMPLE = "simple"
CASE_CATEGORY_COMPLEX = "complex"
SINGLE_FMU_COMPLEX_PORT_THRESHOLD = 150


def _required_keys(kind: str) -> List[str]:
    if kind == "asset":
        return ["schema", "asset_id", "name", "fmu_relpath", "metadata_relpath", "ports"]
    if kind == "case":
        return ["schema", "case_id", "title", "requirement", "mbse", "ground_truth_asset_ids", "solution_relpath", "evaluation_artifacts"]
    if kind == "solution":
        return ["schema", "case_id", "selected_asset_ids", "connections", "schedule"]
    return []


def _required_artifact_keys(kind: str) -> List[str]:
    if kind == "retrieval_reference":
        return [
            "schema",
            "case_id",
            "oracle_mode",
            "acceptable_asset_sets",
            "equivalence_class_id",
            "equivalence_reason",
        ]
    if kind == "verification_requirement":
        return [
            "schema",
            "case_id",
            "title",
            "text",
            "signals",
            "scenario_window",
            "judgement_policy",
            "derivation_basis",
            "criteria",
            "decision_rule",
            "tolerances",
            "time_column_aliases",
            "signal_aliases",
        ]
    if kind == "verification_result":
        return [
            "schema",
            "case_id",
            "status",
            "conclusion",
            "summary",
            "evidence_basis",
            "missing_requirements",
            "supports_decision_accuracy",
        ]
    if kind == "trajectory_manifest":
        return [
            "schema",
            "case_id",
            "source_kind",
            "time_column",
            "signal_columns",
            "ground_truth_relpath",
            "input_relpath",
            "supports_numerical_fidelity",
            "column_aliases",
            "signal_aliases",
            "stage_segments",
            "reference_generation_method",
        ]
    return []


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


def _string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for item in values:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _monitored_signal_names(solution: Dict[str, Any]) -> List[str]:
    monitored = solution.get("monitored_outputs")
    if not isinstance(monitored, list):
        return []
    names: List[str] = []
    for item in monitored:
        if isinstance(item, dict):
            text = str(item.get("name") or item.get("signal") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            names.append(text)
    return names


def _resolve_relpath(case_dir: Path, relpath: Any) -> Optional[Path]:
    text = str(relpath or "").strip()
    if not text:
        return None
    return case_dir / text


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _case_complexity_metrics(
    *,
    case_payload: Dict[str, Any],
    solution_payload: Dict[str, Any],
    asset_payloads_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    ground_truth_asset_ids = _string_list(case_payload.get("ground_truth_asset_ids"))
    assets = [asset_payloads_by_id.get(asset_id) or {} for asset_id in ground_truth_asset_ids]
    monitored_outputs = solution_payload.get("monitored_outputs")
    return {
        "rule_id": "simple_complex_v1",
        "fmu_count": len(ground_truth_asset_ids),
        "connection_count": _list_count(solution_payload.get("connections")),
        "stage_count": _list_count(solution_payload.get("stages")),
        "ground_truth_port_count": sum(_list_count(asset.get("ports")) for asset in assets),
        "ground_truth_input_count": sum(_list_count(asset.get("inputs")) for asset in assets),
        "ground_truth_output_count": sum(_list_count(asset.get("outputs")) for asset in assets),
        "monitored_output_count": _list_count(monitored_outputs),
        "single_fmu_port_threshold_for_complex": SINGLE_FMU_COMPLEX_PORT_THRESHOLD,
    }


def _classify_case_category(complexity_metrics: Dict[str, Any]) -> str:
    if int(complexity_metrics.get("fmu_count") or 0) > 1:
        return CASE_CATEGORY_COMPLEX
    if int(complexity_metrics.get("ground_truth_port_count") or 0) >= SINGLE_FMU_COMPLEX_PORT_THRESHOLD:
        return CASE_CATEGORY_COMPLEX
    return CASE_CATEGORY_SIMPLE


def _check_artifact_payload(*, payload: Dict[str, Any], kind: str, case_name: str, issues: List[str]) -> None:
    for key in _required_artifact_keys(kind):
        if key not in payload:
            issues.append(f"{kind} {case_name} missing key {key}")


def validate(*, dataset_root: Path, library_root: Optional[Path] = None) -> Dict[str, Any]:
    assets_root = dataset_root / "assets"
    cases_root = dataset_root / "cases"
    indexes_root = dataset_root / "indexes"
    manifests_root = dataset_root / "manifests"

    asset_rows: List[Dict[str, Any]] = []
    case_rows: List[Dict[str, Any]] = []
    issues: List[str] = []
    asset_payloads_by_id: Dict[str, Dict[str, Any]] = {}

    for asset_dir in sorted(path for path in assets_root.iterdir() if path.is_dir()):
        asset_json = asset_dir / "asset.json"
        metadata_json = asset_dir / "metadata.json"
        if not asset_json.exists():
            issues.append(f"missing asset.json for {asset_dir.name}")
            continue
        payload = read_json(asset_json)
        for key in _required_keys("asset"):
            if key not in payload:
                issues.append(f"asset {asset_dir.name} missing key {key}")
        if not (asset_dir / str(payload.get("fmu_relpath") or "model.fmu")).exists():
            issues.append(f"asset {asset_dir.name} missing model file")
        if not metadata_json.exists():
            issues.append(f"asset {asset_dir.name} missing metadata.json")
        asset_id = str(payload.get("asset_id") or "").strip()
        if asset_id:
            asset_payloads_by_id[asset_id] = dict(payload)
        asset_rows.append(
            {
                "asset_id": payload.get("asset_id"),
                "name": payload.get("name"),
                "source_type": payload.get("source_type"),
                "relative_dir": str(asset_dir.relative_to(dataset_root)),
            }
        )

    all_asset_ids = sorted(str(row["asset_id"]) for row in asset_rows if row.get("asset_id"))
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        case_json = case_dir / "case.json"
        solution_json = case_dir / "solution.json"
        if not case_json.exists():
            issues.append(f"missing case.json for {case_dir.name}")
            continue
        payload = read_json(case_json)
        for key in _required_keys("case"):
            if key not in payload:
                issues.append(f"case {case_dir.name} missing key {key}")
        requirement = payload.get("requirement") if isinstance(payload.get("requirement"), dict) else {}
        if not str(requirement.get("text") or "").strip():
            issues.append(f"case {case_dir.name} missing non-empty requirement.text")
        if not _string_list(requirement.get("signals_of_interest")):
            issues.append(f"case {case_dir.name} missing non-empty requirement.signals_of_interest")
        provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
        source_root = provenance.get("source_root")
        if not isinstance(source_root, str) or not source_root.strip():
            issues.append(f"case {case_dir.name} missing provenance.source_root")
        else:
            source_path = dataset_root / source_root
            if not source_path.exists():
                issues.append(f"case {case_dir.name} source_root missing on disk: {source_root}")

        if not solution_json.exists():
            issues.append(f"case {case_dir.name} missing solution.json")
            continue
        solution = read_json(solution_json)
        for key in _required_keys("solution"):
            if key not in solution:
                issues.append(f"solution {case_dir.name} missing key {key}")
        if not _monitored_signal_names(solution):
            issues.append(f"solution {case_dir.name} missing non-empty monitored_outputs")

        evaluation_artifacts = payload.get("evaluation_artifacts") if isinstance(payload.get("evaluation_artifacts"), dict) else {}
        if not evaluation_artifacts:
            issues.append(f"case {case_dir.name} missing evaluation_artifacts")
        retrieval_reference = None
        verification_requirement = None
        verification_result = None
        trajectory_manifest = None
        retrieval_reference_path = _resolve_relpath(case_dir, evaluation_artifacts.get("retrieval_reference_relpath"))
        verification_requirement_path = _resolve_relpath(case_dir, evaluation_artifacts.get("verification_requirement_relpath"))
        verification_result_path = _resolve_relpath(case_dir, evaluation_artifacts.get("verification_result_relpath"))
        trajectory_manifest_path = _resolve_relpath(case_dir, evaluation_artifacts.get("trajectory_manifest_relpath"))
        for label, path in (
            ("retrieval_reference", retrieval_reference_path),
            ("verification_requirement", verification_requirement_path),
            ("verification_result", verification_result_path),
            ("trajectory_manifest", trajectory_manifest_path),
        ):
            if path is None or not path.exists():
                issues.append(f"case {case_dir.name} missing artifact file {label}")
        if retrieval_reference_path is not None and retrieval_reference_path.exists():
            retrieval_reference = read_json(retrieval_reference_path)
            _check_artifact_payload(
                payload=retrieval_reference,
                kind="retrieval_reference",
                case_name=case_dir.name,
                issues=issues,
            )
        if verification_requirement_path is not None and verification_requirement_path.exists():
            verification_requirement = read_json(verification_requirement_path)
            _check_artifact_payload(
                payload=verification_requirement,
                kind="verification_requirement",
                case_name=case_dir.name,
                issues=issues,
            )
        if verification_result_path is not None and verification_result_path.exists():
            verification_result = read_json(verification_result_path)
            _check_artifact_payload(
                payload=verification_result,
                kind="verification_result",
                case_name=case_dir.name,
                issues=issues,
            )
        if trajectory_manifest_path is not None and trajectory_manifest_path.exists():
            trajectory_manifest = read_json(trajectory_manifest_path)
            _check_artifact_payload(
                payload=trajectory_manifest,
                kind="trajectory_manifest",
                case_name=case_dir.name,
                issues=issues,
            )

        ground_truth_path = _resolve_relpath(case_dir, evaluation_artifacts.get("ground_truth_trajectory_relpath"))
        input_path = _resolve_relpath(case_dir, evaluation_artifacts.get("input_trajectory_relpath"))
        if ground_truth_path is not None and not ground_truth_path.exists():
            issues.append(f"case {case_dir.name} missing ground_truth_trajectory file")
        if input_path is not None and not input_path.exists():
            issues.append(f"case {case_dir.name} missing input_trajectory file")

        supports_execution_metrics = bool(evaluation_artifacts.get("supports_execution_metrics"))
        supports_numerical_fidelity = bool(evaluation_artifacts.get("supports_numerical_fidelity"))
        supports_decision_accuracy = bool(evaluation_artifacts.get("supports_decision_accuracy"))
        if supports_execution_metrics and not solution.get("schedule"):
            issues.append(f"case {case_dir.name} claims execution metrics support without schedule")
        if trajectory_manifest is not None:
            if bool(trajectory_manifest.get("supports_numerical_fidelity")) != supports_numerical_fidelity:
                issues.append(f"case {case_dir.name} numerical fidelity support flag mismatch")
            if supports_numerical_fidelity and not str(trajectory_manifest.get("ground_truth_relpath") or "").strip():
                issues.append(f"case {case_dir.name} supports numerical fidelity without ground truth relpath")
        if verification_result is not None:
            if bool(verification_result.get("supports_decision_accuracy")) != supports_decision_accuracy:
                issues.append(f"case {case_dir.name} decision accuracy support flag mismatch")
            if supports_decision_accuracy:
                if str(verification_result.get("status") or "") != "available":
                    issues.append(f"case {case_dir.name} supports decision accuracy without available verification result")
                if str(verification_result.get("conclusion") or "") not in {"pass", "fail"}:
                    issues.append(f"case {case_dir.name} supports decision accuracy without pass/fail conclusion")
        if retrieval_reference is not None:
            acceptable_asset_sets = retrieval_reference.get("acceptable_asset_sets")
            if not isinstance(acceptable_asset_sets, list) or not acceptable_asset_sets:
                issues.append(f"case {case_dir.name} retrieval_reference has empty acceptable_asset_sets")
            oracle_mode = str(retrieval_reference.get("oracle_mode") or "")
            if oracle_mode == "equivalence_class" and not str(retrieval_reference.get("equivalence_class_id") or "").strip():
                issues.append(f"case {case_dir.name} equivalence_class oracle missing equivalence_class_id")
        if verification_requirement is not None:
            if not isinstance(verification_requirement.get("criteria"), list):
                issues.append(f"case {case_dir.name} verification_requirement.criteria must be a list")
            if not isinstance(verification_requirement.get("decision_rule"), dict):
                issues.append(f"case {case_dir.name} verification_requirement.decision_rule must be an object")
            if not isinstance(verification_requirement.get("signal_aliases"), dict):
                issues.append(f"case {case_dir.name} verification_requirement.signal_aliases must be an object")
            if not isinstance(verification_requirement.get("time_column_aliases"), list):
                issues.append(f"case {case_dir.name} verification_requirement.time_column_aliases must be a list")
        if trajectory_manifest is not None:
            if not isinstance(trajectory_manifest.get("column_aliases"), dict):
                issues.append(f"case {case_dir.name} trajectory_manifest.column_aliases must be an object")
            if not isinstance(trajectory_manifest.get("signal_aliases"), dict):
                issues.append(f"case {case_dir.name} trajectory_manifest.signal_aliases must be an object")
            if not isinstance(trajectory_manifest.get("stage_segments"), list):
                issues.append(f"case {case_dir.name} trajectory_manifest.stage_segments must be a list")

        complexity_metrics = _case_complexity_metrics(
            case_payload=payload,
            solution_payload=solution,
            asset_payloads_by_id=asset_payloads_by_id,
        )
        payload["case_category"] = _classify_case_category(complexity_metrics)
        payload["complexity_metrics"] = complexity_metrics
        payload["candidate_asset_ids"] = list(all_asset_ids)
        write_json(case_json, payload)

        case_rows.append(
            {
                "case_id": payload.get("case_id"),
                "case_category": payload.get("case_category"),
                "complexity_metrics": payload.get("complexity_metrics"),
                "source_type": payload.get("source_type"),
                "relative_dir": str(case_dir.relative_to(dataset_root)),
                "ground_truth_asset_ids": payload.get("ground_truth_asset_ids", []),
                "source_root": str(source_root or ""),
                "retrieval_oracle_mode": str((retrieval_reference or {}).get("oracle_mode") or ""),
                "supports_execution_metrics": supports_execution_metrics,
                "supports_numerical_fidelity": supports_numerical_fidelity,
                "supports_decision_accuracy": supports_decision_accuracy,
            }
        )

    library_manifest_summary: Dict[str, Any] = {}
    if library_root is not None:
        manifest_path = library_root / "manifest.json"
        if not manifest_path.exists():
            issues.append(f"missing library manifest: {manifest_path}")
        else:
            library_manifest = read_json(manifest_path)
            assets_blob = library_manifest.get("assets") if isinstance(library_manifest.get("assets"), list) else []
            for asset in assets_blob:
                if not isinstance(asset, dict):
                    issues.append("library manifest has non-object asset row")
                    continue
                asset_dir = library_root / str(asset.get("relative_dir") or "")
                asset_json = asset_dir / "asset.json"
                model_path = asset_dir / str(asset.get("fmu_file") or "model.fmu")
                if not asset_dir.exists():
                    issues.append(f"library asset dir missing: {asset_dir}")
                    continue
                if not asset_json.exists():
                    issues.append(f"library asset.json missing: {asset_dir}")
                if not model_path.exists():
                    issues.append(f"library model file missing: {model_path}")
                if any(path.suffix.lower() == ".sysml" for path in asset_dir.iterdir()):
                    issues.append(f"library asset unexpectedly contains .sysml: {asset_dir}")
            library_manifest_summary = {
                "library_root": str(library_root),
                "library_asset_count": len(assets_blob),
            }

    _write_jsonl(indexes_root / "assets.jsonl", asset_rows)
    _write_jsonl(indexes_root / "cases.jsonl", case_rows)
    case_category_counts = {
        CASE_CATEGORY_SIMPLE: sum(1 for row in case_rows if row.get("case_category") == CASE_CATEGORY_SIMPLE),
        CASE_CATEGORY_COMPLEX: sum(1 for row in case_rows if row.get("case_category") == CASE_CATEGORY_COMPLEX),
    }
    manifest = {
        "schema": "UNIFIED_DATASET_MANIFEST_V1",
        "asset_count": len(asset_rows),
        "case_count": len(case_rows),
        "case_category_counts": case_category_counts,
        "cases_supporting_execution_metrics": sum(1 for row in case_rows if row.get("supports_execution_metrics")),
        "cases_supporting_numerical_fidelity": sum(1 for row in case_rows if row.get("supports_numerical_fidelity")),
        "cases_supporting_decision_accuracy": sum(1 for row in case_rows if row.get("supports_decision_accuracy")),
        "issues": issues,
        **library_manifest_summary,
    }
    write_json(manifests_root / "dataset_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.validate_dataset")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument("--library-root", default=None, help="Optional pipeline FMU library root.")
    args = parser.parse_args()
    result = validate(
        dataset_root=Path(args.dataset_root).resolve(),
        library_root=Path(args.library_root).resolve() if args.library_root else None,
    )
    print(
        {
            "asset_count": result["asset_count"],
            "case_count": result["case_count"],
            "library_asset_count": result.get("library_asset_count"),
            "issues": len(result["issues"]),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
