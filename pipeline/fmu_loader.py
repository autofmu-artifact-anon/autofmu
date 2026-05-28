"""Load normalized FMU assets from the file-based library manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from dataset.common import read_json

from .types import FMU, FMUCapabilities, PortMeta


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _capabilities_from_blob(blob: Dict[str, Any]) -> FMUCapabilities:
    return FMUCapabilities(
        needs_execution_tool=bool(blob.get("needs_execution_tool")),
        can_handle_variable_communication_step_size=bool(blob.get("can_handle_variable_communication_step_size", True)),
        can_interpolate_inputs=bool(blob.get("can_interpolate_inputs")),
        can_run_asynchronously=bool(blob.get("can_run_asynchronously")),
        can_be_instantiated_only_once_per_process=bool(blob.get("can_be_instantiated_only_once_per_process")),
        provides_directional_derivatives=bool(blob.get("provides_directional_derivatives")),
        fixed_internal_step_size=blob.get("fixed_internal_step_size"),
    )


def _ports_from_blob(blob: List[Dict[str, Any]]) -> List[PortMeta]:
    ports: List[PortMeta] = []
    for item in blob:
        if not isinstance(item, dict):
            continue
        ports.append(
            PortMeta(
                name=str(item.get("name") or ""),
                causality=str(item.get("causality") or "local"),
                variability=str(item.get("variability") or "continuous"),
                type=str(item.get("type") or "Real"),
                unit=str(item.get("unit") or ""),
                description=str(item.get("description") or ""),
                dimensions=[int(x) for x in item.get("dimensions", [])] if isinstance(item.get("dimensions"), list) else [],
            )
        )
    return ports


def load_fmu_library(manifest_path: str = "pipeline/resources/fmu_library/manifest.json") -> List[FMU]:
    manifest = read_json(_expand(manifest_path))
    manifest_root = _expand(manifest_path).parent
    fmus: List[FMU] = []

    for entry in manifest.get("assets", []) if isinstance(manifest.get("assets"), list) else []:
        if not isinstance(entry, dict):
            continue
        rel_dir = entry.get("relative_dir")
        if not isinstance(rel_dir, str) or not rel_dir:
            continue
        asset_dir = manifest_root / rel_dir
        asset_payload = read_json(asset_dir / str(entry.get("asset_file") or "asset.json"))
        metadata_payload = read_json(asset_dir / str(entry.get("metadata_file") or "metadata.json"))
        ports = _ports_from_blob(metadata_payload.get("ports") if isinstance(metadata_payload.get("ports"), list) else [])
        fmus.append(
            FMU(
                uid=str(asset_payload.get("asset_id") or entry.get("asset_id")),
                name=str(asset_payload.get("name") or entry.get("name") or ""),
                description=str(asset_payload.get("description") or ""),
                path=str((asset_dir / str(entry.get("fmu_file") or "model.fmu")).resolve()),
                fmi_version=str(metadata_payload.get("fmi_version") or asset_payload.get("fmi_version") or "2.0"),
                fmi_types=[str(x) for x in metadata_payload.get("fmi_types", [])] if isinstance(metadata_payload.get("fmi_types"), list) else [],
                ports=ports,
                inputs=[port.name for port in ports if port.causality == "input"],
                outputs=[port.name for port in ports if port.causality == "output"],
                tags=[str(x) for x in asset_payload.get("tags", [])] if isinstance(asset_payload.get("tags"), list) else [],
                capabilities=_capabilities_from_blob(
                    metadata_payload.get("capabilities") if isinstance(metadata_payload.get("capabilities"), dict) else {}
                ),
                meta={
                    "asset_dir": str(asset_dir),
                    "asset_json": asset_payload,
                    "metadata_json": metadata_payload,
                    "default_experiment": metadata_payload.get("default_experiment", {}),
                    "source_type": asset_payload.get("source_type"),
                },
            )
        )

    return fmus
