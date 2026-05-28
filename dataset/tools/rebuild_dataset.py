"""End-to-end rebuild for the unified dataset and pipeline FMU library."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Optional

from dataset.tools.build_pipeline_library import build as build_library
from dataset.tools.migrate_benchmark_to_dataset import migrate as migrate_benchmark
from dataset.tools.migrate_cases_to_dataset import migrate as migrate_cases
from dataset.tools.migrate_dtaas_examples_to_dataset import migrate as migrate_dtaas_examples
from dataset.tools.validate_dataset import validate as validate_dataset


def rebuild(*, dataset_root: Path, library_root: Path, examples_root: Optional[Path] = None) -> None:
    for folder in (dataset_root / "assets", dataset_root / "cases", dataset_root / "indexes", dataset_root / "manifests"):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

    migrate_benchmark(dataset_root=dataset_root)
    migrate_cases(dataset_root=dataset_root)
    migrate_dtaas_examples(dataset_root=dataset_root, examples_root=examples_root)
    validate_dataset(dataset_root=dataset_root)
    build_library(dataset_root=dataset_root, library_root=library_root)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m dataset.tools.rebuild_dataset")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument("--library-root", default="pipeline/resources/fmu_library", help="Output library root.")
    parser.add_argument("--examples-root", default=None, help="DTaaS examples root.")
    args = parser.parse_args()
    dataset_root = Path(args.dataset_root).resolve()
    library_root = Path(args.library_root).resolve()
    examples_root = Path(args.examples_root).resolve() if args.examples_root else None
    rebuild(dataset_root=dataset_root, library_root=library_root, examples_root=examples_root)
    print(
        {
            "dataset_root": str(dataset_root),
            "library_root": str(library_root),
            "examples_root": str(examples_root) if examples_root else None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
