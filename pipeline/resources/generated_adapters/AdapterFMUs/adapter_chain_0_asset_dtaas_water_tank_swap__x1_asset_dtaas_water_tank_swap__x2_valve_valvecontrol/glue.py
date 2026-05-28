"""Auto-generated adapter glue for MBSE pipeline.

This adapter describes interface mappings between the SysML-required variables
and one or more selected FMUs.
"""

from __future__ import annotations

from typing import Any, Dict, List


ADAPTER_ID = 'adapter_chain_0_asset_dtaas_water_tank_swap__x1_asset_dtaas_water_tank_swap__x2_valve_valvecontrol'
MODEL_NAME = 'adapter_chain_0_asset_dtaas_water_tank_swap__x1_asset_dtaas_water_tank_swap__x2_valve_valvecontrol'
SOURCE_FMUS = [{'name': 'asset_dtaas_water_tank_swap__x1'}, {'name': 'asset_dtaas_water_tank_swap__x2'}]
VARIABLES = [('input', 'input', 'Real'), ('output', 'output', 'Real')]

INPUT_VARIABLES = ['input']
OUTPUT_VARIABLES = ['output']

MAPPINGS: list[dict[str, Any]] = [{'direction': 'in', 'sysml': {'name': 'valve'}, 'target': {'name': 'input'}, 'op': {'kind': 'identity', 'params': {'transform_kind': 'mode_signal', 'source_type': 'boolean', 'target_type': 'real', 'mapping': {'0': 0.0, '1': 1.0, 'false': 0.0, 'true': 1.0}}}}, {'direction': 'out', 'sysml': {'name': 'valvecontrol'}, 'source': {'name': 'output'}, 'op': {'kind': 'derived', 'params': {'transform_kind': 'mode_signal', 'source_type': 'boolean', 'target_type': 'real', 'mapping': {'0': 0.0, '1': 1.0, 'false': 0.0, 'true': 1.0}}}}]


def _scalar(value: Any) -> float:
    if isinstance(value, (list, tuple)):
        return float(value[0]) if value else 0.0
    return float(value)


def _as_list(value: Any) -> List[float]:
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return [float(value)]


def _mapping_key(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    numeric = _scalar(value)
    if abs(numeric - round(numeric)) <= 1e-9:
        return str(int(round(numeric)))
    return f'{numeric:.12g}'


def _channel_index(name: str) -> int:
    raw = str(name or '').strip()
    if not raw:
        return 0
    if '_' not in raw:
        return 0
    suffix = raw.rsplit('_', 1)[-1]
    return int(suffix) if suffix.isdigit() else 0


def _transform_output_count(params: Dict[str, Any]) -> int:
    target_dims = params.get('target_dimensions') or params.get('target_dimension') or []
    if isinstance(target_dims, (int, float)):
        target_dims = [int(target_dims)]
    count = 1
    for dim in target_dims if isinstance(target_dims, list) else []:
        try:
            numeric = int(dim)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            count *= numeric
    return max(count, 1)


def _resolve_input_value(inputs: Dict[str, Any], *, sysml_name: str, target_name: str) -> Any:
    if target_name in inputs:
        return inputs[target_name]
    if sysml_name in inputs:
        value = inputs[sysml_name]
        if isinstance(value, (list, tuple)):
            idx = _channel_index(target_name)
            if 0 <= idx < len(value):
                return value[idx]
        return value
    if len(inputs) == 1:
        return next(iter(inputs.values()))
    return None


def _select_transform_payload(inputs: Dict[str, float], raw_inputs: Dict[str, Any]) -> Any:
    if INPUT_VARIABLES:
        values = [inputs[name] for name in INPUT_VARIABLES if name in inputs]
        if len(values) > 1:
            return values
        if len(values) == 1:
            return values[0]
    if inputs:
        values = list(inputs.values())
        return values if len(values) > 1 else values[0]
    if raw_inputs:
        values = list(raw_inputs.values())
        return values if len(values) > 1 else values[0]
    return 0.0


def _apply_transform(value: Any, params: Dict[str, Any]) -> float | List[float]:
    kind = str(params.get('transform_kind') or params.get('mode') or 'pass_through').strip().lower()
    if kind == 'unit_transform':
        scale = float(params.get('scale', 1.0) or 1.0)
        offset = float(params.get('offset', 0.0) or 0.0)
        return _scalar(value) * scale + offset
    if kind == 'mode_signal':
        mapping = params.get('mapping') or {}
        key = _mapping_key(value)
        if key in mapping:
            return float(mapping[key])
        return float(mapping.get('default', 0.0))
    if kind == 'type_cast':
        target_type = str(params.get('target_type') or '').strip().lower()
        raw = _scalar(value)
        if target_type == 'boolean':
            return 1.0 if raw >= 0.5 else 0.0
        if target_type == 'integer':
            return float(int(round(raw)))
        return raw
    if kind == 'dimension_transform':
        values = _as_list(value)
        target_count = _transform_output_count(params)
        if target_count <= 1:
            return float(values[0]) if values else 0.0
        if not values:
            return [0.0 for _ in range(target_count)]
        payload = list(values[:target_count])
        while len(payload) < target_count:
            payload.append(float(payload[-1]))
        return [float(item) for item in payload]
    if isinstance(value, (list, tuple)):
        payload = _as_list(value)
        return payload if len(payload) > 1 else float(payload[0])
    return _scalar(value)


def _distribute_outputs(value: Any, output_names: List[str]) -> Dict[str, float]:
    if not output_names:
        return {}
    if isinstance(value, list):
        result: Dict[str, float] = {}
        for index, name in enumerate(output_names):
            chosen = value[index] if index < len(value) else value[-1]
            result[name] = float(chosen)
        return result
    scalar = float(value)
    return {name: scalar for name in output_names}


def map_sysml_to_fmu(inputs: Dict[str, Any]) -> Dict[str, float]:
    """Apply inbound mappings (SysML inputs -> FMU inputs)."""
    out: Dict[str, float] = {}
    for mapping in MAPPINGS:
        if mapping.get('direction') != 'in':
            continue
        sysml = mapping.get('sysml') or {}
        target = mapping.get('target') or {}
        op = mapping.get('op') or {}
        sysml_name = sysml.get('name')
        target_name = target.get('name')
        kind = op.get('kind')
        if kind == 'constant':
            if target_name:
                out[target_name] = float(op.get('value', 0.0))
            continue
        if not sysml_name or not target_name:
            continue
        raw_value = _resolve_input_value(inputs, sysml_name=sysml_name, target_name=target_name)
        if raw_value is None:
            continue
        if kind in {'identity', 'rename', 'derived'}:
            out[target_name] = _scalar(raw_value)
    return out


def map_fmu_to_sysml(outputs: Dict[str, float]) -> Dict[str, float]:
    """Apply outbound mappings (FMU outputs -> SysML outputs)."""
    out: Dict[str, float] = {}
    for mapping in MAPPINGS:
        if mapping.get('direction') != 'out':
            continue
        sysml = mapping.get('sysml') or {}
        source = mapping.get('source') or {}
        op = mapping.get('op') or {}
        sysml_name = sysml.get('name')
        source_name = source.get('name')
        kind = op.get('kind')
        params = op.get('params') or {}
        if kind == 'constant':
            if sysml_name:
                out[sysml_name] = float(op.get('value', 0.0))
            continue
        if not sysml_name or not source_name:
            continue
        if kind in {'identity', 'rename', 'derived'}:
            if source_name in outputs:
                out[sysml_name] = _apply_transform(outputs[source_name], params)
    return out


def evaluate_adapter(inputs: Dict[str, Any]) -> Dict[str, float]:
    """Evaluate the adapter as a simple input->output transform."""
    inbound = map_sysml_to_fmu(inputs)
    outbound_mapping = next((mapping for mapping in MAPPINGS if mapping.get('direction') == 'out'), None) or {}
    op = outbound_mapping.get('op') or {}
    payload = _select_transform_payload(inbound, inputs)
    transformed = _apply_transform(payload, op.get('params') or {})
    output_names = OUTPUT_VARIABLES or [str((outbound_mapping.get('source') or {}).get('name') or 'output')]
    return _distribute_outputs(transformed, output_names)
