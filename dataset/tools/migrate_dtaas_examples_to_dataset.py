"""Normalize DTaaS multi-FMU orchestration examples into the unified dataset."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

from dataset.common import (
    ensure_symlink,
    parse_fmu_metadata,
    parse_sysml_model,
    read_json,
    resolve_fmu_signal_name,
    slugify,
    summarize_requirement_payload,
    write_json,
    write_text,
)
from dataset.tools.evaluation_artifacts import ordered_unique_text, write_case_evaluation_artifacts


WORKSPACE_PREFIX = "/workspace/examples/"


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    config_relpath: str
    time_relpath: Optional[str] = None
    case_raw_relpaths: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratedFmuSpec:
    workspace_relpath: str
    builder: str
    input_relpath: Optional[str] = None
    observables_relpath: Optional[str] = None
    template_fmu_relpath: Optional[str] = None
    model_description_relpath: Optional[str] = None
    config_relpath: Optional[str] = None


@dataclass(frozen=True)
class CaseSpec:
    slug: str
    title: str
    description: str
    expected_behavior: str
    source_relpath: str
    stages: Tuple[StageSpec, ...]
    generated_fmus: Tuple[GeneratedFmuSpec, ...] = ()
    extra_raw_relpaths: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()
    runtime_summary: str = ""


@dataclass
class InstanceRecord:
    alias: str
    instance_name: str
    asset_id: str
    fmu_path: Path
    raw_workspace_path: str
    metadata: Dict[str, Any]
    base_model_name: str
    description: str
    generated: bool = False


DTAAS_CASE_SPECS: Tuple[CaseSpec, ...] = (
    CaseSpec(
        slug="drobotti_rmqfmu",
        title="Desktop Robotti with RabbitMQ",
        description="RabbitMQ-backed co-simulation between a communication FMU and a distance-computation FMU.",
        expected_behavior="The RabbitMQ FMU receives playback robot coordinates and forwards the computed distance back to the consumer during fixed-step co-simulation.",
        source_relpath="digital_twins/drobotti_rmqfmu",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="multimodel.json",
                time_relpath="coe.json",
                case_raw_relpaths=("multimodel.json", "coe.json", "rabbitMQ-credentials.json"),
            ),
        ),
        extra_raw_relpaths=(
            "data/drobotti_rmqfmu/consume.py",
            "data/drobotti_rmqfmu/drobotti_playback_data.csv",
            "data/drobotti_rmqfmu/get_credentials.py",
            "data/drobotti_rmqfmu/rmq-publisher.py",
        ),
        tags=("rabbitmq", "runtime_io"),
        runtime_summary="RabbitMQ publisher and consumer scripts emulate the physical twin around the co-simulation.",
    ),
    CaseSpec(
        slug="flex_cell",
        title="Flex Cell Digital Twin with Two Industrial Robots",
        description="TwinManager-driven co-simulation that couples UR5e and Kuka robot FMUs with a RabbitMQ FMU.",
        expected_behavior="The RabbitMQ FMU injects target Cartesian positions and motion durations for both robot FMUs, and the logged robot states track those commands over fixed-step co-simulation.",
        source_relpath="digital_twins/flex-cell",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="multimodel_with_rmq.json",
                case_raw_relpaths=(
                    "multimodel.json",
                    "multimodel_with_rmq.json",
                    "kuka_actual.conf",
                    "kuka_experimental.conf",
                    "ur5e_actual.conf",
                    "ur5e_experimental.conf",
                ),
            ),
        ),
        generated_fmus=(
            GeneratedFmuSpec(
                workspace_relpath="models/flex-cell/rmqfmu_flexcell.fmu",
                builder="flexcell_rmq",
                template_fmu_relpath="models/rmqfmu-vhost.fmu",
                model_description_relpath="models/flex-cell/modelDescription.xml",
                config_relpath="data/flex-cell/input/connections.conf",
            ),
        ),
        extra_raw_relpaths=(
            "data/flex-cell/input/connections.conf",
            "data/flex-cell/input/publisher-flexcell-physical.py",
            "data/flex-cell/input/ur5e_mqtt_publisher.py",
            "data/flex-cell/input/physical_twin/kukalbriiwa7_actual.csv",
            "data/flex-cell/input/physical_twin/ur5e_actual.csv",
        ),
        tags=("rabbitmq", "mqtt", "runtime_io", "generated_fmu"),
        runtime_summary="A RabbitMQ/MQTT bridge script injects robot targets and mirrors physical-twin telemetry into the co-simulation.",
    ),
    CaseSpec(
        slug="mass_spring_damper",
        title="Mass Spring Damper",
        description="Two coupled mass-spring-damper FMUs composed through a fixed-step co-simulation.",
        expected_behavior="The coupled FMUs exchange displacement, velocity, and force so the two-mass system evolves coherently under the configured fixed-step schedule.",
        source_relpath="digital_twins/mass-spring-damper",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="cosim.json",
                time_relpath="time.json",
                case_raw_relpaths=("cosim.json", "time.json"),
            ),
        ),
        tags=("maestro",),
    ),
    CaseSpec(
        slug="mass_spring_damper_monitor",
        title="Mass Spring Damper with Monitor",
        description="Mass-spring-damper co-simulation extended with generated monitor FMU and two RtI instances.",
        expected_behavior="The monitor observes the displacement relationship between the two masses through RtI helper FMUs and remains non-violating for the bundled scenario.",
        source_relpath="digital_twins/mass-spring-damper-monitor",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="cosim.json",
                time_relpath="time.json",
                case_raw_relpaths=("cosim.json", "time.json", "model/m2.smv", "model/observables_m2.list"),
            ),
        ),
        generated_fmus=(
            GeneratedFmuSpec(
                workspace_relpath="models/m2.fmu",
                builder="nurv_monitor",
                input_relpath="digital_twins/mass-spring-damper-monitor/model/m2.smv",
                observables_relpath="digital_twins/mass-spring-damper-monitor/model/observables_m2.list",
            ),
        ),
        tags=("monitor", "generated_fmu"),
    ),
    CaseSpec(
        slug="three_tank",
        title="Three-Tank System Digital Twin",
        description="Cascade of three tank instances built from the same FMU and orchestrated through Maestro/TwinManager.",
        expected_behavior="The three tank instances propagate flow from tank1 to tank3 while logging level, in/out flow, leak, and derivative signals over the configured time window.",
        source_relpath="digital_twins/three-tank",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="multimodel.json",
                time_relpath="coe.json",
                case_raw_relpaths=("multimodel.json", "coe.json", "tank1.conf", "tank2.conf", "tank3.conf"),
            ),
        ),
        tags=("multi_instance", "twin_manager"),
    ),
    CaseSpec(
        slug="water_tank_fi",
        title="Water Tank Fault Injection",
        description="Water-tank controller and plant co-simulation with Maestro fault injection extension.",
        expected_behavior="Fault injection tampers with controller output during the configured interval, causing the tank level to rise beyond the nominal operating band.",
        source_relpath="digital_twins/water_tank_FI",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="multimodelFI.json",
                time_relpath="simulation-config.json",
                case_raw_relpaths=("multimodelFI.json", "simulation-config.json"),
            ),
        ),
        extra_raw_relpaths=(
            "common/tools/FaultInject.mabl",
            "data/water_tank_FI/input/wt_fault.xml",
        ),
        tags=("fault_injection",),
    ),
    CaseSpec(
        slug="water_tank_fi_monitor",
        title="Water Tank Fault Injection with Monitor",
        description="Water-tank fault-injection example extended with a generated monitor FMU and RtI helper.",
        expected_behavior="The injected controller fault drives the tank level beyond the monitor threshold and the generated monitor verdict transitions to violation for the bundled scenario.",
        source_relpath="digital_twins/water_tank_FI_monitor",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="multimodelFI.json",
                time_relpath="simulation-config.json",
                case_raw_relpaths=("multimodelFI.json", "simulation-config.json", "wt_fault.xml", "model/m1.smv", "model/observables_m1.list"),
            ),
        ),
        generated_fmus=(
            GeneratedFmuSpec(
                workspace_relpath="models/m1.fmu",
                builder="nurv_monitor",
                input_relpath="digital_twins/water_tank_FI_monitor/model/m1.smv",
                observables_relpath="digital_twins/water_tank_FI_monitor/model/observables_m1.list",
            ),
        ),
        extra_raw_relpaths=("common/tools/FaultInject.mabl",),
        tags=("fault_injection", "monitor", "generated_fmu"),
    ),
    CaseSpec(
        slug="water_tank_swap",
        title="Water Tank Model Swap",
        description="Two-stage water-tank scenario with fault injection followed by dynamic controller swap.",
        expected_behavior="Stage 1 executes the nominal water-tank co-simulation with injected faults, and stage 2 introduces leak detection plus runtime swap to the leak controller when the swap condition is satisfied.",
        source_relpath="digital_twins/water_tank_swap",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="mm1.json",
                time_relpath="simulation-config.json",
                case_raw_relpaths=("mm1.json", "simulation-config.json", "wt_fault.xml", "FaultInject.mabl"),
            ),
            StageSpec(
                stage_id="stage2",
                config_relpath="mm2.json",
                time_relpath="simulation-config.json",
                case_raw_relpaths=("mm2.json", "simulation-config.json"),
            ),
        ),
        tags=("fault_injection", "model_swap", "multi_stage"),
    ),
    CaseSpec(
        slug="incubator_nurv_monitor_validation",
        title="Incubator Digital Twin Validation with NuRV Monitor",
        description="Monitor-validation co-simulation for incubator anomaly detection and energy saver behavior.",
        expected_behavior="Source, anomaly-detection, energy-saver, watcher, and generated monitor FMUs execute together so that the monitor validates timely energy-saving activation after anomaly detection.",
        source_relpath="digital_twins/incubator-NuRV-monitor-validation",
        stages=(
            StageSpec(
                stage_id="stage1",
                config_relpath="cosim.json",
                time_relpath="time.json",
                case_raw_relpaths=("cosim.json", "time.json", "model/safe-operation.smv"),
            ),
        ),
        generated_fmus=(
            GeneratedFmuSpec(
                workspace_relpath="models/safe-operation.fmu",
                builder="nurv_monitor",
                input_relpath="digital_twins/incubator-NuRV-monitor-validation/model/safe-operation.smv",
            ),
        ),
        tags=("monitor", "generated_fmu"),
    ),
)


def _ordered_unique(items: Iterable[Any]) -> List[Any]:
    ordered = OrderedDict()
    for item in items:
        key = repr(item) if isinstance(item, (dict, list, tuple)) else item
        if key not in ordered:
            ordered[key] = item
    return list(ordered.values())


def _clean_alias(alias: str) -> str:
    text = str(alias or "").strip()
    if text.startswith("{") and text.endswith("}"):
        return text[1:-1]
    return text


def _workspace_relpath(text: str) -> str:
    value = str(text or "").strip()
    if value.startswith("file://"):
        value = value[len("file://") :]
    if value.startswith(WORKSPACE_PREFIX):
        return value[len(WORKSPACE_PREFIX) :]
    return value.lstrip("/")


def _resolve_workspace_path(raw: str, *, examples_root: Path, generated_paths: Mapping[str, Path]) -> Path:
    relpath = _workspace_relpath(raw)
    if relpath in generated_paths:
        return generated_paths[relpath]
    resolved = (examples_root / relpath).resolve()
    if not resolved.exists() and relpath in generated_paths:
        return generated_paths[relpath]
    return resolved


def _classify_backend_kind(*, fmu_path: Path, metadata: Mapping[str, Any]) -> str:
    if bool((metadata.get("capabilities") or {}).get("needs_execution_tool")):
        return "rabbitmq_bridge_fmu"
    try:
        with zipfile.ZipFile(fmu_path) as archive:
            names = set(archive.namelist())
    except Exception:
        return "native_fmu"
    if "resources/model.py" in names:
        return "unifmu_python"
    if "sources/model.py" in names:
        return "python_source_fmu"
    return "native_fmu"


def _parse_simple_hocon(path: Path) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    stack: List[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.endswith("{"):
            name = line[:-1].rstrip(":").strip()
            if name:
                stack.append(name)
            continue
        if line == "}":
            if stack:
                stack.pop()
            continue
        if "=" not in line or not stack:
            continue
        key, value = line.split("=", 1)
        section = ".".join(stack)
        data.setdefault(section, {})[key.strip()] = value.strip().strip('"')
    return data


def _copy_tree_to_zip(src_dir: Path, dst_zip: Path) -> None:
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(src_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(src_dir))


def _build_flexcell_rmq_fmu(*, output_path: Path, template_fmu: Path, model_description: Path, config_path: Optional[Path]) -> None:
    with tempfile.TemporaryDirectory(prefix="flexcell_rmq_") as tmp_text:
        tmp_root = Path(tmp_text)
        with zipfile.ZipFile(template_fmu) as archive:
            archive.extractall(tmp_root)

        tree = ET.parse(model_description)
        if config_path is not None and config_path.exists():
            config = _parse_simple_hocon(config_path)
            rabbit = config.get("rabbitmq", {})
            for variable in tree.getroot().findall("./ModelVariables/ScalarVariable"):
                name = str(variable.attrib.get("name") or "")
                scalar = next(iter(variable), None)
                if scalar is None:
                    continue
                if name == "config.hostname" and rabbit.get("hostname"):
                    scalar.attrib["start"] = rabbit["hostname"]
                elif name == "config.port" and rabbit.get("port"):
                    scalar.attrib["start"] = rabbit["port"]
                elif name == "config.username" and rabbit.get("username"):
                    scalar.attrib["start"] = rabbit["username"]
                elif name == "config.password" and rabbit.get("password"):
                    scalar.attrib["start"] = rabbit["password"]
                elif name == "config.vhost" and rabbit.get("vhost"):
                    scalar.attrib["start"] = rabbit["vhost"]

        tree.write(tmp_root / "modelDescription.xml", encoding="utf-8", xml_declaration=True)
        resources_dir = tmp_root / "resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        tree.write(resources_dir / "modelDescription.xml", encoding="utf-8", xml_declaration=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _copy_tree_to_zip(tmp_root, output_path)


def _build_nurv_monitor_fmu(
    *,
    output_path: Path,
    nurv_bin: Path,
    fmi_headers: Path,
    smv_path: Path,
    output_name: str,
    observables_path: Optional[Path],
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"{output_name}_nurv_") as tmp_text:
        tmp_root = Path(tmp_text)
        command_lines = [f'set input_file "{smv_path}"', "go"]
        if observables_path is not None:
            command_lines.append(f'build_monitor -n 0 -C "{observables_path}"')
        else:
            command_lines.append("build_monitor -n 0")
        command_lines.extend([f'generate_monitor -n 0 -l 3 -L "FMU" -o "{output_name}"', "quit"])
        command_path = tmp_root / "synth.cmd"
        write_text(command_path, "\n".join(command_lines))
        subprocess.run([str(nurv_bin), "-quiet", "-source", str(command_path)], cwd=tmp_root, check=True)

        generated_dir = tmp_root / output_name
        model_description = generated_dir / "modelDescription.xml"
        text = model_description.read_text(encoding="utf-8")
        text = text.replace('Enumeration declaredType="eu.fbk.nurv.RV_value"', "Integer")
        model_description.write_text(text, encoding="utf-8")

        env = dict(os.environ, FMI2_HOME=str(fmi_headers))
        subprocess.run(["make", "-C", str(generated_dir), "linux64"], cwd=tmp_root, env=env, check=True)
        built_fmu = tmp_root / f"{output_name}.fmu"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_fmu, output_path)


def _materialize_generated_fmus(*, case_spec: CaseSpec, source_dir: Path, examples_root: Path) -> Dict[str, Path]:
    generated_root = source_dir / "generated_fmus"
    generated_root.mkdir(parents=True, exist_ok=True)
    generated_paths: Dict[str, Path] = {}

    if not case_spec.generated_fmus:
        return generated_paths

    nurv_bin = examples_root / "common/tools/NuRV/NuRV"
    fmi_headers = examples_root / "common/fmi2_headers"
    if any(spec.builder == "nurv_monitor" for spec in case_spec.generated_fmus):
        if not nurv_bin.exists():
            raise FileNotFoundError(f"Missing NuRV binary: {nurv_bin}")
        if not fmi_headers.exists():
            raise FileNotFoundError(f"Missing FMI2 headers: {fmi_headers}")

    for spec in case_spec.generated_fmus:
        output_path = generated_root / Path(spec.workspace_relpath).name
        if not output_path.exists():
            if spec.builder == "nurv_monitor":
                if spec.input_relpath is None:
                    raise ValueError(f"Generated monitor {spec.workspace_relpath} is missing input_relpath")
                _build_nurv_monitor_fmu(
                    output_path=output_path,
                    nurv_bin=nurv_bin,
                    fmi_headers=fmi_headers,
                    smv_path=examples_root / spec.input_relpath,
                    output_name=Path(spec.workspace_relpath).stem,
                    observables_path=(examples_root / spec.observables_relpath) if spec.observables_relpath else None,
                )
            elif spec.builder == "flexcell_rmq":
                if spec.template_fmu_relpath is None or spec.model_description_relpath is None:
                    raise ValueError(f"Generated FMU {spec.workspace_relpath} is missing template/model_description")
                _build_flexcell_rmq_fmu(
                    output_path=output_path,
                    template_fmu=examples_root / spec.template_fmu_relpath,
                    model_description=examples_root / spec.model_description_relpath,
                    config_path=(examples_root / spec.config_relpath) if spec.config_relpath else None,
                )
            else:
                raise ValueError(f"Unsupported generated FMU builder: {spec.builder}")
        generated_paths[spec.workspace_relpath] = output_path.resolve()
    return generated_paths


def _iter_stage_refs(payload: Mapping[str, Any]) -> Iterable[str]:
    connections = payload.get("connections")
    if isinstance(connections, dict):
        for source, targets in connections.items():
            if isinstance(source, str):
                yield source
            if isinstance(targets, list):
                for target in targets:
                    if isinstance(target, str):
                        yield target

    log_vars = payload.get("logVariables")
    if isinstance(log_vars, dict):
        for source in log_vars.keys():
            if isinstance(source, str):
                yield source

    parameters = payload.get("parameters")
    if isinstance(parameters, dict):
        for target in parameters.keys():
            if isinstance(target, str):
                yield target

    model_swaps = payload.get("modelSwaps")
    if isinstance(model_swaps, dict):
        for entry in model_swaps.values():
            if not isinstance(entry, dict):
                continue
            swap_connections = entry.get("swapConnections")
            if not isinstance(swap_connections, dict):
                continue
            for source, targets in swap_connections.items():
                if isinstance(source, str):
                    yield source
                if isinstance(targets, list):
                    for target in targets:
                        if isinstance(target, str):
                            yield target


def _split_endpoint(reference: str) -> Tuple[str, str]:
    text = str(reference or "").strip()
    if not text or "." not in text:
        raise ValueError(f"Unsupported endpoint reference: {reference}")
    alias, remainder = text.split(".", 1)
    return alias, remainder


def _endpoint_namespace(reference: str) -> str:
    _, remainder = _split_endpoint(reference)
    return remainder.split(".", 1)[0]


def _alias_modes(stage_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, bool]:
    namespaces: Dict[str, set[str]] = {}
    for payload in stage_payloads:
        for reference in _iter_stage_refs(payload):
            try:
                alias, _ = _split_endpoint(reference)
            except ValueError:
                continue
            namespaces.setdefault(alias, set()).add(_endpoint_namespace(reference))
    return {alias: len(values) > 1 for alias, values in namespaces.items()}


def _description_for_instance(*, instance_name: str, base_model_name: str, base_description: str, case_title: str) -> str:
    if base_description:
        return f"{instance_name} instance of {base_model_name} in {case_title}. {base_description}".strip()
    return f"{instance_name} instance of {base_model_name} in {case_title}."


def _initial_stage_schedule(stage_payload: Mapping[str, Any], time_payload: Mapping[str, Any]) -> Dict[str, Any]:
    algorithm = stage_payload.get("algorithm") if isinstance(stage_payload.get("algorithm"), dict) else {}
    schedule = {
        "kind": "co_simulation",
        "co_simulation_type": str(algorithm.get("type") or "fixed_step"),
    }
    if algorithm.get("size") is not None:
        schedule["step_size"] = algorithm.get("size")
    if time_payload.get("startTime") is not None:
        schedule["start_time"] = time_payload.get("startTime")
    if time_payload.get("endTime") is not None:
        schedule["stop_time"] = time_payload.get("endTime")
    if time_payload.get("reportProgress") is not None:
        schedule["report_progress"] = time_payload.get("reportProgress")
    if time_payload.get("liveLogInterval") is not None:
        schedule["live_log_interval"] = time_payload.get("liveLogInterval")
    return schedule


def _ensure_raw_links(*, source_dir: Path, examples_root: Path, relpaths: Sequence[str]) -> List[str]:
    written: List[str] = []
    for relpath in relpaths:
        src = examples_root / relpath
        if not src.exists():
            continue
        dst = source_dir / "raw" / relpath
        ensure_symlink(src.resolve(), dst)
        written.append(str(dst.relative_to(source_dir)))
    return written


def _build_case_relpaths(case_spec: CaseSpec) -> List[str]:
    relpaths = [f"{case_spec.source_relpath}/README.md"]
    for stage in case_spec.stages:
        relpaths.extend(f"{case_spec.source_relpath}/{item}" for item in stage.case_raw_relpaths)
    relpaths.extend(case_spec.extra_raw_relpaths)
    return _ordered_unique(relpaths)


def _normalize_endpoint(
    *,
    reference: str,
    alias_multi_instance: Mapping[str, bool],
    instances: Mapping[Tuple[str, str], InstanceRecord],
) -> Tuple[InstanceRecord, str]:
    alias, remainder = _split_endpoint(reference)
    parts = remainder.split(".")
    if alias_multi_instance.get(alias, False):
        instance_name = parts[0]
        signal_ref = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
    else:
        instance_name = _clean_alias(alias)
        signal_ref = ".".join(parts[1:]) if len(parts) > 1 else parts[0]

    record = instances[(alias, instance_name)]
    signal = resolve_fmu_signal_name(signal_ref, [port["name"] for port in record.metadata["ports"]])
    return record, signal


def _generate_sysml(*, package_name: str, system_name: str, instances: Sequence[InstanceRecord], connections: Sequence[Dict[str, str]]) -> str:
    type_to_ports: Dict[str, List[Dict[str, Any]]] = OrderedDict()
    for instance in instances:
        type_to_ports.setdefault(instance.base_model_name, instance.metadata["ports"])

    lines: List[str] = [f"package {package_name} {{"]
    for component_type, ports in type_to_ports.items():
        lines.append(f"  part def {slugify(component_type).title().replace('_', '')} {{")
        seen: set[str] = set()
        for port in ports:
            name = str(port.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            direction = str(port.get("causality") or "local")
            if direction == "input":
                lines.append(f"    in {slugify(name)} : {port.get('type') or 'Real'};")
            elif direction == "output":
                lines.append(f"    out {slugify(name)} : {port.get('type') or 'Real'};")
        lines.append("  }")

    type_names = {instance.base_model_name: slugify(instance.base_model_name).title().replace("_", "") for instance in instances}
    lines.append(f"  part def {system_name} {{")
    for instance in instances:
        lines.append(f"    part {slugify(instance.instance_name)} : {type_names[instance.base_model_name]};")
    for connection in connections:
        src_asset = connection["source"].split(".", 1)[0]
        dst_asset = connection["target"].split(".", 1)[0]
        src_signal = slugify(connection["source"].rsplit(".", 1)[-1])
        dst_signal = slugify(connection["target"].rsplit(".", 1)[-1])
        src_name = slugify(src_asset.rsplit("__", 1)[-1])
        dst_name = slugify(dst_asset.rsplit("__", 1)[-1])
        lines.append(f"    connect {src_name}.{src_signal} to {dst_name}.{dst_signal};")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def _runtime_extension(*, case_spec: CaseSpec, raw_relpaths: Sequence[str]) -> Dict[str, Any]:
    if not case_spec.runtime_summary and not case_spec.extra_raw_relpaths:
        return {}
    runtime_relpaths = [path for path in raw_relpaths if "/data/" in f"/{path}" or "connections.conf" in path or "credentials" in path]
    return {
        "summary": case_spec.runtime_summary,
        "raw_relpaths": runtime_relpaths,
    }


def _output_monitors_for_assets(
    *,
    instances: Sequence[InstanceRecord],
    selected_asset_ids: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    selected = {str(item) for item in selected_asset_ids if str(item)}
    monitored: List[Dict[str, Any]] = []
    for record in instances:
        if selected and record.asset_id not in selected:
            continue
        for port in record.metadata.get("ports", []) if isinstance(record.metadata.get("ports"), list) else []:
            if not isinstance(port, dict) or str(port.get("causality") or "") != "output":
                continue
            signal = str(port.get("name") or "").strip()
            if not signal:
                continue
            monitored.append({"name": signal, "source": f"{record.asset_id}.{signal}"})
    return _ordered_unique(monitored)


def _single_runtime_csv_input_source(*, source_dir: Path, solution_payload: Mapping[str, Any]) -> Path | None:
    extensions = solution_payload.get("extensions") if isinstance(solution_payload.get("extensions"), dict) else {}
    runtime_io = extensions.get("runtime_io") if isinstance(extensions.get("runtime_io"), dict) else {}
    raw_relpaths = runtime_io.get("raw_relpaths") if isinstance(runtime_io.get("raw_relpaths"), list) else []
    csv_paths = [
        source_dir / str(relpath)
        for relpath in raw_relpaths
        if str(relpath).strip().lower().endswith(".csv") and (source_dir / str(relpath)).exists()
    ]
    return csv_paths[0] if len(csv_paths) == 1 else None


def _normalize_stage(
    *,
    case_spec: CaseSpec,
    stage_spec: StageSpec,
    stage_payload: Mapping[str, Any],
    time_payload: Mapping[str, Any],
    alias_multi_instance: Mapping[str, bool],
    instances: Mapping[Tuple[str, str], InstanceRecord],
    source_dir: Path,
    examples_root: Path,
) -> Dict[str, Any]:
    selected_asset_ids: List[str] = []
    fmus = stage_payload.get("fmus") if isinstance(stage_payload.get("fmus"), dict) else {}
    for alias in fmus.keys():
        if alias_multi_instance.get(alias, False):
            asset_ids = [record.asset_id for (key_alias, _), record in instances.items() if key_alias == alias]
            selected_asset_ids.extend(sorted(asset_ids))
        else:
            record = instances[(alias, _clean_alias(alias))]
            selected_asset_ids.append(record.asset_id)
    selected_asset_ids = _ordered_unique(selected_asset_ids)

    connections: List[Dict[str, Any]] = []
    raw_connections = stage_payload.get("connections") if isinstance(stage_payload.get("connections"), dict) else {}
    for source_ref, targets in raw_connections.items():
        if not isinstance(source_ref, str) or not isinstance(targets, list):
            continue
        source_record, source_signal = _normalize_endpoint(reference=source_ref, alias_multi_instance=alias_multi_instance, instances=instances)
        for target_ref in targets:
            if not isinstance(target_ref, str):
                continue
            target_record, target_signal = _normalize_endpoint(reference=target_ref, alias_multi_instance=alias_multi_instance, instances=instances)
            connections.append(
                {
                    "source": f"{source_record.asset_id}.{source_signal}",
                    "target": f"{target_record.asset_id}.{target_signal}",
                }
            )

    monitored_outputs: List[Dict[str, Any]] = []
    log_variables = stage_payload.get("logVariables") if isinstance(stage_payload.get("logVariables"), dict) else {}
    for source_ref, signals in log_variables.items():
        if not isinstance(source_ref, str) or not isinstance(signals, list):
            continue
        record, _ = _normalize_endpoint(reference=source_ref, alias_multi_instance=alias_multi_instance, instances=instances)
        for raw_signal in signals:
            if not isinstance(raw_signal, str):
                continue
            signal = resolve_fmu_signal_name(raw_signal, [port["name"] for port in record.metadata["ports"]])
            monitored_outputs.append({"name": signal, "source": f"{record.asset_id}.{signal}"})

    parameter_overrides: List[Dict[str, Any]] = []
    parameters = stage_payload.get("parameters") if isinstance(stage_payload.get("parameters"), dict) else {}
    for target_ref, value in parameters.items():
        if not isinstance(target_ref, str):
            continue
        record, signal = _normalize_endpoint(reference=target_ref, alias_multi_instance=alias_multi_instance, instances=instances)
        parameter_overrides.append({"target": f"{record.asset_id}.{signal}", "value": value})

    model_swap_extension: Dict[str, Any] = {}
    swap_connections_for_union: List[Dict[str, Any]] = []
    model_swaps = stage_payload.get("modelSwaps") if isinstance(stage_payload.get("modelSwaps"), dict) else {}
    if model_swaps:
        normalized_swaps: List[Dict[str, Any]] = []
        for swap_name, entry in model_swaps.items():
            if not isinstance(entry, dict):
                continue
            normalized_connections: List[Dict[str, Any]] = []
            swap_connections = entry.get("swapConnections") if isinstance(entry.get("swapConnections"), dict) else {}
            for source_ref, targets in swap_connections.items():
                if not isinstance(source_ref, str) or not isinstance(targets, list):
                    continue
                source_record, source_signal = _normalize_endpoint(reference=source_ref, alias_multi_instance=alias_multi_instance, instances=instances)
                for target_ref in targets:
                    if not isinstance(target_ref, str):
                        continue
                    target_record, target_signal = _normalize_endpoint(reference=target_ref, alias_multi_instance=alias_multi_instance, instances=instances)
                    payload = {
                        "source": f"{source_record.asset_id}.{source_signal}",
                        "target": f"{target_record.asset_id}.{target_signal}",
                    }
                    normalized_connections.append(payload)
                    swap_connections_for_union.append(payload)
            normalized_swaps.append(
                {
                    "swap_id": swap_name,
                    "swap_instance": entry.get("swapInstance"),
                    "step_condition": entry.get("stepCondition"),
                    "swap_condition": entry.get("swapCondition"),
                    "connections": normalized_connections,
                }
            )
        model_swap_extension = {
            "swaps": normalized_swaps,
            "model_transfers": stage_payload.get("modelTransfers", {}),
        }

    fault_config_relpath = None
    fault_config = stage_payload.get("faultInjectConfigurationPath")
    if isinstance(fault_config, str):
        relpath = _workspace_relpath(fault_config)
        if not fault_config.startswith(WORKSPACE_PREFIX) and not fault_config.startswith("file://") and not fault_config.startswith("/"):
            relpath = f"{case_spec.source_relpath}/{fault_config}"
        raw_relpath = source_dir / "raw" / relpath
        if raw_relpath.exists() or raw_relpath.is_symlink():
            fault_config_relpath = str(raw_relpath.relative_to(source_dir))

    schedule = _initial_stage_schedule(stage_payload, time_payload)
    stage_raw_relpaths = [
        str((source_dir / "raw" / f"{case_spec.source_relpath}/{item}").relative_to(source_dir))
        for item in stage_spec.case_raw_relpaths
        if (source_dir / "raw" / f"{case_spec.source_relpath}/{item}").exists()
        or (source_dir / "raw" / f"{case_spec.source_relpath}/{item}").is_symlink()
    ]

    extensions: Dict[str, Any] = {
        "parameter_overrides": parameter_overrides,
        "raw_config_relpaths": stage_raw_relpaths,
    }
    if fault_config_relpath or stage_payload.get("faultInjectInstances") is not None:
        extensions["fault_injection"] = {
            "configuration_relpath": fault_config_relpath,
            "instances": stage_payload.get("faultInjectInstances", {}),
        }
    if model_swap_extension:
        extensions["model_swap"] = model_swap_extension
    if stage_payload.get("aliases") is not None:
        extensions["aliases"] = stage_payload.get("aliases")

    return {
        "stage_id": stage_spec.stage_id,
        "selected_asset_ids": selected_asset_ids,
        "connections": _ordered_unique(connections),
        "external_inputs": [],
        "monitored_outputs": _ordered_unique(monitored_outputs),
        "execution_order": list(selected_asset_ids),
        "schedule": schedule,
        "extensions": extensions,
        "_union_swap_connections": swap_connections_for_union,
    }


def _write_source_case(
    *,
    case_spec: CaseSpec,
    source_dir: Path,
    examples_root: Path,
    instances: Sequence[InstanceRecord],
    requirement_payload: Dict[str, Any],
    orchestration_payload: Dict[str, Any],
    ground_truth_payload: Dict[str, Any],
    sysml_text: str,
) -> None:
    fmus_dir = source_dir / "fmus"
    specs_dir = source_dir / "fmu_specs"
    shutil.rmtree(fmus_dir, ignore_errors=True)
    shutil.rmtree(specs_dir, ignore_errors=True)
    fmus_dir.mkdir(parents=True, exist_ok=True)
    specs_dir.mkdir(parents=True, exist_ok=True)

    for record in instances:
        ensure_symlink(record.fmu_path.resolve(), fmus_dir / f"{record.instance_name}.fmu")
        spec_payload = {
            **record.metadata,
            "name": record.instance_name,
            "description": record.description,
            "base_model_name": record.base_model_name,
            "generated": record.generated,
            "provenance": {
                "workspace_path": record.raw_workspace_path,
                "examples_root": str(examples_root),
            },
        }
        write_json(specs_dir / f"fmu_{record.instance_name}.json", spec_payload)
        write_text(specs_dir / f"fmu_{record.instance_name}.md", record.description)

    fmu_list_payload = {
        "case_id": f"case_dtaas_{case_spec.slug}",
        "case_name": case_spec.title,
        "description": case_spec.description,
        "fmu_count": len(instances),
        "fmus": [
            {
                "name": record.instance_name,
                "path": f"fmus/{record.instance_name}.fmu",
                "description": record.description,
                "type": ",".join(record.metadata["fmi_types"]) or "Co-Simulation",
                "fmi_version": record.metadata["fmi_version"],
                "generated": record.generated,
                "base_model_name": record.base_model_name,
                "inputs": [
                    {
                        "name": port["name"],
                        "unit": port.get("unit", ""),
                        "description": port.get("description", ""),
                    }
                    for port in record.metadata["ports"]
                    if port["causality"] == "input"
                ],
                "outputs": [
                    {
                        "name": port["name"],
                        "unit": port.get("unit", ""),
                        "description": port.get("description", ""),
                    }
                    for port in record.metadata["ports"]
                    if port["causality"] == "output"
                ],
                "parameters": [
                    {
                        "name": port["name"],
                        "unit": port.get("unit", ""),
                        "description": port.get("description", ""),
                    }
                    for port in record.metadata["ports"]
                    if port["causality"] == "parameter"
                ],
            }
            for record in instances
        ],
    }

    write_json(source_dir / "requirement.json", requirement_payload)
    write_json(source_dir / "fmu_list.json", fmu_list_payload)
    write_json(source_dir / "orchestration.json", orchestration_payload)
    write_json(source_dir / "ground_truth.json", ground_truth_payload)
    write_text(source_dir / "system.sysml", sysml_text)

    log_lines = [
        f"# case_dtaas_{case_spec.slug}",
        "",
        f"Original example: `{case_spec.source_relpath}`",
        f"Title: {case_spec.title}",
        "",
        "Generated FMUs:"
    ]
    generated_instances = [record.instance_name for record in instances if record.generated]
    if generated_instances:
        log_lines.extend(f"- {name}" for name in generated_instances)
    else:
        log_lines.append("- none")
    log_lines.extend(
        [
            "",
            "Stages:",
            *[f"- {stage['stage_id']}: {', '.join(stage['selected_asset_ids'])}" for stage in orchestration_payload.get("stages", [])],
            "",
            f"Expected behavior: {case_spec.expected_behavior}",
        ]
    )
    write_text(source_dir / "LOG.md", "\n".join(log_lines))


def _normalize_case(
    *,
    case_spec: CaseSpec,
    dataset_root: Path,
    source_dir: Path,
    instances: Sequence[InstanceRecord],
    requirement_payload: Dict[str, Any],
    orchestration_payload: Dict[str, Any],
    ground_truth_payload: Dict[str, Any],
    sysml_text: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    assets_root = dataset_root / "assets"
    cases_root = dataset_root / "cases"
    case_id = f"case_dtaas_{case_spec.slug}"
    source_root_rel = str(source_dir.relative_to(dataset_root))

    asset_payloads: List[Dict[str, Any]] = []
    first_schedule = orchestration_payload.get("schedule") if isinstance(orchestration_payload.get("schedule"), dict) else {}
    for record in instances:
        asset_dir = assets_root / record.asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        ensure_symlink((source_dir / "fmus" / f"{record.instance_name}.fmu").resolve(), asset_dir / "model.fmu")
        metadata = dict(record.metadata)
        metadata["asset_id"] = record.asset_id
        metadata["name"] = record.instance_name
        metadata["description"] = record.description
        metadata["backend_kind"] = str(metadata.get("backend_kind") or _classify_backend_kind(fmu_path=record.fmu_path, metadata=metadata))
        if not metadata.get("default_experiment") and first_schedule:
            metadata["default_experiment"] = {
                "startTime": first_schedule.get("start_time", 0.0),
                "stopTime": first_schedule.get("stop_time", 1.0),
                "stepSize": first_schedule.get("step_size", 0.01),
            }
        write_json(asset_dir / "metadata.json", metadata)
        write_text(asset_dir / "description.md", record.description)

        tags = [case_spec.slug, *case_spec.tags]
        if record.generated:
            tags.append("generated_fmu")
        asset_payload = {
            "schema": "UNIFIED_ASSET_V1",
            "asset_id": record.asset_id,
            "source_type": "dtaas_example_fmu",
            "source_id": f"{case_id}::{record.instance_name}",
            "name": record.instance_name,
            "description": record.description,
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
            "tags": _ordered_unique(tags),
            "library_visible": True,
            "ground_truth_only": False,
            "case_origin": [case_id],
            "provenance": {
                "example_slug": case_spec.slug,
                "example_path": case_spec.source_relpath,
                "workspace_path": record.raw_workspace_path,
                "base_model_name": record.base_model_name,
                "generated": record.generated,
            },
        }
        write_json(asset_dir / "asset.json", asset_payload)
        asset_payloads.append(asset_payload)

    case_dir = cases_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    ensure_symlink((source_dir / "system.sysml").resolve(), case_dir / "system.sysml")
    ensure_symlink((source_dir / "LOG.md").resolve(), case_dir / "notes.md")

    normalized_solution = dict(orchestration_payload)
    normalized_stages: List[Dict[str, Any]] = []
    union_monitored: List[Dict[str, Any]] = []
    for stage in normalized_solution.get("stages", []) if isinstance(normalized_solution.get("stages"), list) else []:
        if not isinstance(stage, dict):
            continue
        stage_payload = dict(stage)
        stage_monitored = stage_payload.get("monitored_outputs") if isinstance(stage_payload.get("monitored_outputs"), list) else []
        if not stage_monitored:
            stage_payload["monitored_outputs"] = _output_monitors_for_assets(
                instances=instances,
                selected_asset_ids=stage_payload.get("selected_asset_ids") if isinstance(stage_payload.get("selected_asset_ids"), list) else [],
            )
        normalized_stages.append(stage_payload)
        union_monitored.extend(stage_payload.get("monitored_outputs", []))
    if normalized_stages:
        normalized_solution["stages"] = normalized_stages

    top_level_monitored = normalized_solution.get("monitored_outputs") if isinstance(normalized_solution.get("monitored_outputs"), list) else []
    if not top_level_monitored:
        normalized_solution["monitored_outputs"] = _ordered_unique(union_monitored) or _output_monitors_for_assets(instances=instances)

    normalized_requirement = dict(requirement_payload)
    if not isinstance(normalized_requirement.get("signals_of_interest"), list) or not normalized_requirement.get("signals_of_interest"):
        normalized_requirement["signals_of_interest"] = ordered_unique_text(
            item.get("name")
            for item in normalized_solution.get("monitored_outputs", [])
            if isinstance(item, dict)
        )

    write_json(case_dir / "solution.json", normalized_solution)

    mbse = parse_sysml_model(sysml_text, sysml_name="system.sysml")
    case_payload = {
        "schema": "UNIFIED_CASE_V1",
        "case_id": case_id,
        "source_type": "dtaas_multi_fmu_case",
        "title": case_spec.title,
        "description": case_spec.description,
        "requirement": {
            **normalized_requirement,
            "text": summarize_requirement_payload(normalized_requirement),
        },
        "mbse": {
            "sysml_relpath": "system.sysml",
            **mbse,
        },
        "ground_truth_asset_ids": [record.asset_id for record in instances],
        "candidate_asset_ids": [],
        "solution_relpath": "solution.json",
        "expected_behavior": case_spec.expected_behavior,
        "provenance": {
            "example_slug": case_spec.slug,
            "example_path": case_spec.source_relpath,
            "source_root": source_root_rel,
            "raw_config_relpaths": normalized_solution.get("extensions", {}).get("raw_config_relpaths", []),
        },
    }
    case_payload["evaluation_artifacts"] = write_case_evaluation_artifacts(
        case_dir=case_dir,
        case_payload=case_payload,
        solution_payload=normalized_solution,
        verification_title=f"{case_payload['title']} Verification Requirement",
        verification_text=(
            f"{case_payload['requirement']['text']} "
            f"Expected ground-truth behavior: {case_spec.expected_behavior} "
            "A final pass/fail conclusion remains pending until a reference execution trace is normalized."
        ).strip(),
        judgement_policy="behavioral_expectation_pending_execution",
        derivation_basis={
            "source_root": source_root_rel,
            "expected_behavior": case_spec.expected_behavior,
            "signals_of_interest": ordered_unique_text(case_payload["requirement"]["signals_of_interest"]),
        },
        verification_status="pending_execution",
        verification_conclusion="unknown",
        verification_summary=(
            "The DTaaS source case has orchestration truth but no normalized ground-truth execution trace yet; "
            "the conclusion will be populated after executor-backed replay is added."
        ),
        missing_requirements=("ground_truth_execution_trace", "objective_pass_fail_conclusion"),
        input_source=_single_runtime_csv_input_source(source_dir=source_dir, solution_payload=normalized_solution),
        trajectory_source_kind="none",
        trajectory_signal_columns=[
            item.get("name")
            for item in normalized_solution.get("monitored_outputs", [])
            if isinstance(item, dict)
        ],
        criteria=[
            {
                "metric": "trajectory_match",
                "operator": "<=",
                "value": None,
                "signals": ordered_unique_text(case_payload["requirement"]["signals_of_interest"]),
                "notes": "Requires canonical DTaaS reference execution trace.",
            }
        ],
        decision_rule={
            "kind": "trajectory_tolerance",
            "signals": ordered_unique_text(case_payload["requirement"]["signals_of_interest"]),
            "time_column": "time",
            "requires_ground_truth": True,
        },
        tolerances={},
        time_column="time",
        signal_aliases={
            str(item.get("name") or ""): [str(item.get("name") or ""), str(item.get("source") or "")]
            for item in normalized_solution.get("monitored_outputs", [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        },
    )
    write_json(case_dir / "case.json", case_payload)
    return asset_payloads, case_payload


def migrate(*, dataset_root: Path, examples_root: Optional[Path] = None) -> Dict[str, Any]:
    dataset_root = dataset_root.resolve()
    examples_root = (examples_root or dataset_root.parent / "DTaaS-examples-main").resolve()
    if not examples_root.exists():
        raise FileNotFoundError(f"DTaaS examples root not found: {examples_root}")

    source_root = dataset_root / "sources" / "dtaas_examples"
    source_root.mkdir(parents=True, exist_ok=True)

    asset_count = 0
    case_count = 0
    for case_spec in DTAAS_CASE_SPECS:
        source_dir = source_root / f"case_dtaas_{case_spec.slug}"
        shutil.rmtree(source_dir, ignore_errors=True)
        source_dir.mkdir(parents=True, exist_ok=True)

        generated_paths = _materialize_generated_fmus(case_spec=case_spec, source_dir=source_dir, examples_root=examples_root)
        raw_relpaths = _ensure_raw_links(source_dir=source_dir, examples_root=examples_root, relpaths=_build_case_relpaths(case_spec))

        stage_payloads: List[Dict[str, Any]] = []
        time_payloads: List[Dict[str, Any]] = []
        for stage_spec in case_spec.stages:
            config_path = examples_root / case_spec.source_relpath / stage_spec.config_relpath
            time_path = (examples_root / case_spec.source_relpath / stage_spec.time_relpath) if stage_spec.time_relpath else None
            stage_payloads.append(read_json(config_path))
            time_payloads.append(read_json(time_path) if time_path and time_path.exists() else {})

        alias_multi_instance = _alias_modes(stage_payloads)
        instances: Dict[Tuple[str, str], InstanceRecord] = {}
        for stage_payload in stage_payloads:
            fmus = stage_payload.get("fmus") if isinstance(stage_payload.get("fmus"), dict) else {}
            for alias, raw_path in fmus.items():
                if not isinstance(alias, str) or not isinstance(raw_path, str):
                    continue
                resolved_path = _resolve_workspace_path(raw_path, examples_root=examples_root, generated_paths=generated_paths)
                generated = _workspace_relpath(raw_path) in generated_paths

                namespaces = sorted(
                    {
                        _endpoint_namespace(reference)
                        for reference in _iter_stage_refs(stage_payload)
                        if reference.startswith(f"{alias}.")
                    }
                )
                instance_names = namespaces if alias_multi_instance.get(alias, False) else [_clean_alias(alias)]
                if not instance_names:
                    instance_names = [_clean_alias(alias)]

                for instance_name in instance_names:
                    key = (alias, instance_name)
                    if key in instances:
                        continue
                    asset_id = f"asset_dtaas_{case_spec.slug}__{slugify(instance_name)}"
                    metadata = parse_fmu_metadata(
                        fmu_path=resolved_path,
                        asset_id=asset_id,
                        fallback_name=instance_name,
                        fallback_description=case_spec.description,
                    )
                    base_model_name = str(metadata["name"])
                    description = _description_for_instance(
                        instance_name=instance_name,
                        base_model_name=base_model_name,
                        base_description=str(metadata.get("description") or ""),
                        case_title=case_spec.title,
                    )
                    metadata["name"] = instance_name
                    metadata["description"] = description
                    instances[key] = InstanceRecord(
                        alias=alias,
                        instance_name=instance_name,
                        asset_id=asset_id,
                        fmu_path=resolved_path,
                        raw_workspace_path=_workspace_relpath(raw_path),
                        metadata=metadata,
                        base_model_name=base_model_name,
                        description=description,
                        generated=generated,
                    )

        normalized_stages: List[Dict[str, Any]] = []
        union_connections: List[Dict[str, Any]] = []
        union_monitored: List[Dict[str, Any]] = []
        union_execution_order: List[str] = []
        union_parameters: List[Dict[str, Any]] = []
        union_raw_config_relpaths: List[str] = list(raw_relpaths)
        top_level_fault: List[Dict[str, Any]] = []
        top_level_model_swap: List[Dict[str, Any]] = []

        for stage_spec, stage_payload, time_payload in zip(case_spec.stages, stage_payloads, time_payloads):
            stage = _normalize_stage(
                case_spec=case_spec,
                stage_spec=stage_spec,
                stage_payload=stage_payload,
                time_payload=time_payload,
                alias_multi_instance=alias_multi_instance,
                instances=instances,
                source_dir=source_dir,
                examples_root=examples_root,
            )
            normalized_stages.append({key: value for key, value in stage.items() if not key.startswith("_")})
            union_connections.extend(stage["connections"])
            union_connections.extend(stage.get("_union_swap_connections", []))
            union_monitored.extend(stage["monitored_outputs"])
            union_execution_order.extend(stage["execution_order"])
            union_parameters.extend(stage.get("extensions", {}).get("parameter_overrides", []))
            union_raw_config_relpaths.extend(stage.get("extensions", {}).get("raw_config_relpaths", []))
            if stage.get("extensions", {}).get("fault_injection"):
                top_level_fault.append(stage["extensions"]["fault_injection"])
            if stage.get("extensions", {}).get("model_swap"):
                top_level_model_swap.append(stage["extensions"]["model_swap"])

        selected_asset_ids = _ordered_unique([record.asset_id for record in instances.values()])
        monitored_outputs = _ordered_unique(union_monitored)
        requirement_payload = {
            "id": f"REQ-DTAAS-{case_spec.slug.upper()}",
            "title": case_spec.title,
            "description": case_spec.description,
            "scenario": {
                **({
                    "t_start_s": normalized_stages[0]["schedule"].get("start_time"),
                    "t_end_s": normalized_stages[0]["schedule"].get("stop_time"),
                } if normalized_stages and len(normalized_stages) == 1 else {}),
                "inputs": {},
                "initial_conditions": {},
            },
            "acceptance_criteria": [],
            "signals_of_interest": _ordered_unique([item["name"] for item in monitored_outputs]),
        }

        top_schedule = dict(normalized_stages[0]["schedule"]) if len(normalized_stages) == 1 else {
            "kind": "multi_stage",
            "stage_count": len(normalized_stages),
            "start_time": min(
                (stage["schedule"].get("start_time") for stage in normalized_stages if stage["schedule"].get("start_time") is not None),
                default=0.0,
            ),
            "stop_time": max(
                (stage["schedule"].get("stop_time") for stage in normalized_stages if stage["schedule"].get("stop_time") is not None),
                default=0.0,
            ),
        }
        if len(normalized_stages) == 1:
            top_schedule["kind"] = "co_simulation"

        top_extensions: Dict[str, Any] = {
            "parameter_overrides": _ordered_unique(union_parameters),
            "raw_config_relpaths": _ordered_unique(union_raw_config_relpaths),
        }
        runtime_extension = _runtime_extension(case_spec=case_spec, raw_relpaths=raw_relpaths)
        if runtime_extension:
            top_extensions["runtime_io"] = runtime_extension
        if top_level_fault:
            top_extensions["fault_injection"] = _ordered_unique(top_level_fault)
        if top_level_model_swap:
            top_extensions["model_swap"] = _ordered_unique(top_level_model_swap)

        orchestration_payload = {
            "schema": "UNIFIED_SOLUTION_V1",
            "case_id": f"case_dtaas_{case_spec.slug}",
            "selected_asset_ids": selected_asset_ids,
            "connections": _ordered_unique(union_connections),
            "external_inputs": [],
            "monitored_outputs": monitored_outputs,
            "schedule": top_schedule,
            "execution_order": _ordered_unique(union_execution_order),
            "adapters": [],
            "loop_resolution": [],
            "notes": [case_spec.expected_behavior],
            "stages": normalized_stages,
            "extensions": top_extensions,
        }

        ground_truth_payload = {
            "correct_fmus": [f"fmu_{record.instance_name}" for record in instances.values()],
            "correct_connections": [
                {"from": item["source"], "to": item["target"]}
                for item in orchestration_payload["connections"]
            ],
            "expected_behavior": case_spec.expected_behavior,
            "stages": [
                {
                    "stage_id": stage["stage_id"],
                    "selected_asset_ids": stage["selected_asset_ids"],
                    "connections": stage["connections"],
                    "schedule": stage["schedule"],
                }
                for stage in normalized_stages
            ],
            "extensions": top_extensions,
        }

        sysml_text = _generate_sysml(
            package_name=f"Pkg{slugify(case_spec.slug).title().replace('_', '')}",
            system_name=f"System{slugify(case_spec.slug).title().replace('_', '')}",
            instances=sorted(instances.values(), key=lambda item: item.instance_name),
            connections=orchestration_payload["connections"],
        )
        _write_source_case(
            case_spec=case_spec,
            source_dir=source_dir,
            examples_root=examples_root,
            instances=sorted(instances.values(), key=lambda item: item.instance_name),
            requirement_payload=requirement_payload,
            orchestration_payload=orchestration_payload,
            ground_truth_payload=ground_truth_payload,
            sysml_text=sysml_text,
        )
        asset_payloads, _ = _normalize_case(
            case_spec=case_spec,
            dataset_root=dataset_root,
            source_dir=source_dir,
            instances=sorted(instances.values(), key=lambda item: item.instance_name),
            requirement_payload=requirement_payload,
            orchestration_payload=orchestration_payload,
            ground_truth_payload=ground_truth_payload,
            sysml_text=sysml_text,
        )
        asset_count += len(asset_payloads)
        case_count += 1

    return {"assets": asset_count, "cases": case_count}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.migrate_dtaas_examples_to_dataset")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument("--examples-root", default=None, help="DTaaS example repository root.")
    args = parser.parse_args()
    result = migrate(
        dataset_root=Path(args.dataset_root),
        examples_root=Path(args.examples_root).resolve() if args.examples_root else None,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
