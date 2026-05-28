"""Build the file-based FMU library consumed by pipeline Stage 2."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any, Dict, List

from dataset.common import read_json, write_json


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    shutil.copy2(src.resolve(), dst)


def build(*, dataset_root: Path, library_root: Path) -> Dict[str, Any]:
    assets_root = dataset_root / "assets"
    library_assets_root = library_root / "assets"
    if library_root.exists():
        shutil.rmtree(library_root)
    library_assets_root.mkdir(parents=True, exist_ok=True)

    manifest_assets: List[Dict[str, Any]] = []
    for asset_dir in sorted(path for path in assets_root.iterdir() if path.is_dir()):
        asset_json = asset_dir / "asset.json"
        if not asset_json.exists():
            continue
        asset_payload = read_json(asset_json)
        if not bool(asset_payload.get("library_visible", True)):
            continue
        target_dir = library_assets_root / asset_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in ("asset.json", "metadata.json", "description.md", "model.fmu", "ref.csv", "input.csv", "simopt.json"):
            src = asset_dir / name
            if src.exists() or src.is_symlink():
                _copy_file(src, target_dir / name)
        manifest_assets.append(
            {
                "asset_id": asset_payload["asset_id"],
                "name": asset_payload["name"],
                "relative_dir": f"assets/{asset_dir.name}",
                "fmu_file": "model.fmu",
                "asset_file": "asset.json",
                "metadata_file": "metadata.json",
                "description_file": "description.md",
                "tags": asset_payload.get("tags", []),
                "source_type": asset_payload.get("source_type"),
            }
        )

    manifest = {
        "schema": "UNIFIED_LIBRARY_MANIFEST_V1",
        "version": 1,
        "asset_count": len(manifest_assets),
        "assets": manifest_assets,
    }
    write_json(library_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.build_pipeline_library")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument("--library-root", default="pipeline/resources/fmu_library", help="Output library root.")
    args = parser.parse_args()
    manifest = build(dataset_root=Path(args.dataset_root).resolve(), library_root=Path(args.library_root).resolve())
    print({"asset_count": manifest["asset_count"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
