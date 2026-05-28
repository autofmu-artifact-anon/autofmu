"""Re-score numerical fidelity for all cases in existing experiment directories.

Reads the existing generated_trajectory.csv and reference data for each case,
re-runs score_numerical_fidelity with the current scoring code (including
missing-signal penalties), and updates metrics.json + experiment_summary.json.

Usage:
    python3 -m evaluator.rescore_numerical --experiment-root <dir> [--experiment-root <dir2> ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .reference import build_reference_pack
from .scoring import score_numerical_fidelity

from pipeline.dataset_loader import load_case


def _rescore_case(case_dir: Path, dataset_root: Path) -> Optional[Dict[str, Any]]:
    metrics_path = case_dir / "metrics.json"
    if not metrics_path.exists():
        return None

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    case_id = case_dir.name
    case_root = dataset_root / "cases" / case_id
    if not case_root.exists():
        return None

    try:
        loaded = load_case(case_root)
    except Exception:
        return None

    ref = build_reference_pack(loaded)

    # Use the *dataset* truth (not stale metrics) to decide supportability.
    if not ref.supports_numerical_fidelity:
        return None

    gen_path = case_dir / "generated_trajectory.csv"
    if not gen_path.exists():
        return None

    execution_result = {"generated_trajectory_path": str(gen_path)}
    new_nf = score_numerical_fidelity(execution_result, ref)

    metrics["numerical_fidelity"] = new_nf
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_nf


def _update_experiment_summary(experiment_root: Path) -> None:
    summary_path = experiment_root / "experiment_summary.json"
    if not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    case_rows = summary.get("case_rows") or []

    case_dir_map: Dict[str, Path] = {}
    for d in experiment_root.iterdir():
        if d.is_dir() and d.name.startswith("case_"):
            case_dir_map[d.name] = d

    updated = 0
    for row in case_rows:
        case_id = str(row.get("case_id") or "").strip()
        case_dir = case_dir_map.get(case_id)
        if case_dir is None:
            continue
        metrics_path = case_dir / "metrics.json"
        if not metrics_path.exists():
            continue
        new_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        row_metrics = row.get("metrics") or {}
        row_metrics["numerical_fidelity"] = new_metrics.get("numerical_fidelity") or {}
        row["metrics"] = row_metrics
        updated += 1

    summary["case_rows"] = case_rows
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  Updated {updated} case rows in experiment_summary.json")


def rescore_experiment(experiment_root: Path, dataset_root: Path) -> Dict[str, int]:
    stats = {"total": 0, "rescored": 0, "skipped": 0, "errors": 0}
    for case_dir in sorted(experiment_root.iterdir()):
        if not case_dir.is_dir() or not case_dir.name.startswith("case_"):
            continue
        stats["total"] += 1
        try:
            result = _rescore_case(case_dir, dataset_root)
            if result is not None:
                stats["rescored"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            stats["errors"] += 1
            print(f"  ERROR {case_dir.name}: {exc}")

    _update_experiment_summary(experiment_root)
    return stats


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Re-score numerical fidelity for existing experiments.")
    parser.add_argument("--experiment-root", action="append", required=True)
    parser.add_argument("--dataset-root", default="dataset")
    args = parser.parse_args(argv)

    dataset_root = Path(args.dataset_root).expanduser().resolve()
    for root_str in args.experiment_root:
        root = Path(root_str).expanduser().resolve()
        print(f"Rescoring: {root.name}")
        stats = rescore_experiment(root, dataset_root)
        print(f"  total={stats['total']} rescored={stats['rescored']} skipped={stats['skipped']} errors={stats['errors']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
