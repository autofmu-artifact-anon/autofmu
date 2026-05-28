"""Normalize manual multi-FMU cases into unified dataset assets and cases."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dataset.common import ensure_symlink, parse_sysml_model, read_json, summarize_requirement_payload, write_json, write_text
from dataset.tools.evaluation_artifacts import ordered_unique_text, write_case_evaluation_artifacts


def _normalize_manual_fmu_metadata(
    *,
    case_id: str,
    fmu_name: str,
    fmu_entry: Dict[str, Any],
    spec_payload: Dict[str, Any],
    orchestration_payload: Dict[str, Any],
) -> Dict[str, Any]:
    ports: List[Dict[str, Any]] = []
    for field_name, causality in (("inputs", "input"), ("outputs", "output")):
        for item in spec_payload.get(field_name, []) if isinstance(spec_payload.get(field_name), list) else []:
            if not isinstance(item, dict):
                continue
            ports.append(
                {
                    "name": str(item.get("name") or ""),
                    "causality": causality,
                    "type": str(item.get("type") or "Real"),
                    "unit": str(item.get("unit") or ""),
                    "description": str(item.get("description") or ""),
                    "variability": "continuous",
                }
            )
    for item in spec_payload.get("parameters", []) if isinstance(spec_payload.get("parameters"), list) else []:
        if not isinstance(item, dict):
            continue
        ports.append(
            {
                "name": str(item.get("name") or ""),
                "causality": "parameter",
                "type": str(item.get("type") or "Real"),
                "unit": str(item.get("unit") or ""),
                "description": str(item.get("description") or ""),
                "variability": "fixed",
            }
        )

    step_size = 0.01
    for entry in orchestration_payload.get("fmus", []) if isinstance(orchestration_payload.get("fmus"), list) else []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("name") or "") == fmu_name and entry.get("step_size") is not None:
            step_size = float(entry.get("step_size"))
            break

    default_experiment = {"startTime": 0.0, "stopTime": 1.0, "stepSize": step_size}
    if isinstance(orchestration_payload.get("co_simulation"), dict):
        cfg = orchestration_payload["co_simulation"]
        default_experiment = {
            "startTime": cfg.get("start_time", 0.0),
            "stopTime": cfg.get("stop_time", 1.0),
            "stepSize": cfg.get("step_size", step_size),
        }
    elif isinstance(orchestration_payload.get("simulation_config"), dict):
        cfg = orchestration_payload["simulation_config"]
        default_experiment = {
            "startTime": cfg.get("start_time", 0.0),
            "stopTime": cfg.get("stop_time", 1.0),
            "stepSize": cfg.get("step_size", step_size),
        }

    return {
        "schema": "UNIFIED_FMU_METADATA_V1",
        "asset_id": f"asset_case_{case_id}__{fmu_name}",
        "name": fmu_name,
        "description": str(spec_payload.get("description") or fmu_entry.get("description") or ""),
        "backend_kind": "python_source_fmu",
        "fmi_version": str(fmu_entry.get("fmi_version") or orchestration_payload.get("fmi_version") or "2.0"),
        "fmi_types": [str(fmu_entry.get("type") or "Co-Simulation")],
        "ports": ports,
        "inputs": [port["name"] for port in ports if port["causality"] == "input"],
        "outputs": [port["name"] for port in ports if port["causality"] == "output"],
        "capabilities": {
            "needs_execution_tool": False,
            "can_handle_variable_communication_step_size": True,
            "can_interpolate_inputs": False,
            "can_run_asynchronously": False,
            "can_be_instantiated_only_once_per_process": False,
            "provides_directional_derivatives": False,
        },
        "default_experiment": default_experiment,
    }


def _normalize_external_inputs(
    *,
    orchestration_payload: Dict[str, Any],
    requirement_payload: Dict[str, Any],
    asset_name_to_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    ext_list = orchestration_payload.get("external_inputs")
    if not isinstance(ext_list, list):
        ext_list = []
        exo = orchestration_payload.get("exogenous_inputs")
        if isinstance(exo, list):
            ext_list = exo

    for entry in ext_list:
        if not isinstance(entry, dict):
            continue
        targets: List[str] = []
        if isinstance(entry.get("target"), str):
            fmu_name, _, signal_name = str(entry["target"]).partition(".")
            targets.append(f"{asset_name_to_id.get(fmu_name, fmu_name)}.{signal_name}")
        if isinstance(entry.get("targets"), list):
            for target in entry["targets"]:
                if not isinstance(target, str):
                    continue
                fmu_name, _, signal_name = target.partition(".")
                targets.append(f"{asset_name_to_id.get(fmu_name, fmu_name)}.{signal_name}")
        if targets:
            items.append(
                {
                    "name": str(entry.get("name") or ""),
                    "targets": targets,
                    "default": entry.get("default"),
                    "unit": entry.get("unit"),
                }
            )

    if items:
        return items

    scenario = requirement_payload.get("scenario")
    if isinstance(scenario, dict) and isinstance(scenario.get("inputs"), dict):
        for name in sorted(scenario["inputs"].keys()):
            items.append({"name": name, "targets": [], "default": scenario["inputs"][name]})
    return items


def _instance_name_to_asset_id(
    *,
    orchestration_payload: Dict[str, Any],
    asset_name_to_id: Dict[str, str],
) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in orchestration_payload.get("fmus", []) if isinstance(orchestration_payload.get("fmus"), list) else []:
        if not isinstance(entry, dict):
            continue
        instance_name = str(entry.get("instance_name") or entry.get("name") or "").strip()
        fmu_name = str(entry.get("fmu_name") or entry.get("name") or "").strip()
        asset_id = asset_name_to_id.get(fmu_name) or asset_name_to_id.get(instance_name)
        if instance_name and asset_id:
            mapping[instance_name] = asset_id
    return mapping


def _signal_sources_by_name(asset_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    mapping: Dict[str, List[Dict[str, Any]]] = {}
    for asset_id, metadata in asset_metadata.items():
        for port in metadata.get("ports", []) if isinstance(metadata.get("ports"), list) else []:
            if not isinstance(port, dict) or str(port.get("causality") or "") != "output":
                continue
            signal = str(port.get("name") or "").strip()
            if not signal:
                continue
            mapping.setdefault(signal, []).append(
                {
                    "source": f"{asset_id}.{signal}",
                    "unit": port.get("unit"),
                }
            )
    return mapping


def _coerce_manual_monitored_outputs(
    *,
    orchestration_payload: Dict[str, Any],
    requirement_payload: Dict[str, Any],
    external_inputs: List[Dict[str, Any]],
    instance_name_to_asset: Dict[str, str],
    signal_sources: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    monitored_outputs: List[Dict[str, Any]] = []
    seen_sources = set()
    external_names = {
        str(item.get("name") or "").strip()
        for item in external_inputs
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }

    raw_monitored = orchestration_payload.get("monitored_outputs")
    if not isinstance(raw_monitored, list):
        raw_monitored = orchestration_payload.get("logged_variables") if isinstance(orchestration_payload.get("logged_variables"), list) else []

    def _append(name: str, source: str, unit: Any = None) -> None:
        if not name or not source or source in seen_sources:
            return
        seen_sources.add(source)
        monitored_outputs.append({"name": name, "source": source, "unit": unit})

    for item in raw_monitored:
        if isinstance(item, dict):
            source = str(item.get("source") or "").strip()
            if not source or "." not in source:
                continue
            alias, _, signal = source.partition(".")
            asset_id = instance_name_to_asset.get(alias)
            if not asset_id:
                continue
            unit = item.get("unit")
            _append(str(item.get("name") or signal).strip(), f"{asset_id}.{signal}", unit)
            continue

        text = str(item or "").strip()
        if not text or text in external_names:
            continue
        if "." not in text:
            continue
        alias, _, signal = text.partition(".")
        asset_id = instance_name_to_asset.get(alias)
        if not asset_id:
            continue
        unit = None
        for candidate in signal_sources.get(signal, []):
            if candidate.get("source") == f"{asset_id}.{signal}":
                unit = candidate.get("unit")
                break
        _append(signal, f"{asset_id}.{signal}", unit)

    requirement_signals = requirement_payload.get("signals_of_interest") if isinstance(requirement_payload.get("signals_of_interest"), list) else []
    for signal_name in requirement_signals:
        signal = str(signal_name or "").strip()
        if not signal or signal in external_names:
            continue
        for candidate in signal_sources.get(signal, []):
            _append(signal, str(candidate.get("source") or ""), candidate.get("unit"))
            break

    return monitored_outputs


def migrate(*, dataset_root: Path) -> Dict[str, Any]:
    sources_root = dataset_root / "sources" / "cases"
    assets_root = dataset_root / "assets"
    cases_root = dataset_root / "cases"

    asset_rows: List[Dict[str, Any]] = []
    case_rows: List[Dict[str, Any]] = []

    for case_source_dir in sorted(path for path in sources_root.iterdir() if path.is_dir()):
        case_id = case_source_dir.name
        requirement_payload = read_json(case_source_dir / "requirement.json")
        fmu_list_payload = read_json(case_source_dir / "fmu_list.json")
        orchestration_payload = read_json(case_source_dir / "orchestration.json")
        ground_truth_payload = read_json(case_source_dir / "ground_truth.json")
        sysml_src = case_source_dir / "system.sysml"
        sysml_text = sysml_src.read_text(encoding="utf-8")
        mbse = parse_sysml_model(sysml_text, sysml_name=sysml_src.name)

        fmus = fmu_list_payload.get("fmus") if isinstance(fmu_list_payload.get("fmus"), list) else []
        asset_name_to_id: Dict[str, str] = {}
        asset_metadata_by_id: Dict[str, Dict[str, Any]] = {}
        for entry in fmus:
            if not isinstance(entry, dict):
                continue
            fmu_name = str(entry.get("name") or "")
            if not fmu_name:
                continue
            asset_id = f"asset_case_{case_id}__{fmu_name}"
            asset_name_to_id[fmu_name] = asset_id

            spec_path = case_source_dir / "fmu_specs" / f"fmu_{fmu_name}.json"
            spec_payload = read_json(spec_path) if spec_path.exists() else {"name": fmu_name, "description": entry.get("description") or ""}
            metadata = _normalize_manual_fmu_metadata(
                case_id=case_id,
                fmu_name=fmu_name,
                fmu_entry=entry,
                spec_payload=spec_payload,
                orchestration_payload=orchestration_payload,
            )

            asset_dir = assets_root / asset_id
            asset_dir.mkdir(parents=True, exist_ok=True)
            fmu_rel = entry.get("path")
            if isinstance(fmu_rel, str) and fmu_rel:
                ensure_symlink((case_source_dir / fmu_rel).resolve(), asset_dir / "model.fmu")
            else:
                fallback = case_source_dir / "fmus" / f"{fmu_name}.fmu"
                if fallback.exists():
                    ensure_symlink(fallback.resolve(), asset_dir / "model.fmu")
            write_json(asset_dir / "metadata.json", metadata)
            asset_metadata_by_id[asset_id] = metadata
            spec_md = case_source_dir / "fmu_specs" / f"fmu_{fmu_name}.md"
            if spec_md.exists():
                ensure_symlink(spec_md.resolve(), asset_dir / "description.md")
            else:
                write_text(asset_dir / "description.md", metadata["description"] or fmu_name)

            asset_payload = {
                "schema": "UNIFIED_ASSET_V1",
                "asset_id": asset_id,
                "source_type": "manual_case_fmu",
                "source_id": f"{case_id}::{fmu_name}",
                "name": fmu_name,
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
                "tags": [case_id, "manual_case"],
                "library_visible": True,
                "ground_truth_only": False,
                "case_origin": [case_id],
                "provenance": {
                    "case_id": case_id,
                    "legacy_fmu_list_entry": entry,
                },
            }
            write_json(asset_dir / "asset.json", asset_payload)
            asset_rows.append(asset_payload)

        case_dir = cases_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        ensure_symlink(sysml_src.resolve(), case_dir / "system.sysml")
        log_src = case_source_dir / "LOG.md"
        if log_src.exists():
            ensure_symlink(log_src.resolve(), case_dir / "notes.md")
        else:
            write_text(case_dir / "notes.md", f"Normalized from manual case {case_id}.")

        correct_fmus = ground_truth_payload.get("correct_fmus") if isinstance(ground_truth_payload.get("correct_fmus"), list) else []
        selected_asset_ids: List[str] = []
        for item in correct_fmus:
            label = str(item)
            fmu_name = label.replace("fmu_", "", 1) if label.startswith("fmu_") else label
            if fmu_name in asset_name_to_id:
                selected_asset_ids.append(asset_name_to_id[fmu_name])

        connections = []
        for conn in ground_truth_payload.get("correct_connections", []) if isinstance(ground_truth_payload.get("correct_connections"), list) else []:
            if not isinstance(conn, dict):
                continue
            src = str(conn.get("from") or "")
            dst = str(conn.get("to") or "")
            if "." not in src or "." not in dst:
                continue
            src_fmu, _, src_sig = src.partition(".")
            dst_fmu, _, dst_sig = dst.partition(".")
            src_name = src_fmu.replace("fmu_", "", 1) if src_fmu.startswith("fmu_") else src_fmu
            dst_name = dst_fmu.replace("fmu_", "", 1) if dst_fmu.startswith("fmu_") else dst_fmu
            connections.append(
                {
                    "source": f"{asset_name_to_id.get(src_name, src_name)}.{src_sig}",
                    "target": f"{asset_name_to_id.get(dst_name, dst_name)}.{dst_sig}",
                }
            )

        external_inputs = _normalize_external_inputs(
            orchestration_payload=orchestration_payload,
            requirement_payload=requirement_payload,
            asset_name_to_id=asset_name_to_id,
        )
        monitored_outputs = _coerce_manual_monitored_outputs(
            orchestration_payload=orchestration_payload,
            requirement_payload=requirement_payload,
            external_inputs=external_inputs,
            instance_name_to_asset=_instance_name_to_asset_id(
                orchestration_payload=orchestration_payload,
                asset_name_to_id=asset_name_to_id,
            ),
            signal_sources=_signal_sources_by_name(asset_metadata_by_id),
        )
        schedule_blob = {
            "kind": "co_simulation",
            "co_simulation": orchestration_payload.get("co_simulation") or orchestration_payload.get("simulation_config") or {},
            "co_simulation_type": orchestration_payload.get("co_simulation_type") or "fixed_step",
        }

        solution_payload = {
            "schema": "UNIFIED_SOLUTION_V1",
            "case_id": case_id,
            "selected_asset_ids": selected_asset_ids,
            "connections": connections,
            "external_inputs": external_inputs,
            "monitored_outputs": monitored_outputs,
            "schedule": schedule_blob,
            "execution_order": [
                asset_name_to_id.get(str(name), str(name))
                for name in orchestration_payload.get("execution_order", [])
            ]
            if isinstance(orchestration_payload.get("execution_order"), list)
            else [],
            "adapters": [],
            "loop_resolution": [],
            "notes": [str(ground_truth_payload.get("expected_behavior") or "").strip()],
        }
        write_json(case_dir / "solution.json", solution_payload)

        case_payload = {
            "schema": "UNIFIED_CASE_V1",
            "case_id": case_id,
            "source_type": "manual_multi_fmu_case",
            "title": str(requirement_payload.get("title") or case_id),
            "description": str(requirement_payload.get("description") or fmu_list_payload.get("description") or ""),
            "requirement": {
                "id": str(requirement_payload.get("id") or case_id),
                "title": str(requirement_payload.get("title") or case_id),
                "description": str(requirement_payload.get("description") or ""),
                "text": summarize_requirement_payload(requirement_payload),
                "scenario": requirement_payload.get("scenario") if isinstance(requirement_payload.get("scenario"), dict) else {},
                "acceptance_criteria": requirement_payload.get("acceptance_criteria") if isinstance(requirement_payload.get("acceptance_criteria"), list) else [],
                "signals_of_interest": requirement_payload.get("signals_of_interest") if isinstance(requirement_payload.get("signals_of_interest"), list) else [],
            },
            "mbse": {
                "sysml_relpath": "system.sysml",
                **mbse,
            },
            "ground_truth_asset_ids": selected_asset_ids,
            "candidate_asset_ids": [],
            "solution_relpath": "solution.json",
            "expected_behavior": str(ground_truth_payload.get("expected_behavior") or ""),
            "provenance": {
                "source_root": str(case_source_dir.relative_to(dataset_root)),
                "legacy_files": {
                    "requirement": "requirement.json",
                    "fmu_list": "fmu_list.json",
                    "orchestration": "orchestration.json",
                    "ground_truth": "ground_truth.json",
                }
            },
        }
        case_payload["evaluation_artifacts"] = write_case_evaluation_artifacts(
            case_dir=case_dir,
            case_payload=case_payload,
            solution_payload=solution_payload,
            verification_title=f"{case_payload['title']} Verification Requirement",
            verification_text=(
                f"{case_payload['requirement']['text']} "
                "Verification should conclude pass only when the co-simulation runs to completion "
                "and satisfies every acceptance criterion on the monitored signals."
            ).strip(),
            judgement_policy="acceptance_criteria_from_requirement",
            derivation_basis={
                "source_root": str(case_source_dir.relative_to(dataset_root)),
                "acceptance_criteria_count": len(case_payload["requirement"]["acceptance_criteria"]),
                "signals_of_interest": ordered_unique_text(case_payload["requirement"]["signals_of_interest"]),
            },
            verification_status="pending_execution",
            verification_conclusion="unknown",
            verification_summary=(
                "Ground-truth FMU execution has not been normalized into the dataset yet; "
                "the conclusion will be filled after executor-backed replay is added."
            ),
            missing_requirements=("ground_truth_execution_trace", "objective_pass_fail_conclusion"),
            trajectory_source_kind="none",
            trajectory_signal_columns=[item.get("name") for item in monitored_outputs],
            criteria=case_payload["requirement"]["acceptance_criteria"],
            decision_rule={
                "kind": "acceptance_criteria",
                "criteria_source": "verification_requirement.criteria",
                "requires_ground_truth": True,
            },
            tolerances={},
            signal_aliases={
                str(item.get("name") or ""): [str(item.get("name") or ""), str(item.get("source") or "")]
                for item in monitored_outputs
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            },
        )
        write_json(case_dir / "case.json", case_payload)
        case_rows.append(case_payload)

    return {"assets": len(asset_rows), "cases": len(case_rows)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.migrate_cases_to_dataset")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    args = parser.parse_args()
    result = migrate(dataset_root=Path(args.dataset_root).resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
