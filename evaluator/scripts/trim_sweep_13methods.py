#!/usr/bin/env python3
"""Trim-ratio sweep for the latest 13-method batch.

Outputs Decision Acc, Exec Succ, MAE, RMSE, NRMSE for Simple and Complex
at trim ratios: 0.5%, 1%, 1.5%, 2%, 2.5%, 3%.

Usage (from experiments/):
    python3 evaluator/scripts/trim_sweep_13methods.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

RUNS_DIR = Path("evaluator/runs")
BATCH_PREFIX = "all13_rerun_20260318T154216Z"
DATASET_ROOT = Path("dataset")
# Align with evaluator.scoring.NRMSE_REPORTING_CAP: cap per-case NRMSE so aggregate is in [0, 2]
NRMSE_REPORTING_CAP = 2.0

EXPERIMENT_SUFFIXES = [
    "current_pipeline",
    "baseline_b1_rule_sequential",
    "baseline_b2_llm_retrieval_rule",
    "baseline_b3_graph_aware",
    "ablation_stage1_top1_llm",
    "ablation_stage1_rule_template",
    "ablation_stage1_heuristic_neighborhood",
    "ablation_stage2_semantic_retrieval_only",
    "ablation_stage2_graph_match_only",
    "ablation_stage2_greedy_hybrid",
    "ablation_stage3_static_rule_scheduler",
    "ablation_stage3_greedy_multirate",
    "ablation_stage3_llm_generated_script",
]

METHOD_LABELS = {
    "current_pipeline": "COMPASS",
    "baseline_b1_rule_sequential": "B1: Rule Pipeline",
    "baseline_b2_llm_retrieval_rule": "B2: Semantic-Only",
    "baseline_b3_graph_aware": "B3: Graph-Aware",
    "ablation_stage1_top1_llm": "Top-1 LLM Decomposition",
    "ablation_stage1_rule_template": "Rule Template Decomposition",
    "ablation_stage1_heuristic_neighborhood": "Heuristic Neighborhood",
    "ablation_stage2_semantic_retrieval_only": "Semantic Retrieval Only",
    "ablation_stage2_graph_match_only": "Graph Match Only",
    "ablation_stage2_greedy_hybrid": "Greedy Hybrid",
    "ablation_stage3_static_rule_scheduler": "Static Rule Scheduler",
    "ablation_stage3_greedy_multirate": "Greedy Multirate",
    "ablation_stage3_llm_generated_script": "LLM-Generated Script",
}


def _load_case_category_map() -> Dict[str, str]:
    cat_map = {}
    cases_dir = DATASET_ROOT / "cases"
    if not cases_dir.exists():
        return cat_map
    for d in cases_dir.iterdir():
        if not d.is_dir():
            continue
        cj = d / "case.json"
        if cj.exists():
            c = json.loads(cj.read_text(encoding="utf-8"))
            cat_map[c.get("case_id", d.name)] = c.get("case_category", "unknown")
    return cat_map


def _is_finite(x: Any) -> bool:
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def _load_all_experiments() -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """Returns (aligned_case_ids, method_case_rows)."""
    aligned: List[str] | None = None
    method_rows: Dict[str, List[Dict[str, Any]]] = {}

    for suffix in EXPERIMENT_SUFFIXES:
        exp_dir = RUNS_DIR / f"{BATCH_PREFIX}_{suffix}"
        if not exp_dir.exists():
            exp_dir = RUNS_DIR / suffix
        summary_path = exp_dir / "experiment_summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        case_rows = summary.get("case_rows") or []
        case_ids = [str(r.get("case_id") or "").strip() for r in case_rows if str(r.get("case_id") or "").strip()]
        if aligned is None:
            aligned = case_ids
        else:
            aligned = sorted(set(aligned) & set(case_ids))
        method_rows[suffix] = {r["case_id"]: r for r in case_rows}

    return aligned or [], method_rows


def _casewise_max_penalties(
    rows_per_method: Dict[str, Dict[str, Any]],
    aligned_case_ids: List[str],
) -> Dict[str, Dict[str, float]]:
    """per case_id: { 'mae': max, 'rmse': max, 'nrmse': max } across methods."""
    penalties: Dict[str, Dict[str, float]] = {}
    for case_id in aligned_case_ids:
        for rows in rows_per_method.values():
            row = rows.get(case_id) if isinstance(rows, dict) else None
            if not row:
                continue
            nf = (row.get("metrics") or {}).get("numerical_fidelity") or {}
            for key in ("mae", "rmse", "nrmse"):
                v = nf.get(key)
                if not _is_finite(v):
                    continue
                fv = float(v)
                if case_id not in penalties:
                    penalties[case_id] = {}
                if key not in penalties[case_id] or fv > penalties[case_id][key]:
                    penalties[case_id][key] = fv
    return penalties


def _trimmed_mean(values: List[float], trim_ratio: float) -> float:
    if not values:
        return float("nan")
    n = len(values)
    k = min(n - 1, max(0, int(math.ceil(n * trim_ratio))))
    sorted_v = sorted(values)
    trimmed = sorted_v[: n - k] if k > 0 else sorted_v
    return sum(trimmed) / len(trimmed)


def _method_metrics_for_scope(
    method_rows: Dict[str, Dict[str, Any]],
    aligned_case_ids: List[str],
    scope_case_ids: List[str],
    penalties: Dict[str, Dict[str, float]],
    trim_ratio: float,
) -> Dict[str, float]:
    """Returns decision_acc, exec_succ, mae, rmse, nrmse for one method in one scope."""
    scope_set = set(scope_case_ids)
    case_ids = [c for c in aligned_case_ids if c in scope_set]
    if not case_ids:
        return {"decision_acc": float("nan"), "exec_succ": float("nan"), "mae": float("nan"), "rmse": float("nan"), "nrmse": float("nan")}

    decision_correct = []
    exec_success = []
    mae_vals = []
    rmse_vals = []
    nrmse_vals = []

    for cid in case_ids:
        row = method_rows.get(cid)
        if not row:
            continue
        metrics = row.get("metrics") or {}
        # Decision: use penalty = 0 (wrong) if missing
        dec = metrics.get("decision") or {}
        if dec.get("supported") and "correct" in dec:
            decision_correct.append(1.0 if dec.get("correct") else 0.0)
        else:
            decision_correct.append(0.0)

        # Execution success
        ex = metrics.get("execution") or {}
        if ex.get("supported") and "success" in ex:
            exec_success.append(1.0 if ex.get("success") else 0.0)
        else:
            exec_success.append(0.0)

        # Numerical (with penalty)
        nf = metrics.get("numerical_fidelity") or {}
        pen = penalties.get(cid) or {}
        mae = nf.get("mae") if _is_finite(nf.get("mae")) else pen.get("mae")
        rmse = nf.get("rmse") if _is_finite(nf.get("rmse")) else pen.get("rmse")
        nrmse = nf.get("nrmse") if _is_finite(nf.get("nrmse")) else pen.get("nrmse")
        if _is_finite(mae):
            mae_vals.append((cid, float(mae)))
        if _is_finite(rmse):
            rmse_vals.append((cid, float(rmse)))
        if _is_finite(nrmse):
            nrmse_vals.append((cid, float(nrmse)))

    # Only include cases that have numerical penalty (so we can fill missing)
    numerical_case_ids = [c for c in case_ids if c in penalties and set(penalties[c].keys()) >= {"mae", "rmse", "nrmse"}]
    mae_filled = []
    rmse_filled = []
    nrmse_filled = []
    for cid in numerical_case_ids:
        row = method_rows.get(cid)
        nf = (row.get("metrics") or {}).get("numerical_fidelity") or {} if row else {}
        pen = penalties.get(cid) or {}
        mae_filled.append(float(nf.get("mae")) if _is_finite(nf.get("mae")) else pen.get("mae", float("nan")))
        rmse_filled.append(float(nf.get("rmse")) if _is_finite(nf.get("rmse")) else pen.get("rmse", float("nan")))
        raw_nrmse = float(nf.get("nrmse")) if _is_finite(nf.get("nrmse")) else pen.get("nrmse", float("nan"))
        nrmse_filled.append(min(raw_nrmse, NRMSE_REPORTING_CAP) if _is_finite(raw_nrmse) else raw_nrmse)

    return {
        "decision_acc": sum(decision_correct) / len(decision_correct) if decision_correct else float("nan"),
        "exec_succ": sum(exec_success) / len(exec_success) if exec_success else float("nan"),
        "mae": _trimmed_mean(mae_filled, trim_ratio) if mae_filled else float("nan"),
        "rmse": _trimmed_mean(rmse_filled, trim_ratio) if rmse_filled else float("nan"),
        "nrmse": _trimmed_mean(nrmse_filled, trim_ratio) if nrmse_filled else float("nan"),
    }


def _fmt(v: float, w: int = 10) -> str:
    if math.isnan(v):
        return "N/A".rjust(w)
    if abs(v) > 1e6:
        return f"{v:.2e}".rjust(w)
    if abs(v) >= 100:
        return f"{v:.2f}".rjust(w)
    return f"{v:.4f}".rjust(w)


def main() -> None:
    cat_map = _load_case_category_map()
    aligned, method_rows = _load_all_experiments()
    simple_ids = sorted(c for c in aligned if cat_map.get(c) == "simple")
    complex_ids = sorted(c for c in aligned if cat_map.get(c) == "complex")

    # method_rows is keyed by suffix; we need dict of case_id -> row per method
    by_method: Dict[str, Dict[str, Any]] = {}
    for suffix in EXPERIMENT_SUFFIXES:
        if suffix in method_rows:
            by_method[suffix] = method_rows[suffix]

    rows_per_method = by_method
    penalties = _casewise_max_penalties(rows_per_method, aligned)

    trim_ratios = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]

    for tr in trim_ratios:
        pct = tr * 100
        print("=" * 140)
        print(f"Trim = {pct}%  (Simple n={len(simple_ids)}, Complex n={len(complex_ids)})")
        print("=" * 140)

        for scope_name, scope_ids in [("Simple", simple_ids), ("Complex", complex_ids)]:
            print(f"\n--- {scope_name} ---")
            h = f"{'Method':<32} {'DecAcc%':>9} {'ExSucc%':>9} {'MAE':>12} {'RMSE':>12} {'NRMSE':>10}"
            print(h)
            print("-" * 90)
            for suffix in EXPERIMENT_SUFFIXES:
                rows = rows_per_method.get(suffix)
                if not rows:
                    continue
                m = _method_metrics_for_scope(rows, aligned, scope_ids, penalties, tr)
                label = METHOD_LABELS.get(suffix, suffix)
                print(f"{label:<32} {_fmt(m['decision_acc']*100, 9)} {_fmt(m['exec_succ']*100, 9)} {_fmt(m['mae'], 12)} {_fmt(m['rmse'], 12)} {_fmt(m['nrmse'], 10)}")
            print("-" * 90)
        print()

    # Also write CSV per trim ratio
    out_dir = RUNS_DIR / f"{BATCH_PREFIX}_trim_sweep"
    out_dir.mkdir(parents=True, exist_ok=True)
    import csv as csv_module
    for tr in trim_ratios:
        pct = tr * 100
        out_path = out_dir / f"metrics_trim_{pct}pct.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv_module.writer(f)
            w.writerow(["Scope", "Method", "Decision_Acc%", "Exec_Succ%", "MAE", "RMSE", "NRMSE"])
            for scope_name, scope_ids in [("Simple", simple_ids), ("Complex", complex_ids)]:
                for suffix in EXPERIMENT_SUFFIXES:
                    rows = rows_per_method.get(suffix)
                    if not rows:
                        continue
                    m = _method_metrics_for_scope(rows, aligned, scope_ids, penalties, tr)
                    label = METHOD_LABELS.get(suffix, suffix)
                    w.writerow([
                        scope_name,
                        label,
                        f"{m['decision_acc']*100:.2f}" if not math.isnan(m["decision_acc"]) else "",
                        f"{m['exec_succ']*100:.2f}" if not math.isnan(m["exec_succ"]) else "",
                        f"{m['mae']:.6f}" if not math.isnan(m["mae"]) else "",
                        f"{m['rmse']:.6f}" if not math.isnan(m["rmse"]) else "",
                        f"{m['nrmse']:.6f}" if not math.isnan(m["nrmse"]) else "",
                    ])
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
