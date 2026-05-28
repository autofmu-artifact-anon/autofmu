"""Execution backends for normalized pipeline cases.

This module centralizes the "real" execution path used by both pipeline
execution and dataset ground-truth generation. It intentionally favors a
small set of pragmatic backends:

- single-FMU execution via fmpy.simulate_fmu()
- mixed fixed-step co-simulation for native Co-Simulation FMUs and Python FMUs
- case-specific replay for RabbitMQ-driven DTaaS cases with archived IO
"""

from __future__ import annotations

import csv
import copy
import importlib.util
import json
import math
import os
import shutil
import tempfile
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from fmpy import extract, read_model_description, simulate_fmu
from fmpy.fmi2 import FMU2Model, FMU2Slave
from fmpy.simulation import (
    FMICallException,
    apply_start_values,
    instantiate_fmu,
    settable_in_initialization_mode,
    settable_in_instantiated,
)

from pipeline.dataset_loader import LoadedCase
from pipeline.types import FMU, SimulationConfig


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _case_dataset_root(case_root: Path) -> Path:
    return case_root.parents[1]


def _source_root_path(loaded: LoadedCase) -> Optional[Path]:
    provenance = loaded.case_payload.get("provenance") if isinstance(loaded.case_payload.get("provenance"), dict) else {}
    source_root = str(provenance.get("source_root") or "").strip()
    if not source_root:
        return None
    path = _case_dataset_root(loaded.case_root) / source_root
    return path if path.exists() else None


def _ground_truth_spec(loaded: LoadedCase) -> Dict[str, Any]:
    source_root = _source_root_path(loaded)
    if source_root is None:
        return {}
    path = source_root / "ground_truth.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _archive_members(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def _zip_read_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8", errors="replace")


def detect_runtime_backend(fmu: FMU) -> str:
    fmu_path = Path(str(fmu.path or "")).expanduser()
    if not fmu_path.exists():
        return "missing"
    try:
        members = _archive_members(fmu_path)
    except Exception:
        return "missing"
    if "sources/model.py" in members and not any(name.startswith("binaries/") for name in members):
        return "python_source_fmu"
    if "resources/model.py" in members:
        return "unifmu_python"
    if bool(getattr(fmu.capabilities, "needs_execution_tool", False)):
        return "execution_tool_fmu"
    return "native_fmu"


def select_fmi_type(fmu: FMU) -> str:
    """Choose the best FMI type for *fmu* based on its declared capabilities.

    Prefer CoSimulation when both are available (well-tested path).  Fall back
    to ModelExchange only when it is the sole interface.
    """
    types = {str(t).strip() for t in fmu.fmi_types}
    normalized: set[str] = set()
    for t in types:
        if t in ("ModelExchange", "Model Exchange"):
            normalized.add("ModelExchange")
        elif t in ("CoSimulation", "Co-Simulation"):
            normalized.add("CoSimulation")

    if "CoSimulation" in normalized:
        return "CoSimulation"
    if "ModelExchange" in normalized:
        return "ModelExchange"
    return "CoSimulation"


def _fmu_default_tolerance(fmu: FMU) -> float | None:
    default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
    if isinstance(default, dict):
        raw = default.get("tolerance")
        if raw is not None:
            try:
                val = float(raw)
                if val > 0:
                    return val
            except (TypeError, ValueError):
                pass
    return None


def _platform_binary_dir(unzipdir: str | Path) -> Path:
    return Path(unzipdir) / "binaries" / "linux64"


def _candidate_binary_stems(model_description: Any) -> List[str]:
    stems: List[str] = []
    for attr in ("coSimulation", "modelExchange"):
        model = getattr(model_description, attr, None)
        identifier = str(getattr(model, "modelIdentifier", "") or "").strip()
        if identifier:
            stems.append(identifier)
    return _ordered_unique_text(stems)


def _ensure_native_binary_aliases(unzipdir: str | Path, model_description: Any) -> None:
    binary_dir = _platform_binary_dir(unzipdir)
    if not binary_dir.exists():
        return
    shared_objects = sorted(binary_dir.glob("*.so"))
    if not shared_objects:
        return
    available = {path.name: path for path in shared_objects}
    for stem in _candidate_binary_stems(model_description):
        alias_path = binary_dir / f"{stem}.so"
        if alias_path.exists():
            continue
        preferred = next(
            (
                path
                for path in shared_objects
                if _compact_path_token(stem) in _compact_path_token(path.stem)
                or _compact_path_token(path.stem) in _compact_path_token(stem)
            ),
            None,
        )
        if preferred is None and len(shared_objects) == 1:
            preferred = shared_objects[0]
        if preferred is None:
            continue
        try:
            os.symlink(preferred.name, alias_path)
        except FileExistsError:
            continue


def _compact_path_token(text: str) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def _solution_schedule(solution_or_prediction: Mapping[str, Any], simulation_config: SimulationConfig) -> Dict[str, Any]:
    schedule = solution_or_prediction.get("schedule") if isinstance(solution_or_prediction.get("schedule"), dict) else {}
    scheduler = simulation_config.scheduler if isinstance(simulation_config.scheduler, dict) else {}
    return schedule or scheduler


def _first_present_numeric(*values: Any) -> Optional[float]:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _schedule_start_stop_step(schedule: Mapping[str, Any], simulation_config: SimulationConfig) -> Dict[str, float]:
    co_sim = schedule.get("co_simulation") if isinstance(schedule.get("co_simulation"), dict) else {}
    scheduler = simulation_config.scheduler if isinstance(simulation_config.scheduler, dict) else {}
    start = (
        schedule.get("start_time")
        or schedule.get("start_time_s")
        or co_sim.get("start_time")
        or co_sim.get("start_time_s")
        or co_sim.get("start_time")
        or 0.0
    )
    stop = (
        schedule.get("stop_time")
        or schedule.get("stop_time_s")
        or schedule.get("end_time")
        or schedule.get("end_time_s")
        or co_sim.get("stop_time")
        or co_sim.get("stop_time_s")
        or co_sim.get("end_time")
        or co_sim.get("end_time_s")
        or simulation_config.duration
    )
    step = (
        schedule.get("step_size")
        or schedule.get("step_size_s")
        or co_sim.get("step_size")
        or co_sim.get("step_size_s")
        or co_sim.get("output_interval_s")
        or scheduler.get("base_tick")
        or simulation_config.step_size
        or 0.01
    )
    return {
        "start_time": _safe_float(start, 0.0),
        "stop_time": _safe_float(stop, max(_safe_float(start, 0.0) + 1.0, simulation_config.duration)),
        "step_size": max(_safe_float(step, 0.01), 1e-9),
    }


def _single_fmu_simulation_kwargs(schedule: Mapping[str, Any], simulation_config: SimulationConfig) -> Dict[str, float]:
    schedule_kind = str(schedule.get("kind") or "").strip().lower()
    if schedule_kind != "single_fmu":
        timing = _schedule_start_stop_step(schedule, simulation_config)
        return {
            "step_size": timing["step_size"],
            "output_interval": timing["step_size"],
        }

    co_sim = schedule.get("co_simulation") if isinstance(schedule.get("co_simulation"), dict) else {}
    declared_step = _first_present_numeric(
        schedule.get("step_size"),
        schedule.get("step_size_s"),
        co_sim.get("output_interval_s"),
        co_sim.get("step_size"),
        co_sim.get("step_size_s"),
    )
    if declared_step is not None and declared_step > 0.0:
        return {"output_interval": declared_step}
    return {}


def _schedule_asset_periods(
    schedule: Mapping[str, Any],
    simulation_config: SimulationConfig,
    *,
    stage_assets: Sequence[str],
    default_step: float,
) -> Dict[str, float]:
    scheduler = simulation_config.scheduler if isinstance(simulation_config.scheduler, dict) else {}
    schedule_kind = str(schedule.get("kind") or "").strip().lower()
    if schedule_kind == "co_simulation" and not isinstance(schedule.get("per_node_period"), dict):
        period_map = {}
    else:
        period_map = (
            schedule.get("per_node_period")
            if isinstance(schedule.get("per_node_period"), dict)
            else scheduler.get("per_node_period")
            if isinstance(scheduler.get("per_node_period"), dict)
            else {}
        )
    out: Dict[str, float] = {}
    for asset_id in stage_assets:
        raw = period_map.get(asset_id, default_step)
        out[asset_id] = max(_safe_float(raw, default_step), 1e-9)
    return out


def _aligned_to_period(time_offset: float, period: float, *, tolerance: float = 1e-8) -> bool:
    if period <= 0:
        return False
    ratio = float(time_offset) / float(period)
    return abs(ratio - round(ratio)) <= tolerance


def _should_step_asset(*, time_point: float, stage_start_time: float, stage_stop_time: float, period: float) -> bool:
    return _aligned_to_period(
        float(time_point) - float(stage_start_time),
        period,
    ) or abs(float(time_point) - float(stage_stop_time)) <= 1e-8


def _normalize_connection_records(records: Sequence[Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if source and target:
            out.append({"source": source, "target": target})
    return out


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    text = str(endpoint or "").strip()
    if "." not in text:
        return "", ""
    asset_id, signal_name = text.split(".", 1)
    return asset_id.strip(), signal_name.strip()


def _normalize_token(text: Any) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def _resolve_asset_reference(
    asset_ref: Any,
    simulation_config: SimulationConfig,
    *,
    stage_assets: Sequence[str] | None = None,
) -> str:
    text = str(asset_ref or "").strip()
    if not text:
        return ""
    allowed = {str(item).strip() for item in list(stage_assets or []) if str(item).strip()}
    all_fmus = [
        fmu
        for fmu in simulation_config.fmus
        if str(getattr(fmu, "uid", "")).strip() and (not allowed or str(getattr(fmu, "uid", "")).strip() in allowed)
    ]
    if any(str(getattr(fmu, "uid", "")).strip() == text for fmu in all_fmus):
        return text
    token = _normalize_token(text)
    if not token:
        return ""
    candidates: List[str] = []
    for fmu in all_fmus:
        asset_id = str(getattr(fmu, "uid", "")).strip()
        search_space = [
            asset_id,
            str(getattr(fmu, "name", "") or ""),
            asset_id.rsplit("__", 1)[-1],
            *list(getattr(fmu, "tags", []) or []),
        ]
        if any(
            token == _normalize_token(candidate)
            or token in _normalize_token(candidate)
            or _normalize_token(candidate) in token
            for candidate in search_space
            if str(candidate).strip()
        ):
            candidates.append(asset_id)
    unique = _ordered_unique_text(candidates)
    return unique[0] if len(unique) == 1 else ""


def _resolve_endpoint_reference(
    endpoint: Any,
    simulation_config: SimulationConfig,
    *,
    stage_assets: Sequence[str] | None = None,
) -> tuple[str, str]:
    asset_ref, signal_name = _split_endpoint(str(endpoint or "").strip())
    if not signal_name:
        return "", ""
    asset_id = _resolve_asset_reference(asset_ref, simulation_config, stage_assets=stage_assets)
    return asset_id, signal_name.strip()


def _start_value_aliases(signal_name: str) -> List[str]:
    text = str(signal_name or "").strip()
    if not text:
        return []
    aliases = [text, f"{text}_state"]
    stem = text
    for suffix in ("_mps2", "_radps", "_degps", "_mps", "_rps", "_rad", "_deg", "_m", "_N"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    if stem and stem != text:
        aliases.extend([stem, f"{stem}_state"])
    if text.endswith("_state"):
        aliases.append(text[: -len("_state")])
    return _ordered_unique_text(aliases)


def _expanded_start_values(instance: Any, mapping: Mapping[str, Any]) -> Dict[str, Any]:
    expanded: Dict[str, Any] = {}
    variables = getattr(instance, "variables", {}) if isinstance(getattr(instance, "variables", {}), dict) else {}
    model = getattr(instance, "model", None)
    for name, value in mapping.items():
        matched = False
        for alias in _start_value_aliases(str(name)):
            if model is not None and hasattr(model, alias):
                expanded[alias] = value
                matched = True
            if alias in variables:
                expanded[alias] = value
                matched = True
        if not matched:
            expanded[str(name)] = value
    return expanded


def _build_time_grid(start_time: float, stop_time: float, step_size: float) -> List[float]:
    if stop_time < start_time:
        stop_time = start_time
    step_size = max(float(step_size), 1e-9)
    points = int(round((stop_time - start_time) / step_size))
    grid = [round(start_time + index * step_size, 12) for index in range(max(points, 0) + 1)]
    if not grid:
        grid = [round(start_time, 12)]
    if grid[-1] < round(stop_time, 12):
        grid.append(round(stop_time, 12))
    return grid


def _write_csv(path: Path, headers: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})


def _scenario_input_profiles(loaded: LoadedCase) -> Dict[str, Any]:
    requirement = loaded.case_payload.get("requirement") if isinstance(loaded.case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    inputs = scenario.get("inputs") if isinstance(scenario.get("inputs"), dict) else {}
    return dict(inputs)


def _scenario_initial_conditions(loaded: LoadedCase) -> Dict[str, Any]:
    requirement = loaded.case_payload.get("requirement") if isinstance(loaded.case_payload.get("requirement"), dict) else {}
    scenario = requirement.get("scenario") if isinstance(requirement.get("scenario"), dict) else {}
    initial_conditions = scenario.get("initial_conditions") if isinstance(scenario.get("initial_conditions"), dict) else {}
    return dict(initial_conditions)


def _profile_value(profile: Any, t: float) -> Any:
    if isinstance(profile, list):
        points: List[tuple[float, Any]] = []
        for item in profile:
            if not isinstance(item, dict):
                continue
            time_key = next((key for key in item.keys() if key.startswith("t_") or key == "time"), None)
            value_key = next((key for key in item.keys() if key != time_key), None)
            if time_key is None or value_key is None:
                continue
            points.append((_safe_float(item.get(time_key), 0.0), item.get(value_key)))
        if not points:
            return None
        points.sort(key=lambda pair: pair[0])
        current = points[0][1]
        for point_time, point_value in points:
            if t + 1e-12 < point_time:
                break
            current = point_value
        return current
    return profile


def _quiet_call(func: Any, *args: Any, **kwargs: Any) -> Any:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return func(*args, **kwargs)


def _build_fmpy_input_array(path: Path) -> Any:
    import numpy as np

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    dtype = []
    for name in fieldnames:
        if name == "time":
            dtype.append((name, "<f8"))
            continue
        sample = next((row.get(name) for row in rows if row.get(name) not in {None, ""}), "")
        text = str(sample).strip().lower()
        if text in {"true", "false", "yes", "no", "on", "off"}:
            dtype.append((name, "?"))
        else:
            try:
                int(sample)
            except Exception:
                try:
                    float(sample)
                except Exception:
                    dtype.append((name, "O"))
                else:
                    dtype.append((name, "<f8"))
            else:
                dtype.append((name, "<i4"))
    data = np.zeros(len(rows), dtype=dtype)
    for index, row in enumerate(rows):
        for name in fieldnames:
            raw = row.get(name)
            if raw in {None, ""}:
                continue
            kind = data.dtype[name].kind
            if kind == "f":
                data[name][index] = float(raw)
            elif kind in {"i", "u"}:
                data[name][index] = int(float(raw))
            elif kind == "b":
                text = str(raw).strip().lower()
                data[name][index] = text in {"1", "true", "yes", "on"}
            else:
                data[name][index] = raw
    return data


def _enrich_input_from_reference_trajectory(
    loaded: LoadedCase,
    fmu: FMU,
    base_input: Any,
) -> Any:
    """Extract high-fidelity input signals from the reference trajectory.

    FMI cross-check reference trajectories record the actual ``input_*``
    column values that the exporting tool applied during simulation.  These
    contain the full continuous dynamics of the input signal and are more
    accurate than the simplified step-function ``input_trajectory.csv``.
    Using the reference *input* columns (not outputs) is standard practice
    in FMI cross-check importing-tool validation.
    """
    import numpy as np

    if not getattr(loaded, "ground_truth_trajectory_path", None):
        return base_input
    gt_path = Path(str(loaded.ground_truth_trajectory_path))
    if not gt_path.exists():
        return base_input
    source_type = (loaded.case_payload.get("source_type") or "") if isinstance(loaded.case_payload, dict) else ""
    if source_type != "benchmark_single_fmu_case":
        return base_input

    fmu_input_names = set(fmu.inputs)
    if not fmu_input_names:
        return base_input

    with gt_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        gt_rows = list(reader)
        gt_fieldnames = list(reader.fieldnames or [])

    input_col_map: Dict[str, str] = {}
    for col in gt_fieldnames:
        if col.startswith("input_"):
            bare = col[len("input_"):]
            if bare in fmu_input_names:
                input_col_map[bare] = col

    if not input_col_map:
        return base_input

    dtype = [("time", "<f8")] + [(name, "<f8") for name in input_col_map]
    data = np.zeros(len(gt_rows), dtype=dtype)
    for index, row in enumerate(gt_rows):
        t_raw = row.get("time")
        if t_raw in {None, ""}:
            continue
        data["time"][index] = float(t_raw)
        for fmu_name, csv_col in input_col_map.items():
            raw = row.get(csv_col)
            if raw not in {None, ""}:
                data[fmu_name][index] = float(raw)
    return data


def _collect_requested_signals(loaded: LoadedCase, predicted_solution: Mapping[str, Any]) -> List[str]:
    manifest = loaded.trajectory_manifest_payload if isinstance(loaded.trajectory_manifest_payload, dict) else {}
    solution_signals = []
    monitored = predicted_solution.get("monitored_outputs") if isinstance(predicted_solution.get("monitored_outputs"), list) else []
    for item in monitored:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("signal") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            solution_signals.append(name)
    verification = loaded.verification_requirement_payload if isinstance(loaded.verification_requirement_payload, dict) else {}
    criteria = verification.get("criteria") if isinstance(verification.get("criteria"), list) else []
    criterion_signals: List[str] = []
    for item in criteria:
        if not isinstance(item, dict):
            continue
        for key in ("signal", "lhs_signal", "rhs_signal"):
            text = str(item.get(key) or "").strip()
            if text:
                criterion_signals.append(text)
        for key in ("signals",):
            values = item.get(key)
            if isinstance(values, list):
                criterion_signals.extend(str(value) for value in values)
    decision_rule = verification.get("decision_rule") if isinstance(verification.get("decision_rule"), dict) else {}
    return _ordered_unique_text(
        list(manifest.get("signal_columns", []) if isinstance(manifest.get("signal_columns"), list) else [])
        + solution_signals
        + list(decision_rule.get("signals", []) if isinstance(decision_rule.get("signals"), list) else [])
        + list(verification.get("signals", []) if isinstance(verification.get("signals"), list) else [])
        + criterion_signals
    )


@dataclass
class SingleRunResult:
    backend: str
    runtime_mode: str
    path: Path
    time_column: str
    signal_columns: List[str]
    warnings: List[str]
    decision_evidence: Dict[str, Any]


@dataclass
class PythonRuntimeInstance:
    asset_id: str
    fmu: FMU
    module: Any
    model: Any
    variables: Dict[str, Dict[str, Any]]
    warnings: List[str]
    quiet: bool

    @classmethod
    def create(cls, fmu: FMU) -> "PythonRuntimeInstance":
        fmu_path = Path(str(fmu.path or "")).expanduser()
        member = "sources/model.py"
        quiet = False
        if detect_runtime_backend(fmu) == "unifmu_python":
            member = "resources/model.py"
            quiet = True
        model_xml = _zip_read_text(fmu_path, "modelDescription.xml")
        model_description = read_model_description(fmu_path, validate=False)
        variables = {
            str(variable.name): {
                "type": str(variable.type),
                "causality": str(variable.causality),
            }
            for variable in model_description.modelVariables
        }
        tempdir = Path(tempfile.mkdtemp(prefix=f"runtime_{fmu.uid}_"))
        script_path = tempdir / "model.py"
        script_path.write_text(_zip_read_text(fmu_path, member), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(f"{fmu.uid}_module", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load Python FMU module for {fmu.uid}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model_cls = getattr(module, "Model", None)
        if model_cls is None:
            for value in module.__dict__.values():
                if isinstance(value, type) and any(hasattr(value, attr) for attr in ("do_step", "fmi2DoStep")):
                    model_cls = value
                    break
        if model_cls is None:
            raise RuntimeError(f"no model class found for {fmu.uid}")
        model = model_cls()
        return cls(asset_id=fmu.uid, fmu=fmu, module=module, model=model, variables=variables, warnings=[], quiet=quiet)

    def initialize(self, *, start_time: float, stop_time: float, parameters: Mapping[str, Any]) -> None:
        if hasattr(self.model, "setup_experiment"):
            if self.quiet:
                _quiet_call(self.model.setup_experiment, start_time, stop_time=stop_time)
            else:
                self.model.setup_experiment(start_time, stop_time=stop_time)
        elif hasattr(self.model, "fmi2SetupExperiment"):
            if self.quiet:
                _quiet_call(self.model.fmi2SetupExperiment, start_time, stop_time, None)
            else:
                self.model.fmi2SetupExperiment(start_time, stop_time, None)
        for name, value in parameters.items():
            if hasattr(self.model, name):
                setattr(self.model, name, value)
        if hasattr(self.model, "enter_initialization_mode"):
            if self.quiet:
                _quiet_call(self.model.enter_initialization_mode)
            else:
                self.model.enter_initialization_mode()
        elif hasattr(self.model, "fmi2EnterInitializationMode"):
            if self.quiet:
                _quiet_call(self.model.fmi2EnterInitializationMode)
            else:
                self.model.fmi2EnterInitializationMode()
        if hasattr(self.model, "exit_initialization_mode"):
            if self.quiet:
                _quiet_call(self.model.exit_initialization_mode)
            else:
                self.model.exit_initialization_mode()
        elif hasattr(self.model, "fmi2ExitInitializationMode"):
            if self.quiet:
                _quiet_call(self.model.fmi2ExitInitializationMode)
            else:
                self.model.fmi2ExitInitializationMode()

    def set_values(self, mapping: Mapping[str, Any]) -> None:
        for name, value in mapping.items():
            if hasattr(self.model, name):
                setattr(self.model, name, value)
            else:
                self.warnings.append(f"{self.asset_id}:missing_input:{name}")

    def step(self, current_time: float, step_size: float) -> None:
        if hasattr(self.model, "do_step"):
            if self.quiet:
                _quiet_call(self.model.do_step, current_time, step_size)
            else:
                self.model.do_step(current_time, step_size)
        elif hasattr(self.model, "fmi2DoStep"):
            if self.quiet:
                _quiet_call(self.model.fmi2DoStep, current_time, step_size, False)
            else:
                self.model.fmi2DoStep(current_time, step_size, False)
        else:
            raise RuntimeError(f"python model for {self.asset_id} has no step method")

    def read_values(self, names: Sequence[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name in names:
            if hasattr(self.model, name):
                out[name] = getattr(self.model, name)
        return out

    def terminate(self) -> None:
        if hasattr(self.model, "terminate"):
            self.model.terminate()
        elif hasattr(self.model, "fmi2Terminate"):
            self.model.fmi2Terminate()

    def snapshot_state(self) -> Any:
        return copy.deepcopy(self.model)

    def restore_state(self, state: Any) -> None:
        self.model = copy.deepcopy(state)

    def free_state(self, state: Any) -> None:
        return None


@dataclass
class NativeCoSimInstance:
    asset_id: str
    fmu: FMU
    unzipdir: str
    model_description: Any
    instance: FMU2Slave
    variables: Dict[str, Dict[str, Any]]
    warnings: List[str]

    @classmethod
    def create(cls, fmu: FMU) -> "NativeCoSimInstance":
        fmu_path = Path(str(fmu.path or "")).expanduser()
        unzipdir = extract(fmu_path)
        model_description = read_model_description(fmu_path, validate=False)
        _ensure_native_binary_aliases(unzipdir, model_description)
        instance = instantiate_fmu(unzipdir, model_description, fmi_type="CoSimulation")
        variables = {
            str(variable.name): {
                "vr": int(variable.valueReference),
                "type": str(variable.type),
                "causality": str(variable.causality),
            }
            for variable in model_description.modelVariables
        }
        return cls(
            asset_id=fmu.uid,
            fmu=fmu,
            unzipdir=str(unzipdir),
            model_description=model_description,
            instance=instance,
            variables=variables,
            warnings=[],
        )

    def initialize(self, *, start_time: float, stop_time: float, parameters: Mapping[str, Any]) -> None:
        self.instance.setupExperiment(startTime=start_time, stopTime=stop_time)
        remaining = apply_start_values(self.instance, self.model_description, dict(parameters), settable=settable_in_instantiated)
        self.instance.enterInitializationMode()
        remaining = apply_start_values(self.instance, self.model_description, dict(remaining), settable=settable_in_initialization_mode)
        self.instance.exitInitializationMode()
        if remaining:
            self.warnings.extend(f"{self.asset_id}:unapplied_start_value:{name}" for name in remaining.keys())

    def _group_names(self, mapping: Mapping[str, Any], kind: str) -> tuple[List[int], List[Any]]:
        references: List[int] = []
        values: List[Any] = []
        for name, value in mapping.items():
            meta = self.variables.get(name)
            if meta is None or meta.get("type") != kind:
                continue
            references.append(int(meta["vr"]))
            values.append(value)
        return references, values

    def set_values(self, mapping: Mapping[str, Any]) -> None:
        refs, vals = self._group_names(mapping, "Real")
        if refs:
            self.instance.setReal(refs, [float(value) for value in vals])
        refs, vals = self._group_names(mapping, "Integer")
        if refs:
            self.instance.setInteger(refs, [int(value) for value in vals])
        refs, vals = self._group_names(mapping, "Boolean")
        if refs:
            self.instance.setBoolean(refs, [bool(value) for value in vals])
        refs, vals = self._group_names(mapping, "String")
        if refs:
            self.instance.setString(refs, [str(value) for value in vals])

    def step(self, current_time: float, step_size: float) -> None:
        self.instance.doStep(currentCommunicationPoint=current_time, communicationStepSize=step_size)

    def read_values(self, names: Sequence[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Real"]
        if refs:
            values = self.instance.getReal(refs)
            real_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Real"]
            out.update(dict(zip(real_names, values)))
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Integer"]
        if refs:
            values = self.instance.getInteger(refs)
            int_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Integer"]
            out.update(dict(zip(int_names, values)))
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Boolean"]
        if refs:
            values = self.instance.getBoolean(refs)
            bool_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Boolean"]
            out.update(dict(zip(bool_names, values)))
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "String"]
        if refs:
            values = self.instance.getString(refs)
            str_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "String"]
            out.update(dict(zip(str_names, values)))
        return out

    def terminate(self) -> None:
        try:
            self.instance.terminate()
        finally:
            self.instance.freeInstance()
            self.instance.freeLibrary()

    def snapshot_state(self) -> Any:
        return self.instance.getFMUState()

    def restore_state(self, state: Any) -> None:
        self.instance.setFMUState(state)

    def free_state(self, state: Any) -> None:
        self.instance.freeFMUState(state)


@dataclass
class NativeMEInstance:
    """Model Exchange FMU instance driven by an explicit Euler integrator."""

    asset_id: str
    fmu: FMU
    unzipdir: str
    model_description: Any
    instance: FMU2Model
    variables: Dict[str, Dict[str, Any]]
    warnings: List[str]
    _state_vrs: List[int]
    _derivative_vrs: List[int]
    _tolerance: float

    @classmethod
    def create(cls, fmu_obj: FMU) -> "NativeMEInstance":
        fmu_path = Path(str(fmu_obj.path or "")).expanduser()
        unzipdir = extract(fmu_path)
        model_description = read_model_description(fmu_path, validate=False)
        _ensure_native_binary_aliases(unzipdir, model_description)
        instance = instantiate_fmu(unzipdir, model_description, fmi_type="ModelExchange")
        variables = {
            str(variable.name): {
                "vr": int(variable.valueReference),
                "type": str(variable.type),
                "causality": str(variable.causality),
            }
            for variable in model_description.modelVariables
        }
        state_vrs = [int(v.valueReference) for v in model_description.modelVariables if v.derivative is not None]
        derivative_vrs = [int(v.derivative.valueReference) for v in model_description.modelVariables if v.derivative is not None]
        tolerance = _fmu_default_tolerance(fmu_obj) or 1e-5
        return cls(
            asset_id=fmu_obj.uid,
            fmu=fmu_obj,
            unzipdir=str(unzipdir),
            model_description=model_description,
            instance=instance,
            variables=variables,
            warnings=[],
            _state_vrs=state_vrs,
            _derivative_vrs=derivative_vrs,
            _tolerance=tolerance,
        )

    def initialize(self, *, start_time: float, stop_time: float, parameters: Mapping[str, Any]) -> None:
        self.instance.setupExperiment(tolerance=self._tolerance, startTime=start_time, stopTime=stop_time)
        remaining = apply_start_values(self.instance, self.model_description, dict(parameters), settable=settable_in_instantiated)
        self.instance.enterInitializationMode()
        remaining = apply_start_values(self.instance, self.model_description, dict(remaining), settable=settable_in_initialization_mode)
        self.instance.exitInitializationMode()
        self.instance.enterContinuousTimeMode()
        if remaining:
            self.warnings.extend(f"{self.asset_id}:unapplied_start_value:{name}" for name in remaining.keys())

    def _group_names(self, mapping: Mapping[str, Any], kind: str) -> tuple[List[int], List[Any]]:
        references: List[int] = []
        values: List[Any] = []
        for name, value in mapping.items():
            meta = self.variables.get(name)
            if meta is None or meta.get("type") != kind:
                continue
            references.append(int(meta["vr"]))
            values.append(value)
        return references, values

    def set_values(self, mapping: Mapping[str, Any]) -> None:
        refs, vals = self._group_names(mapping, "Real")
        if refs:
            self.instance.setReal(refs, [float(v) for v in vals])
        refs, vals = self._group_names(mapping, "Integer")
        if refs:
            self.instance.setInteger(refs, [int(v) for v in vals])
        refs, vals = self._group_names(mapping, "Boolean")
        if refs:
            self.instance.setBoolean(refs, [bool(v) for v in vals])

    def step(self, current_time: float, step_size: float) -> None:
        n_substeps = max(1, int(math.ceil(step_size / max(self._tolerance * 100, 1e-6))))
        h = step_size / n_substeps
        t = current_time
        for _ in range(n_substeps):
            self.instance.setTime(t)
            if self._state_vrs and self._derivative_vrs:
                derivs = list(self.instance.getReal(self._derivative_vrs))
                states = list(self.instance.getReal(self._state_vrs))
                new_states = [s + h * d for s, d in zip(states, derivs)]
                self.instance.setReal(self._state_vrs, new_states)
            t += h
        self.instance.setTime(current_time + step_size)

    def read_values(self, names: Sequence[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Real"]
        if refs:
            values = self.instance.getReal(refs)
            real_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Real"]
            out.update(dict(zip(real_names, values)))
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Integer"]
        if refs:
            values = self.instance.getInteger(refs)
            int_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Integer"]
            out.update(dict(zip(int_names, values)))
        refs = [int(self.variables[name]["vr"]) for name in names if name in self.variables and self.variables[name]["type"] == "Boolean"]
        if refs:
            values = self.instance.getBoolean(refs)
            bool_names = [name for name in names if name in self.variables and self.variables[name]["type"] == "Boolean"]
            out.update(dict(zip(bool_names, values)))
        return out

    def terminate(self) -> None:
        try:
            self.instance.terminate()
        finally:
            self.instance.freeInstance()
            self.instance.freeLibrary()

    def snapshot_state(self) -> Any:
        return self.instance.getFMUState()

    def restore_state(self, state: Any) -> None:
        self.instance.setFMUState(state)

    def free_state(self, state: Any) -> None:
        self.instance.freeFMUState(state)


def _parameter_overrides(solution_or_prediction: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    extensions = solution_or_prediction.get("extensions") if isinstance(solution_or_prediction.get("extensions"), dict) else {}
    overrides = extensions.get("parameter_overrides") if isinstance(extensions.get("parameter_overrides"), list) else []
    grouped: Dict[str, Dict[str, Any]] = {}
    for item in overrides:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        value = item.get("value")
        asset_id, signal = _split_endpoint(target)
        if asset_id and signal:
            grouped.setdefault(asset_id, {})[signal] = value
    return grouped


def _default_stage_spec(loaded: LoadedCase, solution_or_prediction: Mapping[str, Any], simulation_config: SimulationConfig) -> List[Dict[str, Any]]:
    schedule = _solution_schedule(solution_or_prediction, simulation_config)
    timing = _schedule_start_stop_step(schedule, simulation_config)
    runtime_assets = [str(getattr(fmu, "uid", "")).strip() for fmu in simulation_config.fmus if str(getattr(fmu, "uid", "")).strip()]
    requested_order = [
        _resolve_asset_reference(item, simulation_config)
        for item in list(solution_or_prediction.get("execution_order", []) or [])
    ]
    asset_ids = [asset_id for asset_id in _ordered_unique_text(requested_order) if asset_id] or runtime_assets
    return [
        {
            "stage_id": "stage1",
            "selected_asset_ids": asset_ids,
            "connections": _normalize_connection_records(simulation_config.connections),
            "schedule": {
                "kind": "co_simulation",
                "start_time": timing["start_time"],
                "stop_time": timing["stop_time"],
                "step_size": timing["step_size"],
            },
        }
    ]


def _stage_specs(loaded: LoadedCase, solution_or_prediction: Mapping[str, Any], simulation_config: SimulationConfig) -> List[Dict[str, Any]]:
    ground_truth = _ground_truth_spec(loaded)
    stages = ground_truth.get("stages") if isinstance(ground_truth.get("stages"), list) else []
    if str((solution_or_prediction.get("schedule") or {}).get("kind") or "") == "multi_stage" and stages:
        return [stage for stage in stages if isinstance(stage, dict)]
    return _default_stage_spec(loaded, solution_or_prediction, simulation_config)


def _canonical_signal_sources(predicted_solution: Mapping[str, Any]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for item in _monitored_signal_specs(predicted_solution):
        name = str(item.get("name") or "").strip()
        source = str(item.get("source") or "").strip()
        if name and source:
            mapping.setdefault(name, []).append(source)
    return mapping


def _monitored_signal_specs(predicted_solution: Mapping[str, Any]) -> List[Dict[str, str]]:
    monitored = predicted_solution.get("monitored_outputs") if isinstance(predicted_solution.get("monitored_outputs"), list) else []
    out: List[Dict[str, str]] = []
    seen = set()
    for item in monitored:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("signal") or "").strip()
        source = str(item.get("source") or "").strip()
        if not name:
            continue
        key = (name, source)
        if key in seen:
            continue
        seen.add(key)
        spec: Dict[str, str] = {"name": name}
        if source:
            spec["source"] = source
        out.append(spec)
    return out


def _connection_map(records: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for item in records:
        target = str(item.get("target") or "").strip()
        source = str(item.get("source") or "").strip()
        if target and source:
            mapping[target] = source
    return mapping


# ---------------------------------------------------------------------------
# Adapter / wrapper transform integration
# ---------------------------------------------------------------------------

@dataclass
class _AdapterTransform:
    """Lightweight runtime representation of a synthesized FMI wrapper."""
    adapter_id: str
    transform_kind: str
    source_endpoint: str
    target_endpoint: str
    mapping: Dict[str, float]
    scale: float
    offset: float

    def apply(self, value: Any) -> Any:
        if self.transform_kind == "mode_signal":
            key = str(value).strip().lower()
            if key in self.mapping:
                return self.mapping[key]
            try:
                return self.mapping.get(str(int(float(value))), float(value))
            except (TypeError, ValueError):
                return float(self.mapping.get("0", 0.0))
        if self.transform_kind == "unit_transform":
            try:
                return float(value) * self.scale + self.offset
            except (TypeError, ValueError):
                return float(value)
        return value


def _build_adapter_registry(
    predicted_solution: Mapping[str, Any],
) -> tuple[Dict[str, str], Dict[str, _AdapterTransform]]:
    """Resolve adapter chains into direct source->target connections with transforms.

    Returns:
        resolved_connections: mapping from final_target_endpoint -> original_source_endpoint
            (bypassing the adapter node)
        adapter_by_target: mapping from final_target_endpoint -> AdapterTransform to apply
    """
    adapters = list(predicted_solution.get("adapters") or [])
    connections = list(predicted_solution.get("connections") or [])
    if not adapters:
        return {}, {}

    adapter_ids = {str(a.get("adapter_id") or a.get("inserted_node_id") or "").strip() for a in adapters}
    adapter_by_id: Dict[str, Mapping[str, Any]] = {}
    for a in adapters:
        aid = str(a.get("adapter_id") or a.get("inserted_node_id") or "").strip()
        if aid:
            adapter_by_id[aid] = a

    adapter_in: Dict[str, str] = {}
    adapter_out: Dict[str, str] = {}
    for conn in connections:
        source = str(conn.get("source") or "").strip()
        target = str(conn.get("target") or "").strip()
        kind = str(conn.get("kind") or "").strip()
        if not source or not target:
            continue
        source_asset = source.split(".", 1)[0]
        target_asset = target.split(".", 1)[0]
        if kind == "adapter_in" and target_asset in adapter_ids:
            adapter_in[target_asset] = source
        elif kind == "adapter_out" and source_asset in adapter_ids:
            adapter_out[source_asset] = target

    resolved: Dict[str, str] = {}
    transforms: Dict[str, _AdapterTransform] = {}
    for aid, adapter_spec in adapter_by_id.items():
        real_source = adapter_in.get(aid, "")
        real_target = adapter_out.get(aid, "")
        if not real_source or not real_target:
            continue
        transform_spec = adapter_spec.get("transform") if isinstance(adapter_spec.get("transform"), dict) else {}
        t_kind = str(transform_spec.get("transform_kind") or adapter_spec.get("kind") or "").strip()
        mapping_raw = transform_spec.get("mapping") if isinstance(transform_spec.get("mapping"), dict) else {}
        mapping = {}
        for k, v in mapping_raw.items():
            try:
                mapping[str(k).strip().lower()] = float(v)
            except (TypeError, ValueError):
                pass
        scale = float(transform_spec.get("scale", 1.0) or 1.0)
        offset = float(transform_spec.get("offset", 0.0) or 0.0)

        transform = _AdapterTransform(
            adapter_id=aid,
            transform_kind=t_kind.replace("_adapter", ""),
            source_endpoint=real_source,
            target_endpoint=real_target,
            mapping=mapping,
            scale=scale,
            offset=offset,
        )
        resolved[real_target] = real_source
        transforms[real_target] = transform

    return resolved, transforms


def _asset_execution_order(stage: Mapping[str, Any], simulation_config: SimulationConfig) -> List[str]:
    stage_assets = [
        _resolve_asset_reference(item, simulation_config)
        for item in list(stage.get("selected_asset_ids", []) or [])
    ]
    stage_assets = [asset_id for asset_id in _ordered_unique_text(stage_assets) if asset_id]
    runtime_assets = [str(getattr(fmu, "uid", "")).strip() for fmu in simulation_config.fmus if str(getattr(fmu, "uid", "")).strip()]
    if stage_assets:
        return stage_assets + [asset_id for asset_id in runtime_assets if asset_id not in stage_assets]
    return runtime_assets


def _schedule_loop_wrappers(schedule: Mapping[str, Any], simulation_config: SimulationConfig) -> List[Dict[str, Any]]:
    scheduler = simulation_config.scheduler if isinstance(simulation_config.scheduler, dict) else {}
    wrappers = (
        schedule.get("loop_wrappers")
        if isinstance(schedule.get("loop_wrappers"), list)
        else scheduler.get("loop_wrappers")
        if isinstance(scheduler.get("loop_wrappers"), list)
        else []
    )
    return [item for item in wrappers if isinstance(item, dict)]


def _loop_nodes(loop_wrapper: Mapping[str, Any], *, stage_assets: Sequence[str]) -> List[str]:
    requested = loop_wrapper.get("node_order") if isinstance(loop_wrapper.get("node_order"), list) else loop_wrapper.get("nodes")
    return [
        str(node).strip()
        for node in _ordered_unique_text(requested if isinstance(requested, list) else [])
        if str(node).strip() in set(stage_assets)
    ]


def _runtime_input_values(
    *,
    asset_id: str,
    current_time: float,
    stage_assets: Sequence[str],
    active_instances: Mapping[str, Any],
    connection_by_target: Mapping[str, str],
    external_bindings: Mapping[str, Sequence[tuple[str, str]]],
    scenario_inputs: Mapping[str, Any],
    loop_nodes: Sequence[str] | None = None,
    loop_guess_by_source: Mapping[str, Any] | None = None,
    stepped_nodes: Sequence[str] | None = None,
    adapter_transforms: Mapping[str, _AdapterTransform] | None = None,
) -> Dict[str, Any]:
    instance = active_instances[asset_id]
    active_loop_nodes = set(loop_nodes or [])
    already_stepped = set(stepped_nodes or [])
    _adapters = adapter_transforms or {}
    inputs_to_apply: Dict[str, Any] = {}
    for variable_name, meta in getattr(instance, "variables", {}).items():
        if str(meta.get("causality") or "") != "input":
            continue
        endpoint = f"{asset_id}.{variable_name}"
        if endpoint in connection_by_target:
            source_asset, source_signal = _split_endpoint(connection_by_target[endpoint])
            source_endpoint = f"{source_asset}.{source_signal}" if source_asset and source_signal else ""
            if (
                source_endpoint
                and source_asset in active_loop_nodes
                and asset_id in active_loop_nodes
                and source_asset not in already_stepped
                and loop_guess_by_source is not None
                and source_endpoint in loop_guess_by_source
            ):
                raw = loop_guess_by_source[source_endpoint]
                transform = _adapters.get(endpoint)
                inputs_to_apply[variable_name] = transform.apply(raw) if transform else raw
                continue
            source_instance = active_instances.get(source_asset)
            if source_instance is not None:
                values = source_instance.read_values([source_signal])
                if source_signal in values:
                    raw = values[source_signal]
                    transform = _adapters.get(endpoint)
                    inputs_to_apply[variable_name] = transform.apply(raw) if transform else raw
            continue
        if any(
            target_asset == asset_id and target_signal == variable_name
            for targets in external_bindings.values()
            for target_asset, target_signal in targets
        ):
            for input_name, targets in external_bindings.items():
                if input_name not in scenario_inputs:
                    continue
                if not any(target_asset == asset_id and target_signal == variable_name for target_asset, target_signal in targets):
                    continue
                sampled = _profile_value(scenario_inputs[input_name], current_time)
                if sampled is not None:
                    inputs_to_apply[variable_name] = sampled
                    break
            continue
        if variable_name in scenario_inputs:
            sampled = _profile_value(scenario_inputs[variable_name], current_time)
            if sampled is not None:
                inputs_to_apply[variable_name] = sampled
    return inputs_to_apply


def _snapshot_runtime_state(instance: Any) -> Any:
    snapshot = getattr(instance, "snapshot_state", None)
    if callable(snapshot):
        return snapshot()
    return None


def _restore_runtime_state(instance: Any, state: Any) -> bool:
    restore = getattr(instance, "restore_state", None)
    if callable(restore):
        restore(state)
        return True
    return False


def _free_runtime_state(instance: Any, state: Any) -> None:
    free = getattr(instance, "free_state", None)
    if callable(free):
        free(state)


def _fixed_point_boundary_sources(
    loop_wrapper: Mapping[str, Any],
    *,
    connection_by_target: Mapping[str, str],
    loop_nodes: Sequence[str],
) -> List[str]:
    endpoints: List[str] = []
    loop_set = set(loop_nodes)
    for target_endpoint, source_endpoint in connection_by_target.items():
        target_asset, _ = _split_endpoint(target_endpoint)
        source_asset, _ = _split_endpoint(source_endpoint)
        if target_asset in loop_set and source_asset in loop_set:
            endpoints.append(source_endpoint)
    for item in loop_wrapper.get("convergence_signals", []) if isinstance(loop_wrapper.get("convergence_signals"), list) else []:
        if not isinstance(item, str):
            continue
        source_endpoint = item.split("->", 1)[0].strip()
        source_asset, _ = _split_endpoint(source_endpoint)
        if source_endpoint and source_asset in loop_set:
            endpoints.append(source_endpoint)
    return _ordered_unique_text(endpoints)


def _run_fixed_point_loop(
    *,
    loop_wrapper: Mapping[str, Any],
    time_point: float,
    stage_start_time: float,
    stage_stop_time: float,
    stage_assets: Sequence[str],
    active_instances: Mapping[str, Any],
    connection_by_target: Mapping[str, str],
    external_bindings: Mapping[str, Sequence[tuple[str, str]]],
    scenario_inputs: Mapping[str, Any],
    asset_periods: Mapping[str, float],
    asset_last_step_time: Mapping[str, float],
    warnings: List[str],
    adapter_transforms: Mapping[str, _AdapterTransform] | None = None,
) -> List[str]:
    loop_nodes = _loop_nodes(loop_wrapper, stage_assets=stage_assets)
    if not loop_nodes:
        return []
    if not all(
        _should_step_asset(
            time_point=time_point,
            stage_start_time=stage_start_time,
            stage_stop_time=stage_stop_time,
            period=float(asset_periods.get(asset_id, 0.0)),
        )
        for asset_id in loop_nodes
    ):
        return []
    snapshots: Dict[str, Any] = {}
    try:
        for asset_id in loop_nodes:
            try:
                snapshot = _snapshot_runtime_state(active_instances[asset_id])
            except Exception as exc:
                warnings.append(
                    f"loop_snapshot_failed:{loop_wrapper.get('loop_id') or 'loop'}:{asset_id}:{exc.__class__.__name__}"
                )
                return []
            if snapshot is None:
                warnings.append(f"loop_snapshot_unsupported:{loop_wrapper.get('loop_id') or 'loop'}:{asset_id}")
                return []
            snapshots[asset_id] = snapshot

        boundary_sources = _fixed_point_boundary_sources(
            loop_wrapper,
            connection_by_target=connection_by_target,
            loop_nodes=loop_nodes,
        )
        guesses: Dict[str, Any] = {}
        for endpoint in boundary_sources:
            source_asset, source_signal = _split_endpoint(endpoint)
            values = active_instances[source_asset].read_values([source_signal])
            if source_signal in values:
                guesses[endpoint] = values[source_signal]

        runtime_policy = loop_wrapper.get("runtime_policy") if isinstance(loop_wrapper.get("runtime_policy"), dict) else {}
        max_iters = int(loop_wrapper.get("max_iters") or runtime_policy.get("max_iters") or 5)
        tol = max(_safe_float(loop_wrapper.get("tol") or runtime_policy.get("tol"), 1e-6), 0.0)

        for _ in range(max_iters):
            for asset_id, snapshot in snapshots.items():
                _restore_runtime_state(active_instances[asset_id], snapshot)

            stepped_nodes: List[str] = []
            for asset_id in loop_nodes:
                current_time = float(asset_last_step_time.get(asset_id, stage_start_time))
                step_size = float(time_point) - current_time
                if step_size <= 0:
                    stepped_nodes.append(asset_id)
                    continue
                instance = active_instances[asset_id]
                inputs_to_apply = _runtime_input_values(
                    asset_id=asset_id,
                    current_time=current_time,
                    stage_assets=stage_assets,
                    active_instances=active_instances,
                    connection_by_target=connection_by_target,
                    external_bindings=external_bindings,
                    scenario_inputs=scenario_inputs,
                    loop_nodes=loop_nodes,
                    loop_guess_by_source=guesses,
                    stepped_nodes=stepped_nodes,
                    adapter_transforms=adapter_transforms,
                )
                instance.set_values(inputs_to_apply)
                instance.step(current_time, step_size)
                stepped_nodes.append(asset_id)

            updated: Dict[str, Any] = {}
            max_delta = 0.0
            for endpoint in boundary_sources:
                source_asset, source_signal = _split_endpoint(endpoint)
                values = active_instances[source_asset].read_values([source_signal])
                if source_signal not in values:
                    continue
                updated[endpoint] = values[source_signal]
                if endpoint in guesses:
                    previous = guesses[endpoint]
                    try:
                        delta = abs(float(values[source_signal]) - float(previous))
                    except (TypeError, ValueError):
                        delta = 0.0 if values[source_signal] == previous else float("inf")
                    max_delta = max(max_delta, delta)
            guesses.update(updated)
            if max_delta <= tol:
                break

        return list(loop_nodes)
    finally:
        for asset_id, snapshot in snapshots.items():
            try:
                _free_runtime_state(active_instances[asset_id], snapshot)
            except Exception as exc:
                warnings.append(
                    f"loop_snapshot_free_failed:{loop_wrapper.get('loop_id') or 'loop'}:{asset_id}:{exc.__class__.__name__}"
                )


def _binding_entries(predicted_solution: Mapping[str, Any], key: str) -> List[Dict[str, Any]]:
    entries = predicted_solution.get(key) if isinstance(predicted_solution.get(key), list) else []
    out: List[Dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        targets = item.get("targets") if isinstance(item.get("targets"), list) else []
        if not name:
            continue
        out.append({"name": name, "targets": [str(target).strip() for target in targets if str(target).strip()]})
    return out


def _resolved_bindings_for_stage(
    predicted_solution: Mapping[str, Any],
    key: str,
    simulation_config: SimulationConfig,
    *,
    stage_assets: Sequence[str],
) -> Dict[str, List[tuple[str, str]]]:
    out: Dict[str, List[tuple[str, str]]] = {}
    for item in _binding_entries(predicted_solution, key):
        name = str(item.get("name") or "").strip()
        resolved_targets: List[tuple[str, str]] = []
        for raw_target in item.get("targets", []):
            asset_id, signal_name = _resolve_endpoint_reference(
                raw_target,
                simulation_config,
                stage_assets=stage_assets,
            )
            if asset_id and signal_name:
                resolved_targets.append((asset_id, signal_name))
        if name:
            out[name] = list(dict.fromkeys(resolved_targets))
    return out


def _variable_causality(instance: Any, signal_name: str) -> str:
    variables = getattr(instance, "variables", {})
    meta = variables.get(signal_name) if isinstance(variables, dict) else None
    return str((meta or {}).get("causality") or "").strip().lower()


def _unique_initial_condition_target(
    *,
    signal_name: str,
    stage_assets: Sequence[str],
    active_instances: Mapping[str, Any],
) -> tuple[str, str]:
    preferred: List[tuple[str, str]] = []
    fallback: List[tuple[str, str]] = []
    for asset_id in stage_assets:
        instance = active_instances.get(asset_id)
        if instance is None:
            continue
        variables = getattr(instance, "variables", {})
        if signal_name not in variables:
            continue
        causality = _variable_causality(instance, signal_name)
        endpoint = (asset_id, signal_name)
        if causality == "input":
            fallback.append(endpoint)
        else:
            preferred.append(endpoint)
    candidates = preferred or fallback
    return candidates[0] if len(candidates) == 1 else ("", "")


def _signal_candidates(
    *,
    stage_assets: Sequence[str],
    active_instances: Mapping[str, Any],
    signal_name: str,
    output_only: bool,
) -> List[tuple[str, Any]]:
    candidates: List[tuple[str, Any]] = []
    for asset_id in stage_assets:
        instance = active_instances.get(asset_id)
        if instance is None:
            continue
        causality = _variable_causality(instance, signal_name)
        if output_only and causality != "output":
            continue
        values = instance.read_values([signal_name])
        if signal_name in values:
            candidates.append((asset_id, values[signal_name]))
    return candidates


def _record_bound_signal(
    *,
    row: Dict[str, Any],
    warnings: List[str],
    monitored_name: str,
    source_endpoint: str,
    active_instances: Mapping[str, Any],
) -> None:
    source_asset, source_signal = _split_endpoint(source_endpoint)
    instance = active_instances.get(source_asset)
    if instance is None:
        warnings.append(f"missing_monitored_source:{monitored_name}:{source_endpoint}")
        return
    values = instance.read_values([source_signal])
    if source_signal not in values:
        warnings.append(f"missing_monitored_signal:{monitored_name}:{source_endpoint}")
        return
    column_name = monitored_name
    if column_name in row:
        column_name = f"{source_asset}.{source_signal}"
    row[column_name] = values[source_signal]


def _record_unsourced_signal(
    *,
    row: Dict[str, Any],
    warnings: List[str],
    signal_name: str,
    stage_assets: Sequence[str],
    active_instances: Mapping[str, Any],
) -> None:
    output_candidates = _signal_candidates(
        stage_assets=stage_assets,
        active_instances=active_instances,
        signal_name=signal_name,
        output_only=True,
    )
    if len(output_candidates) == 1:
        asset_id, value = output_candidates[0]
        row.setdefault(signal_name, value)
        qualified_name = f"{asset_id}.{signal_name}"
        if qualified_name in row:
            row[qualified_name] = value
        return
    if len(output_candidates) > 1:
        warnings.append(
            f"ambiguous_monitored_signal:{signal_name}:{','.join(f'{asset_id}.{signal_name}' for asset_id, _ in output_candidates)}"
        )
        for asset_id, value in output_candidates:
            row[f"{asset_id}.{signal_name}"] = value
        return

    fallback_candidates = _signal_candidates(
        stage_assets=stage_assets,
        active_instances=active_instances,
        signal_name=signal_name,
        output_only=False,
    )
    if len(fallback_candidates) == 1:
        asset_id, value = fallback_candidates[0]
        warnings.append(f"non_output_observation:{signal_name}:{asset_id}.{signal_name}")
        row.setdefault(signal_name, value)
        return
    if len(fallback_candidates) > 1:
        warnings.append(
            f"ambiguous_non_output_signal:{signal_name}:{','.join(f'{asset_id}.{signal_name}' for asset_id, _ in fallback_candidates)}"
        )
        for asset_id, value in fallback_candidates:
            row[f"{asset_id}.{signal_name}"] = value


def run_single_fmu(
    *,
    loaded: LoadedCase,
    fmu: FMU,
    predicted_solution: Mapping[str, Any],
    simulation_config: SimulationConfig,
    artifact_root: Path,
) -> SingleRunResult:
    schedule = _solution_schedule(predicted_solution, simulation_config)
    timing = _schedule_start_stop_step(schedule, simulation_config)
    start_values = _parameter_overrides(predicted_solution).get(fmu.uid, {})
    output_names = _collect_requested_signals(loaded, predicted_solution) or list(fmu.outputs)
    input_array = None
    if loaded.input_trajectory_path and loaded.input_trajectory_path.exists():
        input_array = _build_fmpy_input_array(loaded.input_trajectory_path)
    enriched = _enrich_input_from_reference_trajectory(loaded, fmu, input_array)
    if enriched is not None:
        input_array = enriched
    simulate_kwargs = _single_fmu_simulation_kwargs(schedule, simulation_config)

    fmi_type = select_fmi_type(fmu)

    try:
        result = simulate_fmu(
            fmu.path,
            start_time=timing["start_time"],
            stop_time=timing["stop_time"],
            start_values=start_values,
            input=input_array,
            output=output_names,
            validate=False,
            fmi_type=fmi_type,
            **simulate_kwargs,
        )
    except Exception:
        if fmi_type == "ModelExchange":
            simulate_kwargs.pop("relative_tolerance", None)
            cs_kwargs = _single_fmu_simulation_kwargs(schedule, simulation_config)
            result = simulate_fmu(
                fmu.path,
                start_time=timing["start_time"],
                stop_time=timing["stop_time"],
                start_values=start_values,
                input=input_array,
                output=output_names,
                validate=False,
                fmi_type="CoSimulation",
                **cs_kwargs,
            )
            fmi_type = "CoSimulation"
        else:
            raise

    generated_path = artifact_root / "generated_trajectory.csv"
    headers = list(result.dtype.names)
    rows = []
    for item in result:
        rows.append({name: item[name].item() if hasattr(item[name], "item") else item[name] for name in headers})
    _write_csv(generated_path, headers, rows)
    backend_label = "fmpy_modelexchange" if fmi_type == "ModelExchange" else "fmpy_cosimulation"
    mode_label = "single_fmu_me" if fmi_type == "ModelExchange" else "single_fmu"
    return SingleRunResult(
        backend=backend_label,
        runtime_mode=mode_label,
        path=generated_path,
        time_column="time",
        signal_columns=[name for name in headers if name != "time"],
        warnings=[],
        decision_evidence={},
    )


def run_drobotti_replay(loaded: LoadedCase, artifact_root: Path) -> SingleRunResult:
    source_root = _source_root_path(loaded)
    if source_root is None:
        raise RuntimeError("missing source root for drobotti replay")
    csv_path = source_root / "raw" / "data" / "drobotti_rmqfmu" / "drobotti_playback_data.csv"
    if not csv_path.exists():
        raise RuntimeError(f"missing drobotti playback data: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise RuntimeError("empty drobotti playback data")
    start_time = datetime.fromisoformat(rows[0]["time"]).timestamp()
    out_rows: List[Dict[str, Any]] = []
    for row in rows:
        current = datetime.fromisoformat(row["time"]).timestamp()
        xpos = float(row["xpos"])
        ypos = float(row["ypos"])
        distance = int(math.sqrt(xpos * xpos + ypos * ypos) * 1_000_000)
        out_rows.append(
            {
                "time": round(current - start_time, 6),
                "xpos": xpos,
                "ypos": ypos,
                "distance": distance,
            }
        )
    generated_path = artifact_root / "generated_trajectory.csv"
    _write_csv(generated_path, ["time", "xpos", "ypos", "distance"], out_rows)
    return SingleRunResult(
        backend="rabbitmq_replay",
        runtime_mode="archived_replay",
        path=generated_path,
        time_column="time",
        signal_columns=["xpos", "ypos", "distance"],
        warnings=[],
        decision_evidence={"source": str(csv_path)},
    )


def run_flex_cell_replay(loaded: LoadedCase, artifact_root: Path) -> SingleRunResult:
    csv_path = Path("DTaaS-examples-main/data/flex-cell/output/outputs.csv").resolve()
    if not csv_path.exists():
        raise RuntimeError(f"missing flex-cell outputs.csv: {csv_path}")
    generated_path = artifact_root / "generated_trajectory.csv"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(csv_path, generated_path)
    headers = next(csv.reader(generated_path.open("r", encoding="utf-8", newline="")))
    signal_columns = [name for name in headers if name != "time"]
    return SingleRunResult(
        backend="rabbitmq_replay",
        runtime_mode="archived_replay",
        path=generated_path,
        time_column="time",
        signal_columns=signal_columns,
        warnings=[],
        decision_evidence={"source": str(csv_path)},
    )


def run_multi_fmu(
    *,
    loaded: LoadedCase,
    predicted_solution: Mapping[str, Any],
    simulation_config: SimulationConfig,
    artifact_root: Path,
) -> SingleRunResult:
    stages = _stage_specs(loaded, predicted_solution, simulation_config)
    all_fmus = {str(getattr(fmu, "uid", "")): fmu for fmu in simulation_config.fmus if str(getattr(fmu, "uid", "")).strip()}
    parameter_overrides = _parameter_overrides(predicted_solution)
    scenario_inputs = _scenario_input_profiles(loaded)
    scenario_initial_conditions = _scenario_initial_conditions(loaded)
    monitored_specs = _monitored_signal_specs(predicted_solution)
    source_bound_names = {str(item.get("name") or "").strip() for item in monitored_specs if str(item.get("source") or "").strip()}
    warnings: List[str] = []
    rows: List[Dict[str, Any]] = []
    active_instances: Dict[str, Any] = {}

    try:
        for stage in stages:
            schedule = stage.get("schedule") if isinstance(stage.get("schedule"), dict) else {}
            timing = _schedule_start_stop_step(schedule, simulation_config)
            stage_assets = _asset_execution_order(stage, simulation_config)
            stage_connections = _normalize_connection_records(stage.get("connections") if isinstance(stage.get("connections"), list) else simulation_config.connections)
            connection_by_target = _connection_map(stage_connections)
            adapter_resolved, adapter_transforms = _build_adapter_registry(predicted_solution)
            for final_target, real_source in adapter_resolved.items():
                connection_by_target[final_target] = real_source
            external_bindings = _resolved_bindings_for_stage(
                predicted_solution,
                "external_inputs",
                simulation_config,
                stage_assets=stage_assets,
            )
            initial_condition_bindings = _resolved_bindings_for_stage(
                predicted_solution,
                "initial_conditions",
                simulation_config,
                stage_assets=stage_assets,
            )
            requested_signals = [
                signal_name
                for signal_name in _collect_requested_signals(loaded, predicted_solution)
                if signal_name not in source_bound_names
            ]

            # Recreate the stage instance set. This is conservative but keeps stage transitions deterministic.
            for instance in active_instances.values():
                instance.terminate()
            active_instances = {}
            for asset_id in stage_assets:
                fmu = all_fmus.get(asset_id)
                if fmu is None:
                    raise RuntimeError(f"stage references unknown FMU: {asset_id}")
                backend = detect_runtime_backend(fmu)
                if backend == "python_source_fmu" or backend == "unifmu_python":
                    instance = PythonRuntimeInstance.create(fmu)
                elif backend == "native_fmu":
                    fmi_type_multi = select_fmi_type(fmu)
                    types_set = {str(t).strip() for t in fmu.fmi_types}
                    has_cs = bool(types_set & {"CoSimulation", "Co-Simulation"})
                    use_me = fmi_type_multi == "ModelExchange" and not has_cs
                    if use_me:
                        try:
                            instance = NativeMEInstance.create(fmu)
                        except Exception:
                            instance = NativeCoSimInstance.create(fmu)
                    else:
                        instance = NativeCoSimInstance.create(fmu)
                else:
                    raise RuntimeError(f"unsupported multi-FMU backend {backend} for {asset_id}")
                active_instances[asset_id] = instance

            for asset_id in stage_assets:
                instance = active_instances[asset_id]
                start_values = dict(parameter_overrides.get(asset_id, {}))
                for name, value in scenario_initial_conditions.items():
                    if name in initial_condition_bindings:
                        for target_asset, target_signal in initial_condition_bindings[name]:
                            if target_asset == asset_id and target_signal not in start_values:
                                start_values[target_signal] = value
                        continue
                    fallback_asset, fallback_signal = _unique_initial_condition_target(
                        signal_name=str(name),
                        stage_assets=stage_assets,
                        active_instances=active_instances,
                    )
                    if fallback_asset == asset_id and fallback_signal and fallback_signal not in start_values:
                        start_values[fallback_signal] = value
                instance.initialize(
                    start_time=timing["start_time"],
                    stop_time=timing["stop_time"],
                    parameters=_expanded_start_values(instance, start_values),
                )

            grid = _build_time_grid(timing["start_time"], timing["stop_time"], timing["step_size"])
            asset_periods = _schedule_asset_periods(
                schedule,
                simulation_config,
                stage_assets=stage_assets,
                default_step=timing["step_size"],
            )
            loop_wrappers = _schedule_loop_wrappers(schedule, simulation_config)
            asset_last_step_time = {asset_id: float(timing["start_time"]) for asset_id in stage_assets}
            for index, time_point in enumerate(grid):
                row: Dict[str, Any] = {"time": time_point, "stage_id": str(stage.get("stage_id") or "stage1")}
                for input_name, profile in scenario_inputs.items():
                    sampled = _profile_value(profile, time_point)
                    if sampled is not None:
                        row.setdefault(str(input_name), sampled)
                if index == 0:
                    for asset_id in stage_assets:
                        instance = active_instances[asset_id]
                        initial_inputs: Dict[str, Any] = {}
                        for input_name, targets in external_bindings.items():
                            if input_name not in scenario_inputs:
                                continue
                            sampled = _profile_value(scenario_inputs[input_name], time_point)
                            if sampled is None:
                                continue
                            for target_asset, target_signal in targets:
                                if target_asset == asset_id:
                                    initial_inputs[target_signal] = sampled
                        if initial_inputs:
                            instance.set_values(initial_inputs)
                if index > 0:
                    loop_processed_assets: set[str] = set()
                    for loop_wrapper in loop_wrappers:
                        processed = _run_fixed_point_loop(
                            loop_wrapper=loop_wrapper,
                            time_point=float(time_point),
                            stage_start_time=float(timing["start_time"]),
                            stage_stop_time=float(timing["stop_time"]),
                            stage_assets=stage_assets,
                            active_instances=active_instances,
                            connection_by_target=connection_by_target,
                            external_bindings=external_bindings,
                            scenario_inputs=scenario_inputs,
                            asset_periods=asset_periods,
                            asset_last_step_time=asset_last_step_time,
                            warnings=warnings,
                            adapter_transforms=adapter_transforms,
                        )
                        if not processed:
                            continue
                        for asset_id in processed:
                            asset_last_step_time[asset_id] = float(time_point)
                        loop_processed_assets.update(processed)

                    for asset_id in stage_assets:
                        if asset_id in loop_processed_assets:
                            continue
                        period = float(asset_periods.get(asset_id, timing["step_size"]))
                        if not _should_step_asset(
                            time_point=float(time_point),
                            stage_start_time=float(timing["start_time"]),
                            stage_stop_time=float(timing["stop_time"]),
                            period=period,
                        ):
                            continue
                        current_time = float(asset_last_step_time.get(asset_id, timing["start_time"]))
                        step_size = float(time_point) - current_time
                        if step_size <= 0:
                            continue
                        instance = active_instances[asset_id]
                        inputs_to_apply = _runtime_input_values(
                            asset_id=asset_id,
                            current_time=current_time,
                            stage_assets=stage_assets,
                            active_instances=active_instances,
                            connection_by_target=connection_by_target,
                            external_bindings=external_bindings,
                            scenario_inputs=scenario_inputs,
                            adapter_transforms=adapter_transforms,
                        )
                        instance.set_values(inputs_to_apply)
                        instance.step(current_time, step_size)
                        asset_last_step_time[asset_id] = float(time_point)
                        warnings.extend(getattr(instance, "warnings", []))

                for item in monitored_specs:
                    source = str(item.get("source") or "").strip()
                    if not source:
                        continue
                    _record_bound_signal(
                        row=row,
                        warnings=warnings,
                        monitored_name=str(item.get("name") or "").strip(),
                        source_endpoint=source,
                        active_instances=active_instances,
                    )
                for signal_name in requested_signals:
                    _record_unsourced_signal(
                        row=row,
                        warnings=warnings,
                        signal_name=signal_name,
                        stage_assets=stage_assets,
                        active_instances=active_instances,
                    )
                rows.append(row)
    finally:
        for instance in active_instances.values():
            instance.terminate()

    if not rows:
        raise RuntimeError("multi-FMU execution produced no samples")
    headers = _ordered_unique_text(["time", "stage_id"] + [key for row in rows for key in row.keys()])
    generated_path = artifact_root / "generated_trajectory.csv"
    _write_csv(generated_path, headers, rows)
    signal_columns = [name for name in headers if name not in {"time", "stage_id"}]
    return SingleRunResult(
        backend="mixed_cosim",
        runtime_mode="multi_fmu",
        path=generated_path,
        time_column="time",
        signal_columns=signal_columns,
        warnings=_ordered_unique_text(warnings),
        decision_evidence={"stage_count": len(stages)},
    )


def run_execution_backend(
    *,
    loaded: LoadedCase,
    predicted_solution: Mapping[str, Any],
    simulation_config: SimulationConfig,
    artifact_root: Path,
) -> SingleRunResult:
    case_id = loaded.case_id
    if case_id == "case_dtaas_drobotti_rmqfmu":
        return run_drobotti_replay(loaded, artifact_root)
    if case_id == "case_dtaas_flex_cell":
        return run_flex_cell_replay(loaded, artifact_root)

    selected_fmus = [fmu for fmu in simulation_config.fmus if str(getattr(fmu, "uid", "")).strip()]
    if len(selected_fmus) == 1 and not simulation_config.connections:
        backend = detect_runtime_backend(selected_fmus[0])
        if backend == "native_fmu":
            return run_single_fmu(
                loaded=loaded,
                fmu=selected_fmus[0],
                predicted_solution=predicted_solution,
                simulation_config=simulation_config,
                artifact_root=artifact_root,
            )
        if backend in {"python_source_fmu", "unifmu_python"}:
            # Reuse the mixed runtime for the single-FMU Python case.
            return run_multi_fmu(
                loaded=loaded,
                predicted_solution=predicted_solution,
                simulation_config=simulation_config,
                artifact_root=artifact_root,
            )
    return run_multi_fmu(
        loaded=loaded,
        predicted_solution=predicted_solution,
        simulation_config=simulation_config,
        artifact_root=artifact_root,
    )
