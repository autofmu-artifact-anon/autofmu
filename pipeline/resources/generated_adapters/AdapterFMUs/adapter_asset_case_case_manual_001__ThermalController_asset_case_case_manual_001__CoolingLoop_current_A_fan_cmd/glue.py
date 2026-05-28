"""Auto-generated adapter glue for MBSE pipeline.

This adapter describes interface mappings between the SysML-required variables
and one or more selected FMUs.
"""

from __future__ import annotations

from typing import Any, Dict


ADAPTER_ID = 'adapter_asset_case_case_manual_001__ThermalController_asset_case_case_manual_001__CoolingLoop_current_A_fan_cmd'
MODEL_NAME = 'adapter_asset_case_case_manual_001__ThermalController_asset_case_case_manual_001__CoolingLoop_current_A_fan_cmd'
SOURCE_FMUS = [{'name': 'asset_case_case_manual_001__ThermalController'}, {'name': 'asset_case_case_manual_001__CoolingLoop'}]
VARIABLES = [('input', 'input', 'Real'), ('output', 'output', 'Real')]

MAPPINGS: list[dict[str, Any]] = [{'direction': 'in', 'sysml': {'name': 'current_A'}, 'target': {'name': 'input'}, 'op': {'kind': 'identity', 'params': {'mode': 'unit_conversion', 'source_unit': 'a', 'target_unit': '1', 'scale': 1.0, 'offset': 0.0}}}, {'direction': 'out', 'sysml': {'name': 'fan_cmd'}, 'source': {'name': 'output'}, 'op': {'kind': 'derived', 'params': {'mode': 'unit_conversion', 'source_unit': 'a', 'target_unit': '1', 'scale': 1.0, 'offset': 0.0}}}]


def map_sysml_to_fmu(inputs: Dict[str, float]) -> Dict[str, float]:
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
        if kind in {'identity', 'rename', 'derived'}:
            if sysml_name in inputs:
                out[target_name] = float(inputs[sysml_name])
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
        if kind == 'constant':
            if sysml_name:
                out[sysml_name] = float(op.get('value', 0.0))
            continue
        if not sysml_name or not source_name:
            continue
        if kind in {'identity', 'rename', 'derived'}:
            if source_name in outputs:
                out[sysml_name] = float(outputs[source_name])
    return out
