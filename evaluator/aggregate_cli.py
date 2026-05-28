from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .runner import build_cross_method_summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluator.aggregate_cli")
    parser.add_argument(
        "--experiment-root",
        action="append",
        required=True,
        help="Experiment root directory containing experiment_summary.json. May be repeated.",
    )
    parser.add_argument("--out", default=None, help="Optional JSON output path.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary = build_cross_method_summary(list(args.experiment_root or []))
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
