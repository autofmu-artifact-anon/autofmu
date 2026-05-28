from __future__ import annotations

import argparse
from typing import Optional, Sequence

from .registry import available_bundles
from .runner import run_experiment
from .types import EvaluationSpec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluator.cli")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case-id", action="append", default=None, help="Case id under dataset/cases. May be repeated.")
    group.add_argument("--all-cases", action="store_true", help="Run evaluator for all normalized cases.")
    parser.add_argument("--dataset-root", default="dataset", help="Unified dataset root.")
    parser.add_argument(
        "--manifest-path",
        default="pipeline/resources/fmu_library/manifest.json",
        help="FMU library manifest path.",
    )
    parser.add_argument("--bundle", default="current_pipeline", help="Evaluator method bundle name.")
    parser.add_argument("--out-root", default="evaluator/runs", help="Output root for evaluator artifacts.")
    parser.add_argument("--experiment-id", default=None, help="Optional experiment id.")
    parser.add_argument("--workers", type=int, default=1, help="Reserved evaluator worker count.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=100.0,
        help="Per-case simulation execution timeout in seconds.",
    )
    parser.add_argument("--resume", action="store_true", help="Reuse completed case artifacts under the same experiment id.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first failing case.")
    parser.add_argument(
        "--disable-reference-bootstrap",
        action="store_true",
        help="Skip ground-truth bootstrap overrides in predicted solution assembly.",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Disable stage-2 benchmark_single_fmu and mbse_component_cover fallbacks.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.bundle not in available_bundles():
        parser.error(f"Unknown bundle {args.bundle!r}. Available: {', '.join(available_bundles())}")
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.timeout_seconds is not None and args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be > 0")

    stage2_config: dict = {}
    if args.disable_fallback:
        stage2_config["enable_benchmark_single_fmu_fallback"] = False
        stage2_config["enable_mbse_component_cover_fallback"] = False

    spec = EvaluationSpec(
        dataset_root=args.dataset_root,
        manifest_path=args.manifest_path,
        bundle_name=args.bundle,
        case_ids=[] if args.all_cases else list(args.case_id or []),
        out_root=args.out_root,
        experiment_id=args.experiment_id,
        fail_fast=bool(args.fail_fast),
        workers=int(args.workers),
        timeout_seconds=args.timeout_seconds,
        resume=bool(args.resume),
        stage2_config=stage2_config,
        disable_reference_bootstrap=bool(args.disable_reference_bootstrap),
    )
    summary = run_experiment(spec)
    print(
        {
            "experiment_id": summary.experiment_id,
            "cases_total": summary.cases_total,
            "succeeded": summary.succeeded,
            "failed": summary.failed,
            "output_root": summary.output_root,
        }
    )
    return 0 if summary.failed < summary.cases_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
