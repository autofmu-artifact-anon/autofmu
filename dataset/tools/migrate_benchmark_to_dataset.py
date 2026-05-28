"""Normalize benchmark single-FMU samples into unified dataset assets and cases."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List

from dataset.common import (
    build_benchmark_requirement_text,
    ensure_symlink,
    parse_sysml_model,
    read_json,
    write_json,
    write_text,
)
from dataset.tools.evaluation_artifacts import (
    benchmark_equivalence_class_id,
    choose_benchmark_trajectory_source,
    ordered_unique_text,
    read_csv_columns,
    write_case_evaluation_artifacts,
)


def _load_index(index_csv: Path) -> List[Dict[str, str]]:
    with index_csv.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _normalize_capabilities(meta: Dict[str, Any]) -> Dict[str, Any]:
    impl = meta.get("implementation") if isinstance(meta.get("implementation"), dict) else {}
    cs = impl.get("coSimulation") if isinstance(impl.get("coSimulation"), dict) else {}
    me = impl.get("modelExchange") if isinstance(impl.get("modelExchange"), dict) else {}
    return {
        "needs_execution_tool": bool(cs.get("needsExecutionTool") or me.get("needsExecutionTool")),
        "can_handle_variable_communication_step_size": bool(cs.get("canHandleVariableCommunicationStepSize")),
        "can_interpolate_inputs": bool(cs.get("canInterpolateInputs")),
        "can_run_asynchronously": bool(cs.get("canRunAsynchronuously")),
        "can_be_instantiated_only_once_per_process": bool(
            cs.get("canBeInstantiatedOnlyOncePerProcess") or me.get("canBeInstantiatedOnlyOncePerProcess")
        ),
        "provides_directional_derivatives": bool(
            cs.get("providesDirectionalDerivatives")
            or cs.get("providesDirectionalDerivative")
            or me.get("providesDirectionalDerivatives")
            or me.get("providesDirectionalDerivative")
        ),
        "fixed_internal_step_size": cs.get("fixedInternalStepSize"),
    }


def _normalize_ports(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    ports: List[Dict[str, Any]] = []
    for item in meta.get("variables", []) if isinstance(meta.get("variables"), list) else []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        causality = str(item.get("causality") or "local")
        ports.append(
            {
                "name": str(name),
                "causality": causality,
                "variability": str(item.get("variability") or "continuous"),
                "type": str(item.get("type") or "Real"),
                "unit": str(item.get("unit") or ""),
                "description": str(item.get("description") or ""),
            }
        )
    return ports


def _normalize_default_experiment(meta: Dict[str, Any], simopt_path: Path) -> Dict[str, Any]:
    default = {}
    fmi = meta.get("fmi") if isinstance(meta.get("fmi"), dict) else {}
    if isinstance(fmi.get("defaultExperiment"), dict):
        default.update(fmi["defaultExperiment"])
    if simopt_path.exists():
        try:
            simopt = read_json(simopt_path)
        except Exception:
            simopt = {}
        if isinstance(simopt, dict):
            default.update(
                {
                    "startTime": simopt.get("startTime", default.get("startTime")),
                    "stopTime": simopt.get("stopTime", default.get("stopTime")),
                    "stepSize": simopt.get("stepSize", default.get("stepSize")),
                    "tolerance": simopt.get("tolerance", default.get("tolerance")),
                }
            )
    return {k: v for k, v in default.items() if v is not None}


def _prefixed_header_signals(columns: List[str], prefix: str) -> List[str]:
    signals: List[str] = []
    for column in columns:
        if not column.startswith(prefix):
            continue
        signals.append(column[len(prefix) :])
    return ordered_unique_text(signals)


def _csv_signal_columns(path: Path) -> List[str]:
    columns = read_csv_columns(path)
    if not columns:
        return []
    first = str(columns[0]).strip().lower()
    if first in {"time", "t", "timestamp"}:
        return ordered_unique_text(columns[1:])
    return ordered_unique_text(columns)


def _infer_signal_sets(
    *,
    metadata: Dict[str, Any],
    ref_src: Path,
    timeseries_src: Path,
    input_src: Path,
) -> Dict[str, List[str]]:
    chosen_trajectory = ref_src if ref_src.exists() else timeseries_src
    trajectory_columns = _csv_signal_columns(chosen_trajectory) if chosen_trajectory.exists() else []
    input_columns = _csv_signal_columns(input_src) if input_src.exists() else []

    inputs = ordered_unique_text(metadata.get("inputs", []))
    outputs = ordered_unique_text(metadata.get("outputs", []))
    if not inputs:
        inputs = _prefixed_header_signals(trajectory_columns, "input_")
    if not inputs:
        inputs = input_columns

    if not outputs:
        outputs = _prefixed_header_signals(trajectory_columns, "output_")
    if not outputs:
        outputs = ordered_unique_text(column for column in trajectory_columns if column not in set(inputs))

    if not outputs:
        outputs = ordered_unique_text(
            port["name"]
            for port in metadata.get("ports", [])
            if isinstance(port, dict) and str(port.get("causality") or "") in {"output", "local"}
        )
    if not inputs:
        inputs = ordered_unique_text(
            port["name"]
            for port in metadata.get("ports", [])
            if isinstance(port, dict) and str(port.get("causality") or "") == "input"
        )

    return {
        "inputs": inputs,
        "outputs": outputs,
    }


def _benchmark_requirement_text(*, metadata: Dict[str, Any]) -> str:
    text = build_benchmark_requirement_text(
        model_name=metadata["name"],
        description=metadata["description"],
        inputs=metadata["inputs"],
        outputs=metadata["outputs"],
    )
    if text.strip():
        return text
    monitor_text = ", ".join(metadata["outputs"]) if metadata["outputs"] else "the archived trajectory signals"
    experiment = metadata.get("default_experiment") or {}
    return (
        f"Execute {metadata['name']} over the default experiment from "
        f"{experiment.get('startTime', 0.0)}s to {experiment.get('stopTime', 1.0)}s "
        f"and reproduce the reference trajectory for {monitor_text}."
    )


def migrate(*, dataset_root: Path, clear: bool = False) -> Dict[str, Any]:
    sources_root = dataset_root / "sources" / "fmu-benchmark-mini"
    assets_root = dataset_root / "assets"
    cases_root = dataset_root / "cases"
    indexes_root = dataset_root / "indexes"
    manifests_root = dataset_root / "manifests"
    index_csv = sources_root / "index.csv"
    if not index_csv.exists():
        raise FileNotFoundError(f"Benchmark index missing: {index_csv}")

    rows = _load_index(index_csv)
    asset_rows: List[Dict[str, Any]] = []
    case_rows: List[Dict[str, Any]] = []
    benchmark_retrieval_index: List[Dict[str, Any]] = []

    for row in rows:
        dataset_id = str(row.get("dataset_id") or "").strip()
        if not dataset_id:
            continue
        asset_id = f"asset_bench_{dataset_id}"
        case_id = f"case_bench_{dataset_id}"

        fmu_src = (sources_root / row["path_to_fmu"]).resolve()
        raw_meta_src = (sources_root / row["path_to_metadata"]).resolve()
        sysml_src = fmu_src.with_suffix(".sysml")
        ref_src = fmu_src.parent / f"{fmu_src.stem}_ref.csv"
        timeseries_src = fmu_src.parent / f"{fmu_src.stem}.timeseries.csv"
        input_src = fmu_src.parent / f"{fmu_src.stem}_in.csv"
        simopt_src = fmu_src.parent / f"{fmu_src.stem}_simopt.json"
        raw_meta = read_json(raw_meta_src)

        ports = _normalize_ports(raw_meta)
        metadata = {
            "schema": "UNIFIED_FMU_METADATA_V1",
            "asset_id": asset_id,
            "dataset_id": dataset_id,
            "name": str((raw_meta.get("fmi") or {}).get("modelName") or row.get("model_name") or fmu_src.stem),
            "description": str((raw_meta.get("fmi") or {}).get("description") or row.get("model_name") or ""),
            "fmi_version": str((raw_meta.get("fmi") or {}).get("fmiVersion") or row.get("fmiVersion") or ""),
            "fmi_types": list((raw_meta.get("fmi") or {}).get("fmiTypes") or [x.strip() for x in str(row.get("fmiTypes") or "").split(";") if x.strip()]),
            "ports": ports,
            "inputs": [port["name"] for port in ports if port["causality"] == "input"],
            "outputs": [port["name"] for port in ports if port["causality"] == "output"],
            "backend_kind": "native_fmu",
            "capabilities": _normalize_capabilities(raw_meta),
            "default_experiment": _normalize_default_experiment(raw_meta, simopt_src),
        }
        signal_sets = _infer_signal_sets(
            metadata=metadata,
            ref_src=ref_src,
            timeseries_src=timeseries_src,
            input_src=input_src,
        )
        metadata["inputs"] = signal_sets["inputs"]
        metadata["outputs"] = signal_sets["outputs"]

        asset_dir = assets_root / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        ensure_symlink(fmu_src, asset_dir / "model.fmu")
        write_json(asset_dir / "metadata.json", metadata)
        write_text(asset_dir / "description.md", metadata["description"] or metadata["name"])
        if ref_src.exists():
            ensure_symlink(ref_src, asset_dir / "ref.csv")
        if input_src.exists():
            ensure_symlink(input_src, asset_dir / "input.csv")
        if simopt_src.exists():
            ensure_symlink(simopt_src, asset_dir / "simopt.json")

        asset_payload = {
            "schema": "UNIFIED_ASSET_V1",
            "asset_id": asset_id,
            "source_type": "benchmark_single_fmu",
            "source_id": dataset_id,
            "name": metadata["name"],
            "description": metadata["description"],
            "fmu_relpath": "model.fmu",
            "metadata_relpath": "metadata.json",
            "description_relpath": "description.md",
            "fmi_version": metadata["fmi_version"],
            "fmi_types": metadata["fmi_types"],
            "inputs": metadata["inputs"],
            "outputs": metadata["outputs"],
            "ports": metadata["ports"],
            "capabilities": metadata["capabilities"],
            "default_experiment": metadata["default_experiment"],
            "backend_kind": metadata["backend_kind"],
            "tags": [str(row.get("tool_id") or ""), str(row.get("platform") or "")],
            "library_visible": True,
            "ground_truth_only": False,
            "case_origin": [case_id],
            "provenance": {
                "source_repo": row.get("source_repo"),
                "source_path": row.get("source_path"),
                "path_to_fmu": row.get("path_to_fmu"),
                "path_to_metadata": row.get("path_to_metadata"),
            },
        }
        write_json(asset_dir / "asset.json", asset_payload)
        asset_rows.append(asset_payload)

        if sysml_src.exists():
            sysml_text = sysml_src.read_text(encoding="utf-8")
            mbse = parse_sysml_model(sysml_text, sysml_name=sysml_src.name)
        else:
            sysml_text = ""
            mbse = {
                "package_name": metadata["name"],
                "system_name": metadata["name"],
                "components": [{"name": metadata["name"], "component_type": metadata["name"], "ports": []}],
                "connections": [],
                "adjacency": {metadata["name"]: []},
                "constraints": [],
            }

        case_dir = cases_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        if sysml_src.exists():
            ensure_symlink(sysml_src, case_dir / "system.sysml")

        requirement_text = _benchmark_requirement_text(metadata=metadata)
        requirement_payload = {
            "id": f"REQ-BENCH-{dataset_id}",
            "title": metadata["name"],
            "description": requirement_text,
            "text": requirement_text,
            "scenario": metadata["default_experiment"],
            "acceptance_criteria": [],
            "signals_of_interest": metadata["outputs"],
        }

        solution_payload = {
            "schema": "UNIFIED_SOLUTION_V1",
            "case_id": case_id,
            "selected_asset_ids": [asset_id],
            "connections": [],
            "external_inputs": [
                {"name": name, "targets": [f"{asset_id}.{name}"]}
                for name in metadata["inputs"]
            ],
            "monitored_outputs": [
                {"name": name, "source": f"{asset_id}.{name}"}
                for name in metadata["outputs"]
            ],
            "schedule": {
                "kind": "single_fmu",
                "start_time": metadata["default_experiment"].get("startTime", 0.0),
                "stop_time": metadata["default_experiment"].get("stopTime", 1.0),
                "step_size": metadata["default_experiment"].get("stepSize", 0.01),
            },
            "execution_order": [asset_id],
            "adapters": [],
            "loop_resolution": [],
            "notes": ["Auto-generated single-FMU benchmark solution."],
        }
        write_json(case_dir / "solution.json", solution_payload)
        write_text(case_dir / "notes.md", f"Normalized from benchmark dataset row {dataset_id}.")

        trajectory_sources = choose_benchmark_trajectory_source(source_dir=fmu_src.parent, stem=fmu_src.stem)
        ground_truth_trajectory_src = trajectory_sources["ground_truth_source"]
        trajectory_source_kind = str(trajectory_sources["source_kind"])
        trajectory_columns = _csv_signal_columns(ground_truth_trajectory_src) if ground_truth_trajectory_src else []
        evaluation_artifacts = write_case_evaluation_artifacts(
            case_dir=case_dir,
            case_payload={"case_id": case_id, "requirement": requirement_payload},
            solution_payload=solution_payload,
            verification_title=f"Verify benchmark FMU {metadata['name']}",
            verification_text=(
                f"Run the benchmark FMU {metadata['name']} under the default experiment and verify that the "
                f"generated trajectory matches the archived ground-truth trajectory for monitored outputs "
                f"{', '.join(metadata['outputs']) or 'the available signals'}."
            ),
            judgement_policy="trajectory_match",
            derivation_basis={
                "source_type": "benchmark_single_fmu_case",
                "source_root": str(fmu_src.parent.relative_to(dataset_root)),
                "ground_truth_source": ground_truth_trajectory_src.name if ground_truth_trajectory_src else "",
                "input_source": input_src.name if input_src.exists() else "",
                "signals": list(metadata["outputs"]),
            },
            verification_status="available",
            verification_conclusion="pass",
            verification_summary=(
                "The normalized benchmark case ships with an archived reference trajectory from the source dataset; "
                "that trajectory is treated as the ground-truth verification outcome for the reference model."
            ),
            missing_requirements=[],
            retrieval_oracle_mode="equivalence_class",
            retrieval_equivalence_class_id=benchmark_equivalence_class_id(
                title=metadata["name"],
                inputs=metadata["inputs"],
                outputs=metadata["outputs"],
            ),
            retrieval_equivalence_reason="benchmark requirement text does not distinguish identical model/interface variants",
            trajectory_source_kind=trajectory_source_kind,
            ground_truth_source=ground_truth_trajectory_src,
            input_source=trajectory_sources["input_source"],
            trajectory_signal_columns=trajectory_columns,
            criteria=[
                {
                    "metric": "trajectory_match",
                    "operator": "<=",
                    "value": metadata["default_experiment"].get("tolerance", 1e-5),
                    "signals": list(metadata["outputs"]),
                }
            ],
            decision_rule={
                "kind": "trajectory_tolerance",
                "signals": list(metadata["outputs"]),
                "time_column": "time",
                "tolerance": metadata["default_experiment"].get("tolerance", 1e-5),
            },
            tolerances={"trajectory_match": metadata["default_experiment"].get("tolerance", 1e-5)},
            time_column="time",
            time_column_aliases=("Time",),
            signal_aliases={signal: [signal] for signal in metadata["outputs"]},
        )

        case_payload = {
            "schema": "UNIFIED_CASE_V1",
            "case_id": case_id,
            "source_type": "benchmark_single_fmu_case",
            "title": requirement_payload["title"],
            "description": metadata["description"],
            "requirement": requirement_payload,
            "mbse": {
                "sysml_relpath": "system.sysml" if sysml_src.exists() else "",
                **mbse,
            },
            "ground_truth_asset_ids": [asset_id],
            "candidate_asset_ids": [],
            "solution_relpath": "solution.json",
            "expected_behavior": (
                f"Ground-truth trajectory available via {trajectory_source_kind}."
                if ground_truth_trajectory_src is not None
                else "Single FMU benchmark reference."
            ),
            "evaluation_artifacts": evaluation_artifacts,
            "provenance": {
                "benchmark_dataset_id": dataset_id,
                "benchmark_index_row": row,
                "source_root": str(fmu_src.parent.relative_to(dataset_root)),
            },
        }
        write_json(case_dir / "case.json", case_payload)
        case_rows.append(case_payload)
        benchmark_retrieval_index.append(
            {
                "case_dir": case_dir,
                "asset_id": asset_id,
                "equivalence_class_id": benchmark_equivalence_class_id(
                    title=metadata["name"],
                    inputs=metadata["inputs"],
                    outputs=metadata["outputs"],
                ),
            }
        )

    acceptable_by_class: Dict[str, List[List[str]]] = {}
    for item in benchmark_retrieval_index:
        acceptable_by_class.setdefault(str(item["equivalence_class_id"]), []).append([str(item["asset_id"])])
    for item in benchmark_retrieval_index:
        retrieval_path = Path(item["case_dir"]) / "retrieval_reference.json"
        payload = read_json(retrieval_path)
        payload["acceptable_asset_sets"] = acceptable_by_class[str(item["equivalence_class_id"])]
        write_json(retrieval_path, payload)

    write_json(manifests_root / "benchmark_manifest.json", {"assets": len(asset_rows), "cases": len(case_rows)})
    return {"assets": len(asset_rows), "cases": len(case_rows)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.migrate_benchmark_to_dataset")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    args = parser.parse_args()
    result = migrate(dataset_root=Path(args.dataset_root).resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
