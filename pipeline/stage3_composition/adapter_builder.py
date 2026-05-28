"""Adapter FMU builder retained on the supported Stage 3 module path."""

from __future__ import annotations

import json
import logging
import subprocess
import textwrap
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AdapterVariable:
    name: str
    causality: str  # input|output|parameter
    fmi_type: str = "Real"


@dataclass(frozen=True)
class AdapterOperation:
    kind: str  # identity|rename|derived|constant|unmapped|unsupported
    params: Dict[str, Any]


@dataclass(frozen=True)
class AdapterSpec:
    adapter_id: str
    model_name: str
    source_fmus: List[Dict[str, str]]
    variables: List[AdapterVariable]
    mappings: List[Dict[str, Any]]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "model_name": self.model_name,
            "source_fmus": self.source_fmus,
            "variables": [{"name": v.name, "causality": v.causality, "fmi_type": v.fmi_type} for v in self.variables],
            "mappings": self.mappings,
            "notes": self.notes,
        }


_ZIP_EPOCH_DT = (1980, 1, 1, 0, 0, 0)


def _safe_name(raw: str) -> str:
    keep = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-", "."}:
            keep.append(ch)
        else:
            keep.append("_")
    cleaned = "".join(keep).strip("_.")
    return cleaned or "adapter"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _deterministic_guid(spec: AdapterSpec) -> str:
    payload = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mbse_val.adapter::{payload}"))


def _render_model_description(*, model_name: str, guid: str, variables: List[AdapterVariable]) -> str:
    # Minimal FMI 2.0 modelDescription.xml (Co-Simulation) for artifact packaging.
    def _scalar(var: AdapterVariable, vr: int) -> str:
        causality = var.causality
        variability = "continuous" if causality in {"input", "output"} else "fixed"
        return (
            f'    <ScalarVariable name="{var.name}" valueReference="{vr}" causality="{causality}" variability="{variability}">\n'
            f"      <{var.fmi_type} />\n"
            f"    </ScalarVariable>"
        )

    vars_xml = "\n".join(_scalar(v, idx + 1) for idx, v in enumerate(variables))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<fmiModelDescription fmiVersion="2.0" modelName="{model_name}" guid="{guid}" generationTool="mbse_val.pipeline">\n'
        f'  <CoSimulation modelIdentifier="{model_name}" canHandleVariableCommunicationStepSize="true" />\n'
        "  <ModelVariables>\n"
        f"{vars_xml}\n"
        "  </ModelVariables>\n"
        "</fmiModelDescription>\n"
    )


def _render_glue_py(spec: AdapterSpec) -> str:
    header = (
        '"""Auto-generated adapter glue for MBSE pipeline.\n\n'
        "This adapter describes interface mappings between the SysML-required variables\n"
        "and one or more selected FMUs.\n"
        '"""\n'
    )
    return (
        f"{header}\n"
        "from __future__ import annotations\n\n"
        "from typing import Any, Dict, List\n\n\n"
        f"ADAPTER_ID = {spec.adapter_id!r}\n"
        f"MODEL_NAME = {spec.model_name!r}\n"
        f"SOURCE_FMUS = {spec.source_fmus!r}\n"
        f"VARIABLES = {[(v.name, v.causality, v.fmi_type) for v in spec.variables]!r}\n\n"
        f"INPUT_VARIABLES = {[v.name for v in spec.variables if v.causality == 'input']!r}\n"
        f"OUTPUT_VARIABLES = {[v.name for v in spec.variables if v.causality == 'output']!r}\n\n"
        f"MAPPINGS: list[dict[str, Any]] = {spec.mappings!r}\n\n\n"
        "def _scalar(value: Any) -> float:\n"
        "    if isinstance(value, (list, tuple)):\n"
        "        return float(value[0]) if value else 0.0\n"
        "    return float(value)\n\n\n"
        "def _as_list(value: Any) -> List[float]:\n"
        "    if isinstance(value, (list, tuple)):\n"
        "        return [float(item) for item in value]\n"
        "    return [float(value)]\n\n\n"
        "def _mapping_key(value: Any) -> str:\n"
        "    if isinstance(value, str):\n"
        "        return value.strip().lower()\n"
        "    numeric = _scalar(value)\n"
        "    if abs(numeric - round(numeric)) <= 1e-9:\n"
        "        return str(int(round(numeric)))\n"
        "    return f'{numeric:.12g}'\n\n\n"
        "def _channel_index(name: str) -> int:\n"
        "    raw = str(name or '').strip()\n"
        "    if not raw:\n"
        "        return 0\n"
        "    if '_' not in raw:\n"
        "        return 0\n"
        "    suffix = raw.rsplit('_', 1)[-1]\n"
        "    return int(suffix) if suffix.isdigit() else 0\n\n\n"
        "def _transform_output_count(params: Dict[str, Any]) -> int:\n"
        "    target_dims = params.get('target_dimensions') or params.get('target_dimension') or []\n"
        "    if isinstance(target_dims, (int, float)):\n"
        "        target_dims = [int(target_dims)]\n"
        "    count = 1\n"
        "    for dim in target_dims if isinstance(target_dims, list) else []:\n"
        "        try:\n"
        "            numeric = int(dim)\n"
        "        except (TypeError, ValueError):\n"
        "            continue\n"
        "        if numeric > 0:\n"
        "            count *= numeric\n"
        "    return max(count, 1)\n\n\n"
        "def _resolve_input_value(inputs: Dict[str, Any], *, sysml_name: str, target_name: str) -> Any:\n"
        "    if target_name in inputs:\n"
        "        return inputs[target_name]\n"
        "    if sysml_name in inputs:\n"
        "        value = inputs[sysml_name]\n"
        "        if isinstance(value, (list, tuple)):\n"
        "            idx = _channel_index(target_name)\n"
        "            if 0 <= idx < len(value):\n"
        "                return value[idx]\n"
        "        return value\n"
        "    if len(inputs) == 1:\n"
        "        return next(iter(inputs.values()))\n"
        "    return None\n\n\n"
        "def _select_transform_payload(inputs: Dict[str, float], raw_inputs: Dict[str, Any]) -> Any:\n"
        "    if INPUT_VARIABLES:\n"
        "        values = [inputs[name] for name in INPUT_VARIABLES if name in inputs]\n"
        "        if len(values) > 1:\n"
        "            return values\n"
        "        if len(values) == 1:\n"
        "            return values[0]\n"
        "    if inputs:\n"
        "        values = list(inputs.values())\n"
        "        return values if len(values) > 1 else values[0]\n"
        "    if raw_inputs:\n"
        "        values = list(raw_inputs.values())\n"
        "        return values if len(values) > 1 else values[0]\n"
        "    return 0.0\n\n\n"
        "def _apply_transform(value: Any, params: Dict[str, Any]) -> float | List[float]:\n"
        "    kind = str(params.get('transform_kind') or params.get('mode') or 'pass_through').strip().lower()\n"
        "    if kind == 'unit_transform':\n"
        "        scale = float(params.get('scale', 1.0) or 1.0)\n"
        "        offset = float(params.get('offset', 0.0) or 0.0)\n"
        "        return _scalar(value) * scale + offset\n"
        "    if kind == 'mode_signal':\n"
        "        mapping = params.get('mapping') or {}\n"
        "        key = _mapping_key(value)\n"
        "        if key in mapping:\n"
        "            return float(mapping[key])\n"
        "        return float(mapping.get('default', 0.0))\n"
        "    if kind == 'type_cast':\n"
        "        target_type = str(params.get('target_type') or '').strip().lower()\n"
        "        raw = _scalar(value)\n"
        "        if target_type == 'boolean':\n"
        "            return 1.0 if raw >= 0.5 else 0.0\n"
        "        if target_type == 'integer':\n"
        "            return float(int(round(raw)))\n"
        "        return raw\n"
        "    if kind == 'dimension_transform':\n"
        "        values = _as_list(value)\n"
        "        target_count = _transform_output_count(params)\n"
        "        if target_count <= 1:\n"
        "            return float(values[0]) if values else 0.0\n"
        "        if not values:\n"
        "            return [0.0 for _ in range(target_count)]\n"
        "        payload = list(values[:target_count])\n"
        "        while len(payload) < target_count:\n"
        "            payload.append(float(payload[-1]))\n"
        "        return [float(item) for item in payload]\n"
        "    if isinstance(value, (list, tuple)):\n"
        "        payload = _as_list(value)\n"
        "        return payload if len(payload) > 1 else float(payload[0])\n"
        "    return _scalar(value)\n\n\n"
        "def _distribute_outputs(value: Any, output_names: List[str]) -> Dict[str, float]:\n"
        "    if not output_names:\n"
        "        return {}\n"
        "    if isinstance(value, list):\n"
        "        result: Dict[str, float] = {}\n"
        "        for index, name in enumerate(output_names):\n"
        "            chosen = value[index] if index < len(value) else value[-1]\n"
        "            result[name] = float(chosen)\n"
        "        return result\n"
        "    scalar = float(value)\n"
        "    return {name: scalar for name in output_names}\n\n\n"
        "def map_sysml_to_fmu(inputs: Dict[str, Any]) -> Dict[str, float]:\n"
        '    """Apply inbound mappings (SysML inputs -> FMU inputs)."""\n'
        "    out: Dict[str, float] = {}\n"
        "    for mapping in MAPPINGS:\n"
        "        if mapping.get('direction') != 'in':\n"
        "            continue\n"
        "        sysml = mapping.get('sysml') or {}\n"
        "        target = mapping.get('target') or {}\n"
        "        op = mapping.get('op') or {}\n"
        "        sysml_name = sysml.get('name')\n"
        "        target_name = target.get('name')\n"
        "        kind = op.get('kind')\n"
        "        if kind == 'constant':\n"
        "            if target_name:\n"
        "                out[target_name] = float(op.get('value', 0.0))\n"
        "            continue\n"
        "        if not sysml_name or not target_name:\n"
        "            continue\n"
        "        raw_value = _resolve_input_value(inputs, sysml_name=sysml_name, target_name=target_name)\n"
        "        if raw_value is None:\n"
        "            continue\n"
        "        if kind in {'identity', 'rename', 'derived'}:\n"
        "            out[target_name] = _scalar(raw_value)\n"
        "    return out\n\n\n"
        "def map_fmu_to_sysml(outputs: Dict[str, float]) -> Dict[str, float]:\n"
        '    """Apply outbound mappings (FMU outputs -> SysML outputs)."""\n'
        "    out: Dict[str, float] = {}\n"
        "    for mapping in MAPPINGS:\n"
        "        if mapping.get('direction') != 'out':\n"
        "            continue\n"
        "        sysml = mapping.get('sysml') or {}\n"
        "        source = mapping.get('source') or {}\n"
        "        op = mapping.get('op') or {}\n"
        "        sysml_name = sysml.get('name')\n"
        "        source_name = source.get('name')\n"
        "        kind = op.get('kind')\n"
        "        params = op.get('params') or {}\n"
        "        if kind == 'constant':\n"
        "            if sysml_name:\n"
        "                out[sysml_name] = float(op.get('value', 0.0))\n"
        "            continue\n"
        "        if not sysml_name or not source_name:\n"
        "            continue\n"
        "        if kind in {'identity', 'rename', 'derived'}:\n"
        "            if source_name in outputs:\n"
        "                out[sysml_name] = _apply_transform(outputs[source_name], params)\n"
        "    return out\n\n\n"
        "def evaluate_adapter(inputs: Dict[str, Any]) -> Dict[str, float]:\n"
        '    """Evaluate the adapter as a simple input->output transform."""\n'
        "    inbound = map_sysml_to_fmu(inputs)\n"
        "    outbound_mapping = next((mapping for mapping in MAPPINGS if mapping.get('direction') == 'out'), None) or {}\n"
        "    op = outbound_mapping.get('op') or {}\n"
        "    payload = _select_transform_payload(inbound, inputs)\n"
        "    transformed = _apply_transform(payload, op.get('params') or {})\n"
        "    output_names = OUTPUT_VARIABLES or [str((outbound_mapping.get('source') or {}).get('name') or 'output')]\n"
        "    return _distribute_outputs(transformed, output_names)\n"
    )


def _render_fmi2_stub_c(*, model_name: str, variables: List[AdapterVariable], mappings: List[Dict[str, Any]]) -> str:
    constants: Dict[str, float] = {}
    for mapping in mappings:
        if (mapping.get("direction") or "").lower() != "out":
            continue
        op = mapping.get("op") or {}
        if (op.get("kind") or "").lower() != "constant":
            continue
        sysml = mapping.get("sysml") or {}
        name = sysml.get("name")
        if isinstance(name, str) and name:
            value = op.get("value", 0.0)
            if isinstance(value, (int, float)):
                constants[name] = float(value)

    constant_lines: List[str] = []
    for idx, var in enumerate(variables):
        if var.causality != "output":
            continue
        if var.name in constants:
            constant_lines.append(f"  comp->real_values[{idx}] = {constants[var.name]:.17g};")
    input_indices = [idx for idx, var in enumerate(variables) if var.causality == "input"]
    output_indices = [idx for idx, var in enumerate(variables) if var.causality == "output"]
    transform = _extract_transform_params(mappings)
    transform_lines = _render_transform_c_lines(input_indices=input_indices, output_indices=output_indices, transform=transform)
    body_lines = constant_lines + transform_lines
    body = "\n".join(body_lines) if body_lines else "  (void)comp;"

    return textwrap.dedent(
        f"""\
        // Auto-generated FMI 2.0 Co-Simulation stub for adapter FMU.
        // Model: {model_name}
        //
        // This stub is intentionally minimal and Real-only.
        // It applies scalar adapter transforms and pins constant-mapped outputs when present.

        #include <stddef.h>
        #include <stdlib.h>
        #include <string.h>

        typedef const char* fmi2String;
        typedef double fmi2Real;
        typedef int fmi2Integer;
        typedef int fmi2Boolean;
        typedef unsigned int fmi2ValueReference;
        typedef unsigned char fmi2Byte;
        typedef void* fmi2Component;
        typedef void* fmi2ComponentEnvironment;
        typedef void* fmi2FMUstate;

        typedef enum {{
          fmi2OK = 0,
          fmi2Warning = 1,
          fmi2Discard = 2,
          fmi2Error = 3,
          fmi2Fatal = 4,
          fmi2Pending = 5
        }} fmi2Status;

        typedef enum {{
          fmi2ModelExchange = 0,
          fmi2CoSimulation = 1
        }} fmi2Type;

        typedef struct {{
          void (*logger)(fmi2ComponentEnvironment env, fmi2String instanceName, fmi2Status status, fmi2String category, fmi2String message, ...);
          void* (*allocateMemory)(size_t nobj, size_t size);
          void (*freeMemory)(void* obj);
          void (*stepFinished)(fmi2ComponentEnvironment env, fmi2Status status);
          fmi2ComponentEnvironment componentEnvironment;
        }} fmi2CallbackFunctions;

        typedef struct {{
          fmi2CallbackFunctions cb;
          fmi2Real real_values[{len(variables)}];
        }} AdapterComponent;

        static void* _alloc(const fmi2CallbackFunctions* cb, size_t bytes) {{
          if (cb && cb->allocateMemory) {{
            return cb->allocateMemory(1, bytes);
          }}
          return calloc(1, bytes);
        }}

        static void _free(const fmi2CallbackFunctions* cb, void* ptr) {{
          if (!ptr) return;
          if (cb && cb->freeMemory) {{
            cb->freeMemory(ptr);
            return;
          }}
          free(ptr);
        }}

        const char* fmi2GetTypesPlatform(void) {{ return "default"; }}
        const char* fmi2GetVersion(void) {{ return "2.0"; }}

        fmi2Component fmi2Instantiate(
          fmi2String instanceName,
          fmi2Type fmuType,
          fmi2String fmuGUID,
          fmi2String fmuResourceLocation,
          const fmi2CallbackFunctions* functions,
          fmi2Boolean visible,
          fmi2Boolean loggingOn
        ) {{
          (void)instanceName;
          (void)fmuType;
          (void)fmuGUID;
          (void)fmuResourceLocation;
          (void)visible;
          (void)loggingOn;

          AdapterComponent* comp = (AdapterComponent*)_alloc(functions, sizeof(AdapterComponent));
          if (!comp) return NULL;
          if (functions) {{
            memcpy(&comp->cb, functions, sizeof(fmi2CallbackFunctions));
          }} else {{
            memset(&comp->cb, 0, sizeof(fmi2CallbackFunctions));
          }}
          memset(comp->real_values, 0, sizeof(comp->real_values));
          return (fmi2Component)comp;
        }}

        void fmi2FreeInstance(fmi2Component c) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return;
          _free(&comp->cb, comp);
        }}

        fmi2Status fmi2SetDebugLogging(fmi2Component c, fmi2Boolean loggingOn, size_t nCategories, const fmi2String categories[]) {{
          (void)c;
          (void)loggingOn;
          (void)nCategories;
          (void)categories;
          return fmi2OK;
        }}

        fmi2Status fmi2SetupExperiment(fmi2Component c, fmi2Boolean toleranceDefined, fmi2Real tolerance, fmi2Real startTime, fmi2Boolean stopTimeDefined, fmi2Real stopTime) {{
          (void)c;
          (void)toleranceDefined;
          (void)tolerance;
          (void)startTime;
          (void)stopTimeDefined;
          (void)stopTime;
          return fmi2OK;
        }}

        fmi2Status fmi2EnterInitializationMode(fmi2Component c) {{ (void)c; return fmi2OK; }}
        fmi2Status fmi2ExitInitializationMode(fmi2Component c) {{ (void)c; return fmi2OK; }}
        fmi2Status fmi2Terminate(fmi2Component c) {{ (void)c; return fmi2OK; }}

        fmi2Status fmi2Reset(fmi2Component c) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          memset(comp->real_values, 0, sizeof(comp->real_values));
          return fmi2OK;
        }}

        fmi2Status fmi2GetReal(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, fmi2Real value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            value[i] = comp->real_values[ref - 1];
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2GetInteger(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, fmi2Integer value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            value[i] = (fmi2Integer)comp->real_values[ref - 1];
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2GetBoolean(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, fmi2Boolean value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            value[i] = comp->real_values[ref - 1] >= 0.5 ? 1 : 0;
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2GetString(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, fmi2String value[]) {{
          (void)c;
          (void)vr;
          for (size_t i = 0; i < nvr; i++) {{
            value[i] = "";
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2SetReal(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, const fmi2Real value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            comp->real_values[ref - 1] = value[i];
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2SetInteger(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, const fmi2Integer value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            comp->real_values[ref - 1] = (fmi2Real)value[i];
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2SetBoolean(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, const fmi2Boolean value[]) {{
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
          for (size_t i = 0; i < nvr; i++) {{
            unsigned int ref = vr[i];
            if (ref == 0 || ref > {len(variables)}) return fmi2Error;
            comp->real_values[ref - 1] = value[i] ? 1.0 : 0.0;
          }}
          return fmi2OK;
        }}

        fmi2Status fmi2SetString(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, const fmi2String value[]) {{
          (void)c;
          (void)vr;
          (void)nvr;
          (void)value;
          return fmi2OK;
        }}

        fmi2Status fmi2DoStep(
          fmi2Component c,
          fmi2Real currentCommunicationPoint,
          fmi2Real communicationStepSize,
          fmi2Boolean noSetFMUStatePriorToCurrentPoint
        ) {{
          (void)currentCommunicationPoint;
          (void)communicationStepSize;
          (void)noSetFMUStatePriorToCurrentPoint;
          AdapterComponent* comp = (AdapterComponent*)c;
          if (!comp) return fmi2Error;
        {body}
          return fmi2OK;
        }}

        // Optional functions commonly touched by runtimes (best-effort defaults).
        fmi2Status fmi2CancelStep(fmi2Component c) {{ (void)c; return fmi2OK; }}
        fmi2Status fmi2GetStatus(fmi2Component c, int s, fmi2Status* value) {{ (void)c; (void)s; (void)value; return fmi2Discard; }}
        fmi2Status fmi2GetRealStatus(fmi2Component c, int s, fmi2Real* value) {{ (void)c; (void)s; (void)value; return fmi2Discard; }}
        fmi2Status fmi2GetIntegerStatus(fmi2Component c, int s, fmi2Integer* value) {{ (void)c; (void)s; (void)value; return fmi2Discard; }}
        fmi2Status fmi2GetBooleanStatus(fmi2Component c, int s, fmi2Boolean* value) {{ (void)c; (void)s; (void)value; return fmi2Discard; }}
        fmi2Status fmi2GetStringStatus(fmi2Component c, int s, fmi2String* value) {{ (void)c; (void)s; (void)value; return fmi2Discard; }}
        fmi2Status fmi2GetFMUstate(fmi2Component c, fmi2FMUstate* state) {{
          (void)c;
          if (state) *state = NULL;
          return fmi2Error;
        }}
        fmi2Status fmi2SetFMUstate(fmi2Component c, fmi2FMUstate state) {{
          (void)c;
          (void)state;
          return fmi2Error;
        }}
        fmi2Status fmi2FreeFMUstate(fmi2Component c, fmi2FMUstate* state) {{
          (void)c;
          if (state) *state = NULL;
          return fmi2OK;
        }}
        fmi2Status fmi2SerializedFMUstateSize(fmi2Component c, fmi2FMUstate state, size_t* size) {{
          (void)c;
          (void)state;
          if (size) *size = 0u;
          return fmi2Error;
        }}
        fmi2Status fmi2SerializeFMUstate(fmi2Component c, fmi2FMUstate state, fmi2Byte serializedState[], size_t size) {{
          (void)c;
          (void)state;
          (void)serializedState;
          (void)size;
          return fmi2Error;
        }}
        fmi2Status fmi2DeSerializeFMUstate(fmi2Component c, const fmi2Byte serializedState[], size_t size, fmi2FMUstate* state) {{
          (void)c;
          (void)serializedState;
          (void)size;
          if (state) *state = NULL;
          return fmi2Error;
        }}
        fmi2Status fmi2GetDirectionalDerivative(
          fmi2Component c,
          const fmi2ValueReference unknowns[],
          size_t nUnknowns,
          const fmi2ValueReference knowns[],
          size_t nKnowns,
          const fmi2Real dvKnown[],
          fmi2Real dvUnknown[]
        ) {{
          (void)c;
          (void)unknowns;
          (void)nUnknowns;
          (void)knowns;
          (void)nKnowns;
          (void)dvKnown;
          (void)dvUnknown;
          return fmi2Error;
        }}
        fmi2Status fmi2SetRealInputDerivatives(
          fmi2Component c,
          const fmi2ValueReference vr[],
          size_t nvr,
          const fmi2Integer order[],
          const fmi2Real value[]
        ) {{
          (void)c;
          (void)vr;
          (void)nvr;
          (void)order;
          (void)value;
          return fmi2Error;
        }}
        fmi2Status fmi2GetRealOutputDerivatives(
          fmi2Component c,
          const fmi2ValueReference vr[],
          size_t nvr,
          const fmi2Integer order[],
          fmi2Real value[]
        ) {{
          (void)c;
          (void)vr;
          (void)nvr;
          (void)order;
          (void)value;
          return fmi2Error;
        }}
        """
    )


def _extract_transform_params(mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
    for mapping in mappings:
        if (mapping.get("direction") or "").lower() != "out":
            continue
        op = mapping.get("op") or {}
        if (op.get("kind") or "").lower() == "constant":
            continue
        params = op.get("params")
        if isinstance(params, dict):
            return dict(params)
    return {"transform_kind": "pass_through"}


def _render_transform_c_lines(*, input_indices: List[int], output_indices: List[int], transform: Dict[str, Any]) -> List[str]:
    if not input_indices or not output_indices:
        return []
    kind = str(transform.get("transform_kind") or transform.get("mode") or "pass_through").strip().lower()
    input_idx = input_indices[0]
    default_lines: List[str] = []
    if kind == "unit_transform":
        scale = float(transform.get("scale", 1.0) or 1.0)
        offset = float(transform.get("offset", 0.0) or 0.0)
        default_lines = [
            f"  double adapter_input = comp->real_values[{input_idx}];",
            f"  double adapter_output = adapter_input * {scale:.17g} + {offset:.17g};",
        ]
    elif kind == "type_cast":
        target_type = str(transform.get("target_type") or "").strip().lower()
        default_lines = [f"  double adapter_input = comp->real_values[{input_idx}];"]
        if target_type == "boolean":
            default_lines.append("  double adapter_output = adapter_input >= 0.5 ? 1.0 : 0.0;")
        elif target_type == "integer":
            default_lines.append(
                "  double adapter_output = adapter_input >= 0.0 ? (double)((int)(adapter_input + 0.5)) : (double)((int)(adapter_input - 0.5));"
            )
        else:
            default_lines.append("  double adapter_output = adapter_input;")
    elif kind == "mode_signal":
        mapping = transform.get("mapping") if isinstance(transform.get("mapping"), dict) else {}
        true_value = float(mapping.get("true", mapping.get("1", 1.0)) or 1.0)
        false_value = float(mapping.get("false", mapping.get("0", 0.0)) or 0.0)
        default_lines = [
            f"  double adapter_input = comp->real_values[{input_idx}];",
            f"  double adapter_output = adapter_input >= 0.5 ? {true_value:.17g} : {false_value:.17g};",
        ]
    elif kind == "dimension_transform":
        default_lines = []
        for output_pos, output_idx in enumerate(output_indices):
            source_idx = input_indices[min(output_pos, len(input_indices) - 1)]
            default_lines.append(f"  comp->real_values[{output_idx}] = comp->real_values[{source_idx}];")
        return default_lines
    else:
        default_lines = [
            f"  double adapter_input = comp->real_values[{input_idx}];",
            "  double adapter_output = adapter_input;",
        ]
    for output_idx in output_indices:
        default_lines.append(f"  comp->real_values[{output_idx}] = adapter_output;")
    return default_lines


def _write_zip_entry(zf: zipfile.ZipFile, *, arcname: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(filename=arcname, date_time=_ZIP_EPOCH_DT)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3  # Unix
    info.external_attr = (mode & 0xFFFF) << 16
    zf.writestr(info, data)


@dataclass(frozen=True)
class AdapterBuildResult:
    adapter_id: str
    adapter_dir: Path
    glue_py: Path
    synthesis_json: Path
    model_description_xml: Path
    fmu_path: Path

    def to_dict(self) -> Dict[str, str]:
        return {
            "adapter_id": str(self.adapter_id),
            "adapter_dir": str(self.adapter_dir),
            "glue_py": str(self.glue_py),
            "synthesis_json": str(self.synthesis_json),
            "model_description_xml": str(self.model_description_xml),
            "fmu_path": str(self.fmu_path),
        }


class AdapterFmuBuilder:
    def __init__(self, *, logger: logging.Logger) -> None:
        self.logger = logger

    def build(self, *, run_root: Path, spec: AdapterSpec) -> AdapterBuildResult:
        adapter_root = run_root / "AdapterFMUs"
        adapter_root.mkdir(parents=True, exist_ok=True)
        adapter_dir = adapter_root / _safe_name(spec.adapter_id)
        adapter_dir.mkdir(parents=True, exist_ok=True)

        glue_py = adapter_dir / "glue.py"
        synthesis_json = adapter_dir / "synthesis.json"
        model_description_xml = adapter_dir / "modelDescription.xml"
        fmu_path = adapter_root / f"{_safe_name(spec.adapter_id)}.fmu"

        _write_text(glue_py, _render_glue_py(spec))
        _write_json(
            synthesis_json,
            {
                "adapter_id": spec.adapter_id,
                "model_name": spec.model_name,
                "operators_used": sorted({(m.get("op") or {}).get("kind", "unknown") for m in spec.mappings}),
                "variables": [{"name": v.name, "causality": v.causality, "fmi_type": v.fmi_type} for v in spec.variables],
                "source_fmus": spec.source_fmus,
                "mappings": spec.mappings,
                "notes": spec.notes,
            },
        )

        safe_model_name = _safe_name(spec.model_name)
        guid = _deterministic_guid(spec)
        _write_text(model_description_xml, _render_model_description(model_name=safe_model_name, guid=guid, variables=spec.variables))

        sources_dir = adapter_dir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        c_path = sources_dir / "adapter_fmu.c"
        _write_text(
            c_path,
            _render_fmi2_stub_c(model_name=safe_model_name, variables=spec.variables, mappings=spec.mappings),
        )

        binary_path: Optional[Path] = None
        try:
            binaries_dir = adapter_dir / "binaries" / "linux64"
            binaries_dir.mkdir(parents=True, exist_ok=True)
            binary_path = binaries_dir / f"{safe_model_name}.so"
            subprocess.run(
                ["gcc", "-shared", "-fPIC", "-O2", "-o", str(binary_path), str(c_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "Adapter FMU binary build failed (sources-only package) | adapter_id=%s | error=%s",
                spec.adapter_id,
                exc,
            )
            binary_path = None

        # Package to FMU (zip) after generating glue code.
        with zipfile.ZipFile(fmu_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            _write_zip_entry(zf, arcname="modelDescription.xml", data=model_description_xml.read_bytes(), mode=0o644)
            _write_zip_entry(zf, arcname="resources/glue.py", data=glue_py.read_bytes(), mode=0o644)
            _write_zip_entry(zf, arcname="resources/synthesis.json", data=synthesis_json.read_bytes(), mode=0o644)
            _write_zip_entry(zf, arcname="sources/adapter_fmu.c", data=c_path.read_bytes(), mode=0o644)
            if binary_path and binary_path.exists():
                _write_zip_entry(
                    zf,
                    arcname=f"binaries/linux64/{safe_model_name}.so",
                    data=binary_path.read_bytes(),
                    mode=0o755,
                )

        self.logger.info(
            "Adapter FMU created | adapter_id=%s | fmu=%s | binaries=%s",
            spec.adapter_id,
            fmu_path,
            "linux64" if (binary_path and binary_path.exists()) else "none",
        )
        return AdapterBuildResult(
            adapter_id=spec.adapter_id,
            adapter_dir=adapter_dir,
            glue_py=glue_py,
            synthesis_json=synthesis_json,
            model_description_xml=model_description_xml,
            fmu_path=fmu_path,
        )
