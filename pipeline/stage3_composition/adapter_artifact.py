"""Adapter artifact materialization for Stage 3."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from pipeline.types import AdapterSpec

from .adapter_builder import AdapterFmuBuilder, AdapterSpec as BuilderAdapterSpec, AdapterVariable


def _contract_variables(io_contract: Dict[str, object], direction: str) -> List[str]:
    key = "inputs" if direction == "input" else "outputs"
    items = io_contract.get(key) if isinstance(io_contract, dict) else []
    names: List[str] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
    if names:
        return names
    return ["input"] if direction == "input" else ["output"]


def build_adapter_artifact(adapter_spec: AdapterSpec, *, out_dir: Path) -> Dict[str, str]:
    builder = AdapterFmuBuilder(logger=logging.getLogger(__name__))
    source_name = adapter_spec.source.split(".", 1)[-1]
    target_name = adapter_spec.target.split(".", 1)[-1]
    input_vars = _contract_variables(adapter_spec.io_contract, "input")
    output_vars = _contract_variables(adapter_spec.io_contract, "output")
    model_name = adapter_spec.inserted_node_id or adapter_spec.adapter_id
    builder_spec = BuilderAdapterSpec(
        adapter_id=adapter_spec.adapter_id,
        model_name=model_name,
        source_fmus=[{"name": adapter_spec.source.split(".", 1)[0]}, {"name": adapter_spec.target.split(".", 1)[0]}],
        variables=[AdapterVariable(name=name, causality="input", fmi_type="Real") for name in input_vars]
        + [AdapterVariable(name=name, causality="output", fmi_type="Real") for name in output_vars],
        mappings=[
            *[
                {
                    "direction": "in",
                    "sysml": {"name": source_name},
                    "target": {"name": name},
                    "op": {"kind": "identity", "params": adapter_spec.transform},
                }
                for name in input_vars
            ],
            *[
                {
                    "direction": "out",
                    "sysml": {"name": target_name},
                    "source": {"name": name},
                    "op": {"kind": "derived", "params": adapter_spec.transform},
                }
                for name in output_vars
            ],
        ],
        notes=list(adapter_spec.notes),
    )
    built = builder.build(run_root=out_dir, spec=builder_spec)
    return built.to_dict()
