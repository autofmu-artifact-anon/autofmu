"""Execution backends for normalized FMU assets.

This module intentionally avoids new runtime dependencies. It supports:
- native FMI 2.0 Co-Simulation FMUs through `ctypes`
- a minimal FMI 2.0 Model Exchange path for simple single-FMU cases
- Python-backed FMUs bundled as `sources/model.py`
- UniFMU Python models bundled as `resources/model.py`
"""

from __future__ import annotations

import ctypes
import importlib.util
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence
import xml.etree.ElementTree as ET

from pipeline.types import FMU

try:
    from scipy.integrate import solve_ivp
except Exception:  # pragma: no cover - current environment already has scipy
    solve_ivp = None


_LIBC = ctypes.CDLL(None)
_LIBC.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
_LIBC.calloc.restype = ctypes.c_void_p
_LIBC.free.argtypes = [ctypes.c_void_p]
_LIBC.free.restype = None


class Fmi2Status:
    ok = 0
    warning = 1
    discard = 2
    error = 3
    fatal = 4
    pending = 5


@dataclass(frozen=True)
class VariableSpec:
    name: str
    value_reference: int
    type_name: str
    causality: str
    variability: str


@dataclass(frozen=True)
class ModelSpec:
    guid: str
    model_identifier_cs: str
    model_identifier_me: str
    default_start_time: float
    default_stop_time: float
    default_step_size: float
    number_of_event_indicators: int
    number_of_continuous_states: int
    variables: List[VariableSpec]


def infer_backend_kind(fmu: FMU) -> str:
    asset_json = dict((fmu.meta or {}).get("asset_json") or {})
    metadata_json = dict((fmu.meta or {}).get("metadata_json") or {})
    backend_kind = str(
        metadata_json.get("backend_kind")
        or asset_json.get("backend_kind")
        or ""
    ).strip()
    if backend_kind:
        return backend_kind
    fmu_path = Path(str(fmu.path or "")).expanduser().resolve()
    try:
        with zipfile.ZipFile(fmu_path) as archive:
            names = set(archive.namelist())
    except Exception:
        return "native_fmu"
    if "resources/model.py" in names:
        if bool(getattr(fmu.capabilities, "needs_execution_tool", False)) and any("rabbitmq" in name.lower() for name in names):
            return "rabbitmq_bridge_fmu"
        return "unifmu_python"
    if "sources/model.py" in names:
        return "python_source_fmu"
    if any(name.startswith("binaries/linux64/") and name.endswith(".so") for name in names):
        return "native_fmu"
    return "native_fmu"


def load_model_spec(fmu_path: str | Path) -> ModelSpec:
    path = Path(fmu_path).expanduser().resolve()
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("modelDescription.xml")
    root = ET.fromstring(xml_bytes)
    default_experiment = root.find("DefaultExperiment")
    start_time = float((default_experiment.attrib.get("startTime") if default_experiment is not None else 0.0) or 0.0)
    stop_time = float((default_experiment.attrib.get("stopTime") if default_experiment is not None else 1.0) or 1.0)
    step_size = float((default_experiment.attrib.get("stepSize") if default_experiment is not None else 0.0) or 0.0)
    variables: List[VariableSpec] = []
    for node in root.findall("./ModelVariables/ScalarVariable"):
        child = next(iter(list(node)), None)
        type_name = child.tag if child is not None else "Real"
        try:
            vr = int(node.attrib.get("valueReference") or "0")
        except ValueError:
            vr = 0
        variables.append(
            VariableSpec(
                name=str(node.attrib.get("name") or ""),
                value_reference=vr,
                type_name=str(type_name),
                causality=str(node.attrib.get("causality") or "local"),
                variability=str(node.attrib.get("variability") or "continuous"),
            )
        )
    derivatives = root.findall("./ModelStructure/Derivatives/Unknown")
    cs = root.find("CoSimulation")
    me = root.find("ModelExchange")
    return ModelSpec(
        guid=str(root.attrib.get("guid") or ""),
        model_identifier_cs=str(cs.attrib.get("modelIdentifier") if cs is not None else ""),
        model_identifier_me=str(me.attrib.get("modelIdentifier") if me is not None else ""),
        default_start_time=start_time,
        default_stop_time=stop_time,
        default_step_size=step_size,
        number_of_event_indicators=int(root.attrib.get("numberOfEventIndicators") or 0),
        number_of_continuous_states=len(derivatives),
        variables=variables,
    )


def ensure_extracted_fmu(fmu_path: str | Path, *, cache_root: Path) -> Path:
    source = Path(fmu_path).expanduser().resolve()
    target = cache_root / source.stem
    if (target / ".extracted.ok").exists():
        return target
    if target.exists():
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        archive.extractall(target)
    (target / ".extracted.ok").write_text(source.as_posix(), encoding="utf-8")
    return target


def _typed_default(type_name: str) -> Any:
    normalized = type_name.lower()
    if normalized in {"integer", "enumeration"}:
        return 0
    if normalized == "boolean":
        return 0
    if normalized == "string":
        return ""
    return 0.0


def _normalize_scalar(value: Any, type_name: str) -> Any:
    normalized = type_name.lower()
    if normalized in {"integer", "enumeration"}:
        return int(round(float(value)))
    if normalized == "boolean":
        if isinstance(value, str):
            return 1 if value.strip().lower() in {"1", "true", "yes", "on"} else 0
        return 1 if bool(value) else 0
    if normalized == "string":
        return str(value)
    return float(value)


def _variable_maps(model_spec: ModelSpec) -> tuple[Dict[str, VariableSpec], Dict[int, VariableSpec]]:
    by_name = {item.name: item for item in model_spec.variables if item.name}
    by_vr = {item.value_reference: item for item in model_spec.variables}
    return by_name, by_vr


@contextmanager
def _temp_sys_path(*paths: Path) -> Iterator[None]:
    inserts = [path.as_posix() for path in paths if path.exists()]
    original = list(sys.path)
    try:
        for item in reversed(inserts):
            if item not in sys.path:
                sys.path.insert(0, item)
        yield
    finally:
        sys.path[:] = original


def _load_python_module(source_path: Path, *, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {source_path}")
    module = importlib.util.module_from_spec(spec)
    module.Fmi2Status = Fmi2Status
    spec.loader.exec_module(module)
    return module


class PythonModelInstance:
    def __init__(self, *, fmu: FMU, work_root: Path, model_spec: ModelSpec, resource_relpath: str) -> None:
        self.fmu = fmu
        self.model_spec = model_spec
        self._by_name, self._by_vr = _variable_maps(model_spec)
        self.extract_dir = ensure_extracted_fmu(str(fmu.path or ""), cache_root=work_root)
        self.source_path = self.extract_dir / resource_relpath
        module_name = f"runtime_{fmu.uid.replace('-', '_')}"
        search_root = self.source_path.parent
        with _temp_sys_path(search_root, search_root.parent):
            module = _load_python_module(self.source_path, module_name=module_name)
        model_class = getattr(module, "Model", None)
        if model_class is None:
            for value in module.__dict__.values():
                if isinstance(value, type) and any(hasattr(value, attr) for attr in ("do_step", "fmi2DoStep")):
                    model_class = value
                    break
        if model_class is None:
            raise TypeError(f"No runtime model class found in {self.source_path}")
        self.instance = model_class()
        self._style = "fmi2" if hasattr(self.instance, "fmi2DoStep") else "pythonfmu"

    def initialize(self, *, start_time: float, stop_time: float, tolerance: float, initial_values: Mapping[str, Any]) -> None:
        self.set_named_values(initial_values, during_initialization=True)
        if self._style == "fmi2":
            self.instance.fmi2SetupExperiment(start_time, stop_time, tolerance)
            self.instance.fmi2EnterInitializationMode()
            self.instance.fmi2ExitInitializationMode()
        else:
            if hasattr(self.instance, "setup_experiment"):
                self.instance.setup_experiment(start_time=start_time, stop_time=stop_time, tolerance=tolerance)
            if hasattr(self.instance, "enter_initialization_mode"):
                self.instance.enter_initialization_mode()
            if hasattr(self.instance, "exit_initialization_mode"):
                self.instance.exit_initialization_mode()

    def set_named_values(self, values: Mapping[str, Any], *, during_initialization: bool = False) -> None:
        grouped: Dict[str, List[tuple[int, Any]]] = {}
        for name, raw in values.items():
            spec = self._by_name.get(str(name))
            if spec is None:
                continue
            if not during_initialization and spec.causality == "parameter" and spec.variability == "fixed":
                continue
            grouped.setdefault(spec.type_name.lower(), []).append((spec.value_reference, _normalize_scalar(raw, spec.type_name)))
        for type_name, pairs in grouped.items():
            if not pairs:
                continue
            vrs = [vr for vr, _ in pairs]
            typed_values = [value for _, value in pairs]
            if self._style == "fmi2":
                setter = getattr(self.instance, f"fmi2Set{_camel_type(type_name)}", None)
            else:
                setter = getattr(self.instance, f"set_{type_name}", None)
            if setter is None:
                continue
            setter(vrs, typed_values)

    def get_named_values(self, names: Sequence[str]) -> Dict[str, Any]:
        grouped: Dict[str, List[VariableSpec]] = {}
        for name in names:
            spec = self._by_name.get(str(name))
            if spec is None:
                continue
            grouped.setdefault(spec.type_name.lower(), []).append(spec)
        out: Dict[str, Any] = {}
        for type_name, specs in grouped.items():
            if self._style == "fmi2":
                getter = getattr(self.instance, f"fmi2Get{_camel_type(type_name)}", None)
            else:
                getter = getattr(self.instance, f"get_{type_name}", None)
            if getter is None:
                continue
            refs = [spec.value_reference for spec in specs]
            result = getter(refs)
            if self._style == "fmi2":
                _, values = result
            else:
                values = result
            for spec, value in zip(specs, list(values)):
                out[spec.name] = _normalize_scalar(value, spec.type_name)
        return out

    def step(self, *, current_time: float, step_size: float) -> None:
        if self._style == "fmi2":
            self.instance.fmi2DoStep(current_time, step_size, False)
        else:
            self.instance.do_step(current_time, step_size, False)

    def close(self) -> None:
        terminator = getattr(self.instance, "fmi2Terminate", None) or getattr(self.instance, "terminate", None)
        if callable(terminator):
            terminator()


_LOGGER_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p)
_ALLOC_CB = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t)
_FREE_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
_STEP_FINISHED_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)


class _CallbackFunctions(ctypes.Structure):
    _fields_ = [
        ("logger", _LOGGER_CB),
        ("allocateMemory", _ALLOC_CB),
        ("freeMemory", _FREE_CB),
        ("stepFinished", _STEP_FINISHED_CB),
        ("componentEnvironment", ctypes.c_void_p),
    ]


class NativeFmuInstance:
    def __init__(self, *, fmu: FMU, work_root: Path, mode: str) -> None:
        self.fmu = fmu
        self.mode = mode
        self.extract_dir = ensure_extracted_fmu(str(fmu.path or ""), cache_root=work_root)
        self.model_spec = load_model_spec(str(fmu.path or ""))
        self._by_name, self._by_vr = _variable_maps(self.model_spec)
        model_identifier = self.model_spec.model_identifier_cs if mode == "cs" else self.model_spec.model_identifier_me
        if not model_identifier:
            raise ValueError(f"{fmu.uid} does not expose {mode} model identifier")
        self.shared_lib = ctypes.CDLL(str(self.extract_dir / "binaries" / "linux64" / f"{model_identifier}.so"))
        self._callbacks = _CallbackFunctions(
            _LOGGER_CB(lambda *_args: None),
            _ALLOC_CB(lambda nobj, size: _LIBC.calloc(nobj, size)),
            _FREE_CB(lambda pointer: _LIBC.free(pointer)),
            _STEP_FINISHED_CB(lambda *_args: None),
            None,
        )
        self._bind_common()
        self.component = None

    def _bind_common(self) -> None:
        self.shared_lib.fmi2Instantiate.argtypes = [
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(_CallbackFunctions),
            ctypes.c_uint8,
            ctypes.c_uint8,
        ]
        self.shared_lib.fmi2Instantiate.restype = ctypes.c_void_p
        self.shared_lib.fmi2FreeInstance.argtypes = [ctypes.c_void_p]
        self.shared_lib.fmi2SetupExperiment.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_uint8,
            ctypes.c_double,
        ]
        self.shared_lib.fmi2EnterInitializationMode.argtypes = [ctypes.c_void_p]
        self.shared_lib.fmi2ExitInitializationMode.argtypes = [ctypes.c_void_p]
        self.shared_lib.fmi2Terminate.argtypes = [ctypes.c_void_p]
        self.shared_lib.fmi2Reset.argtypes = [ctypes.c_void_p]
        self.shared_lib.fmi2SetReal.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_double)]
        self.shared_lib.fmi2GetReal.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_double)]
        self.shared_lib.fmi2SetInteger.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int)]
        self.shared_lib.fmi2GetInteger.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int)]
        self.shared_lib.fmi2SetBoolean.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int8)]
        self.shared_lib.fmi2GetBoolean.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int8)]
        self.shared_lib.fmi2SetString.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_char_p)]
        self.shared_lib.fmi2GetString.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_char_p)]
        self.shared_lib.fmi2SetTime.argtypes = [ctypes.c_void_p, ctypes.c_double]
        if self.mode == "cs":
            self.shared_lib.fmi2DoStep.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double, ctypes.c_uint8]
        else:
            self.shared_lib.fmi2SetContinuousStates.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
            self.shared_lib.fmi2GetContinuousStates.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
            self.shared_lib.fmi2GetDerivatives.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
            self.shared_lib.fmi2EnterContinuousTimeMode.argtypes = [ctypes.c_void_p]
            self.shared_lib.fmi2CompletedIntegratorStep.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint8,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
            ]
            if hasattr(self.shared_lib, "fmi2GetEventIndicators"):
                self.shared_lib.fmi2GetEventIndicators.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]

    def initialize(self, *, start_time: float, stop_time: float, tolerance: float, initial_values: Mapping[str, Any]) -> None:
        resource_dir = self.extract_dir / "resources"
        resource_uri = resource_dir.resolve().as_uri().encode("utf-8") if resource_dir.exists() else None
        fmu_type = 1 if self.mode == "cs" else 0
        self.component = self.shared_lib.fmi2Instantiate(
            self.fmu.uid.encode("utf-8"),
            fmu_type,
            self.model_spec.guid.encode("utf-8"),
            resource_uri,
            ctypes.byref(self._callbacks),
            0,
            0,
        )
        if not self.component:
            raise RuntimeError(f"fmi2Instantiate failed for {self.fmu.uid}")
        self.shared_lib.fmi2SetupExperiment(self.component, 0, tolerance, start_time, 1, stop_time)
        self.shared_lib.fmi2EnterInitializationMode(self.component)
        self.set_named_values(initial_values, during_initialization=True)
        self.shared_lib.fmi2ExitInitializationMode(self.component)
        if self.mode == "me":
            self.shared_lib.fmi2EnterContinuousTimeMode(self.component)

    def set_named_values(self, values: Mapping[str, Any], *, during_initialization: bool = False) -> None:
        grouped: Dict[str, List[tuple[int, Any]]] = {}
        for name, raw in values.items():
            spec = self._by_name.get(str(name))
            if spec is None:
                continue
            if not during_initialization and spec.causality == "parameter" and spec.variability == "fixed":
                continue
            grouped.setdefault(spec.type_name.lower(), []).append((spec.value_reference, _normalize_scalar(raw, spec.type_name)))
        for type_name, pairs in grouped.items():
            if not pairs:
                continue
            refs = (ctypes.c_uint32 * len(pairs))(*[vr for vr, _ in pairs])
            if type_name in {"integer", "enumeration"}:
                values_buf = (ctypes.c_int * len(pairs))(*[int(value) for _, value in pairs])
                self.shared_lib.fmi2SetInteger(self.component, refs, len(pairs), values_buf)
            elif type_name == "boolean":
                values_buf = (ctypes.c_int8 * len(pairs))(*[int(value) for _, value in pairs])
                self.shared_lib.fmi2SetBoolean(self.component, refs, len(pairs), values_buf)
            elif type_name == "string":
                encoded = [str(value).encode("utf-8") for _, value in pairs]
                values_buf = (ctypes.c_char_p * len(pairs))(*encoded)
                self.shared_lib.fmi2SetString(self.component, refs, len(pairs), values_buf)
            else:
                values_buf = (ctypes.c_double * len(pairs))(*[float(value) for _, value in pairs])
                self.shared_lib.fmi2SetReal(self.component, refs, len(pairs), values_buf)

    def get_named_values(self, names: Sequence[str]) -> Dict[str, Any]:
        grouped: Dict[str, List[VariableSpec]] = {}
        for name in names:
            spec = self._by_name.get(str(name))
            if spec is None:
                continue
            grouped.setdefault(spec.type_name.lower(), []).append(spec)
        out: Dict[str, Any] = {}
        for type_name, specs in grouped.items():
            refs = (ctypes.c_uint32 * len(specs))(*[spec.value_reference for spec in specs])
            if type_name in {"integer", "enumeration"}:
                values = (ctypes.c_int * len(specs))()
                self.shared_lib.fmi2GetInteger(self.component, refs, len(specs), values)
                raw_values = list(values)
            elif type_name == "boolean":
                values = (ctypes.c_int8 * len(specs))()
                self.shared_lib.fmi2GetBoolean(self.component, refs, len(specs), values)
                raw_values = [int(value) for value in values]
            elif type_name == "string":
                values = (ctypes.c_char_p * len(specs))()
                self.shared_lib.fmi2GetString(self.component, refs, len(specs), values)
                raw_values = [value.decode("utf-8") if value else "" for value in values]
            else:
                values = (ctypes.c_double * len(specs))()
                self.shared_lib.fmi2GetReal(self.component, refs, len(specs), values)
                raw_values = list(values)
            for spec, value in zip(specs, raw_values):
                out[spec.name] = _normalize_scalar(value, spec.type_name)
        return out

    def step(self, *, current_time: float, step_size: float) -> None:
        if self.mode == "cs":
            self.shared_lib.fmi2DoStep(self.component, current_time, step_size, 0)
            return
        self._step_me(current_time=current_time, step_size=step_size)

    def _step_me(self, *, current_time: float, step_size: float) -> None:
        state_count = max(int(self.model_spec.number_of_continuous_states), 0)
        if state_count <= 0:
            self.shared_lib.fmi2SetTime(self.component, current_time + step_size)
            enter_event = ctypes.c_uint8(0)
            terminate = ctypes.c_uint8(0)
            self.shared_lib.fmi2CompletedIntegratorStep(self.component, 1, ctypes.byref(enter_event), ctypes.byref(terminate))
            return
        state_buf = (ctypes.c_double * state_count)()
        self.shared_lib.fmi2GetContinuousStates(self.component, state_buf, state_count)
        x0 = [float(item) for item in state_buf]

        def rhs(time_value: float, state: Sequence[float]) -> List[float]:
            self.shared_lib.fmi2SetTime(self.component, time_value)
            x_buf = (ctypes.c_double * state_count)(*list(state))
            self.shared_lib.fmi2SetContinuousStates(self.component, x_buf, state_count)
            dx_buf = (ctypes.c_double * state_count)()
            self.shared_lib.fmi2GetDerivatives(self.component, dx_buf, state_count)
            return [float(item) for item in dx_buf]

        if solve_ivp is None:
            derivatives = rhs(current_time, x0)
            x1 = [x + step_size * dx for x, dx in zip(x0, derivatives)]
        else:
            solution = solve_ivp(rhs, (current_time, current_time + step_size), x0, t_eval=[current_time + step_size], max_step=max(step_size / 8.0, 1e-6))
            if not solution.success:
                raise RuntimeError(f"ModelExchange integration failed for {self.fmu.uid}: {solution.message}")
            x1 = [float(item) for item in solution.y[:, -1]]
        self.shared_lib.fmi2SetTime(self.component, current_time + step_size)
        x_buf = (ctypes.c_double * state_count)(*x1)
        self.shared_lib.fmi2SetContinuousStates(self.component, x_buf, state_count)
        enter_event = ctypes.c_uint8(0)
        terminate = ctypes.c_uint8(0)
        self.shared_lib.fmi2CompletedIntegratorStep(self.component, 1, ctypes.byref(enter_event), ctypes.byref(terminate))

    def close(self) -> None:
        if self.component:
            try:
                self.shared_lib.fmi2Terminate(self.component)
            except Exception:
                pass
            try:
                self.shared_lib.fmi2FreeInstance(self.component)
            except Exception:
                pass
            self.component = None


def build_runtime_instance(fmu: FMU, *, work_root: Path, preferred_mode: str = "") -> Any:
    model_spec = load_model_spec(str(fmu.path or ""))
    backend_kind = infer_backend_kind(fmu)
    if backend_kind == "python_source_fmu":
        return PythonModelInstance(fmu=fmu, work_root=work_root, model_spec=model_spec, resource_relpath="sources/model.py")
    if backend_kind == "unifmu_python":
        return PythonModelInstance(fmu=fmu, work_root=work_root, model_spec=model_spec, resource_relpath="resources/model.py")
    mode = preferred_mode or ""
    if not mode:
        has_cs = any(str(kind) in {"CoSimulation", "Co-Simulation"} for kind in fmu.fmi_types)
        mode = "cs" if has_cs else "me"
    return NativeFmuInstance(fmu=fmu, work_root=work_root, mode=mode)


def default_work_root(prefix: str = "pipeline_runtime_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _camel_type(type_name: str) -> str:
    lowered = str(type_name or "").lower()
    if lowered == "integer":
        return "Integer"
    if lowered == "boolean":
        return "Boolean"
    if lowered == "string":
        return "String"
    if lowered == "enumeration":
        return "Integer"
    return "Real"
