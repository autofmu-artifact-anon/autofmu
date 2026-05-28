"""Generate the paper-table CSV from a cross-method summary JSON.

Usage:
    python -m evaluator.gen_paper_table_csv --input <cross_method.json> --output <table.csv>
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

METHOD_ORDER = [
    ("Baselines",                "B1: Rule Pipeline",           "baseline_b1_rule_sequential"),
    ("Baselines",                "B2: Semantic-Only",           "baseline_b2_llm_retrieval_rule"),
    ("Baselines",                "B3: Graph-Aware",             "baseline_b3_graph_aware"),
    ("Requirement Decomposition","Top-1 LLM Decomposition",    "ablation_stage1_top1_llm"),
    ("Requirement Decomposition","Rule Template Decomposition", "ablation_stage1_rule_template"),
    ("Requirement Decomposition","Heuristic Neighborhood",      "ablation_stage1_heuristic_neighborhood"),
    ("Simulation Units Matching","Semantic Retrieval Only",     "ablation_stage2_semantic_retrieval_only"),
    ("Simulation Units Matching","Graph Match Only",            "ablation_stage2_graph_match_only"),
    ("Simulation Units Matching","Greedy Hybrid",               "ablation_stage2_greedy_hybrid"),
    ("Sim. Program Construction","Static Rule Scheduler",       "ablation_stage3_static_rule_scheduler"),
    ("Sim. Program Construction","Greedy Multirate",            "ablation_stage3_greedy_multirate"),
    ("Sim. Program Construction","LLM-Generated Script",        "ablation_stage3_llm_generated_script"),
    ("Ours",                     "COMPASS",                     "current_pipeline"),
]


def _find_experiment(experiments: List[Dict[str, Any]], suffix: str) -> Optional[Dict[str, Any]]:
    for exp in experiments:
        eid = str(exp.get("experiment_id") or "")
        if eid.endswith(suffix):
            return exp
    return None


def _pct(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) * 100:.2f}"


def _flt(value: Any, decimals: int = 4) -> str:
    if value is None:
        return ""
    return f"{float(value):.{decimals}f}"


def _build_rows(data: Dict[str, Any]) -> List[Dict[str, str]]:
    experiments = data.get("experiments") or []
    rows: List[Dict[str, str]] = []

    for category, method_name, suffix in METHOD_ORDER:
        exp = _find_experiment(experiments, suffix)
        if exp is None:
            continue
        cm = exp.get("cross_method_aggregate_metrics") or {}
        bcc = cm.get("by_case_category") or {}
        sim = bcc.get("simple") or {}
        cmp = bcc.get("complex") or {}

        row = {
            "Category": category,
            "Method": method_name,
            # --- Simple ---
            "Simple_Decision_Acc(%)":    _pct(sim.get("decision_accuracy")),
            "Simple_Exec_Succ(%)":       _pct(sim.get("execution_success_rate")),
            "Simple_Exec_Time(s)":       _flt(sim.get("mean_execution_time_seconds"), 4),
            "Simple_MAE":                _flt(sim.get("trimmed_mae"), 4),
            "Simple_RMSE":               _flt(sim.get("trimmed_rmse"), 4),
            "Simple_NRMSE":              _flt(sim.get("trimmed_nrmse"), 4),
            # --- Complex ---
            "Complex_Decision_Acc(%)":   _pct(cmp.get("decision_accuracy")),
            "Complex_Exec_Succ(%)":      _pct(cmp.get("execution_success_rate")),
            "Complex_Exec_Time(s)":      _flt(cmp.get("mean_execution_time_seconds"), 4),
            "Complex_MAE":               _flt(cmp.get("trimmed_mae"), 4),
            "Complex_RMSE":              _flt(cmp.get("trimmed_rmse"), 4),
            "Complex_NRMSE":             _flt(cmp.get("trimmed_nrmse"), 4),
            # --- Overall ---
            "Overall_Decision_Acc(%)":   _pct(cm.get("decision_accuracy")),
            "Overall_Exec_Succ(%)":      _pct(cm.get("execution_success_rate")),
            "Overall_Exec_Time(s)":      _flt(cm.get("mean_execution_time_seconds"), 4),
            "Overall_MAE":               _flt(cm.get("trimmed_mae"), 4),
            "Overall_RMSE":              _flt(cm.get("trimmed_rmse"), 4),
            "Overall_NRMSE":             _flt(cm.get("trimmed_nrmse"), 4),
        }
        rows.append(row)
    return rows


FIELDNAMES = [
    "Category", "Method",
    "Simple_Decision_Acc(%)", "Simple_Exec_Succ(%)", "Simple_Exec_Time(s)",
    "Simple_MAE", "Simple_RMSE", "Simple_NRMSE",
    "Complex_Decision_Acc(%)", "Complex_Exec_Succ(%)", "Complex_Exec_Time(s)",
    "Complex_MAE", "Complex_RMSE", "Complex_NRMSE",
    "Overall_Decision_Acc(%)", "Overall_Exec_Succ(%)", "Overall_Exec_Time(s)",
    "Overall_MAE", "Overall_RMSE", "Overall_NRMSE",
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate paper-table CSV from cross-method JSON.")
    parser.add_argument("--input", required=True, help="Path to cross_method.json")
    parser.add_argument("--output", required=True, help="Output CSV path")
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    rows = _build_rows(data)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
