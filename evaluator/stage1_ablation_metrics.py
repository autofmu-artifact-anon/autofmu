#!/usr/bin/env python3
"""
Stage 1 Ablation Metrics Aggregator
Computes stage-specific metrics for all 4 Stage 1 variants across all cases.
"""

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUNS_DIR = Path("/root/projects/experiments/evaluator/runs")

VARIANTS = {
    "current_pipeline": "post_fix_20260317T_current_pipeline",
    "top1_llm": "all13_rerun_20260317T060413Z_ablation_stage1_top1_llm",
    "rule_template": "all13_rerun_20260317T060413Z_ablation_stage1_rule_template",
    "heuristic_neighborhood": "all13_rerun_20260317T060413Z_ablation_stage1_heuristic_neighborhood",
}


def safe_mean(lst):
    return statistics.mean(lst) if lst else 0.0


def safe_stdev(lst):
    return statistics.stdev(lst) if len(lst) > 1 else 0.0


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_selected_candidate(stage1_data, stage2_data):
    """Find which candidate from stage1 was selected by stage2."""
    selected_id = stage2_data["task_set"]["task_set_id"]
    for cand in stage1_data:
        if cand.get("task_set_id") == selected_id:
            return cand
    return stage1_data[0] if stage1_data else None


def compute_case_metrics(stage1_data, stage2_data):
    """Compute all Stage 1 metrics for a single case."""
    selected = get_selected_candidate(stage1_data, stage2_data)
    if selected is None:
        return None

    metrics = {}

    # --- A. Candidate Pool Metrics ---
    metrics["num_candidates"] = len(stage1_data)
    all_scores = [c["score"] for c in stage1_data]
    metrics["candidate_score_max"] = max(all_scores)
    metrics["candidate_score_min"] = min(all_scores)
    metrics["candidate_score_spread"] = max(all_scores) - min(all_scores)
    metrics["candidate_score_mean"] = safe_mean(all_scores)

    sources = [c.get("generation_source", "unknown") for c in stage1_data]
    metrics["source_diversity"] = len(set(sources))
    metrics["has_llm_candidate"] = int(any("llm" in s for s in sources))
    metrics["has_rule_candidate"] = int(any("rule" in s for s in sources))

    # --- B. Selected Candidate Score ---
    metrics["selected_score"] = selected["score"]
    sb = selected.get("score_breakdown", {})

    # Unified breakdown keys (current_pipeline uses different keys than ablations)
    metrics["sb_component_coverage"] = sb.get("component_coverage", sb.get("component_ratio", None))
    metrics["sb_signal_coverage"] = sb.get("signal_coverage", sb.get("port_ratio", None))
    metrics["sb_criteria_coverage"] = sb.get("criteria_coverage", sb.get("criteria_bonus", None))
    metrics["sb_constraint_completeness"] = sb.get("constraint_completeness", None)
    metrics["sb_regime_coverage"] = sb.get("regime_coverage", None)
    metrics["sb_topology_alignment"] = sb.get("topology_alignment", None)
    metrics["sb_chain_completeness"] = sb.get("chain_completeness", None)
    metrics["sb_requirement_grounding"] = sb.get("requirement_grounding", None)
    metrics["sb_final_score"] = sb.get("final_score", selected["score"])

    # --- C. Selected Candidate Structure ---
    tasks = selected.get("tasks", [])
    metrics["num_tasks"] = len(tasks)

    total_signals = sum(len(t.get("required_signals", [])) for t in tasks)
    total_specs = sum(len(t.get("signal_specs", [])) for t in tasks)
    total_criteria = sum(len(t.get("acceptance_criteria", [])) for t in tasks)
    total_constraints = sum(len(t.get("constraint_set", [])) for t in tasks)

    metrics["total_required_signals"] = total_signals
    metrics["total_signal_specs"] = total_specs
    metrics["total_acceptance_criteria"] = total_criteria
    metrics["total_constraints"] = total_constraints
    metrics["avg_signals_per_task"] = total_signals / len(tasks) if tasks else 0

    # Acceptance criteria non-empty rate
    nonempty_criteria = 0
    for t in tasks:
        for ac in t.get("acceptance_criteria", []):
            if isinstance(ac, dict):
                has_content = any(
                    v and str(v).strip() and str(v).strip().lower() not in ("", "s", "n/a", "none")
                    for k, v in ac.items()
                    if k not in ("notes",)
                )
                if has_content:
                    nonempty_criteria += 1
            elif ac:
                nonempty_criteria += 1
    metrics["nonempty_criteria_count"] = nonempty_criteria
    metrics["criteria_nonempty_rate"] = nonempty_criteria / total_criteria if total_criteria > 0 else 0

    # Signal specs richness
    specs_with_unit = 0
    specs_with_direction = 0
    specs_with_grounding = 0
    for t in tasks:
        for sp in t.get("signal_specs", []):
            if sp.get("unit_hint"):
                specs_with_unit += 1
            if sp.get("direction"):
                specs_with_direction += 1
            if sp.get("grounded_component_ref") or sp.get("grounded_port_ref"):
                specs_with_grounding += 1
    metrics["specs_with_unit"] = specs_with_unit
    metrics["specs_with_direction"] = specs_with_direction
    metrics["specs_with_grounding"] = specs_with_grounding
    metrics["spec_grounding_rate"] = specs_with_grounding / total_specs if total_specs > 0 else 0

    # --- D. Grounding & Calibration ---
    metrics["grounding_status"] = selected.get("grounding_status", "unknown")
    metrics["is_grounded"] = int(selected.get("grounding_status") == "grounded")

    grounded_components = set()
    grounded_ports = set()
    for t in tasks:
        grounded_components.update(t.get("grounded_components", []))
        grounded_ports.update(t.get("grounded_ports", []))
    metrics["num_grounded_components"] = len(grounded_components)
    metrics["num_grounded_ports"] = len(grounded_ports)

    # p-value and conformal
    metrics["p_value"] = selected.get("p_value", 0)
    ci = selected.get("conformal_info", {})
    metrics["conformal_accepted"] = int(ci.get("accepted", False)) if ci else 0
    metrics["conformal_threshold"] = ci.get("threshold", None)
    metrics["has_conformal"] = int(bool(ci))

    # --- E. Signal Chain Metrics ---
    chains = selected.get("required_signal_chains", [])
    metrics["num_signal_chains"] = len(chains)
    if chains:
        chain_lengths = [len(c) if isinstance(c, list) else 1 for c in chains]
        metrics["avg_chain_length"] = safe_mean(chain_lengths)
        metrics["max_chain_length"] = max(chain_lengths)
    else:
        metrics["avg_chain_length"] = 0
        metrics["max_chain_length"] = 0

    # --- F. Generation Source ---
    metrics["generation_source"] = selected.get("generation_source", "unknown")

    # --- G. Task Diagnostics ---
    diag_grounded_count = 0
    diag_llm_sanitized_count = 0
    for t in tasks:
        diag = t.get("diagnostics", {})
        if diag.get("grounded"):
            diag_grounded_count += 1
        if diag.get("llm_sanitized"):
            diag_llm_sanitized_count += 1
    metrics["task_grounded_rate"] = diag_grounded_count / len(tasks) if tasks else 0
    metrics["task_llm_sanitized_rate"] = diag_llm_sanitized_count / len(tasks) if tasks else 0

    return metrics


def aggregate_metrics(all_case_metrics):
    """Aggregate metrics across all cases for a variant."""
    if not all_case_metrics:
        return {}

    numeric_keys = [
        "num_candidates", "candidate_score_max", "candidate_score_min",
        "candidate_score_spread", "candidate_score_mean",
        "source_diversity", "has_llm_candidate", "has_rule_candidate",
        "selected_score",
        "sb_component_coverage", "sb_signal_coverage", "sb_criteria_coverage",
        "sb_constraint_completeness", "sb_regime_coverage",
        "sb_topology_alignment", "sb_chain_completeness",
        "sb_requirement_grounding", "sb_final_score",
        "num_tasks", "total_required_signals", "total_signal_specs",
        "total_acceptance_criteria", "total_constraints", "avg_signals_per_task",
        "nonempty_criteria_count", "criteria_nonempty_rate",
        "specs_with_unit", "specs_with_direction", "specs_with_grounding",
        "spec_grounding_rate",
        "is_grounded", "num_grounded_components", "num_grounded_ports",
        "p_value", "conformal_accepted", "has_conformal",
        "num_signal_chains", "avg_chain_length", "max_chain_length",
        "task_grounded_rate", "task_llm_sanitized_rate",
    ]

    agg = {}
    for key in numeric_keys:
        values = [m[key] for m in all_case_metrics if m.get(key) is not None]
        if values:
            agg[f"{key}_mean"] = safe_mean(values)
            agg[f"{key}_std"] = safe_stdev(values)
            agg[f"{key}_n"] = len(values)
        else:
            agg[f"{key}_mean"] = None
            agg[f"{key}_std"] = None
            agg[f"{key}_n"] = 0

    # Categorical distributions
    gs_dist = defaultdict(int)
    src_dist = defaultdict(int)
    for m in all_case_metrics:
        gs_dist[m.get("grounding_status", "unknown")] += 1
        src_dist[m.get("generation_source", "unknown")] += 1
    agg["grounding_status_dist"] = dict(gs_dist)
    agg["generation_source_dist"] = dict(src_dist)
    agg["total_cases"] = len(all_case_metrics)

    return agg


def find_common_cases(variants_dirs):
    """Find case IDs present in ALL variants."""
    case_sets = []
    for vdir in variants_dirs.values():
        run_path = RUNS_DIR / vdir
        if not run_path.exists():
            print(f"WARNING: {run_path} does not exist")
            continue
        cases = {d for d in os.listdir(run_path) if d.startswith("case_")}
        case_sets.append(cases)
    common = case_sets[0]
    for cs in case_sets[1:]:
        common = common & cs
    return sorted(common)


def main():
    common_cases = find_common_cases(VARIANTS)
    print(f"Found {len(common_cases)} common cases across all 4 variants\n")

    all_results = {}
    failed_cases = defaultdict(list)

    for vname, vdir in VARIANTS.items():
        case_metrics = []
        for case_id in common_cases:
            s1_path = RUNS_DIR / vdir / case_id / "stage1.raw.json"
            s2_path = RUNS_DIR / vdir / case_id / "stage2.raw.json"

            if not s1_path.exists() or not s2_path.exists():
                failed_cases[vname].append((case_id, "missing_file"))
                continue

            try:
                s1_data = load_json(s1_path)
                s2_data = load_json(s2_path)
                m = compute_case_metrics(s1_data, s2_data)
                if m:
                    case_metrics.append(m)
                else:
                    failed_cases[vname].append((case_id, "no_selected"))
            except Exception as e:
                failed_cases[vname].append((case_id, str(e)))

        all_results[vname] = aggregate_metrics(case_metrics)
        print(f"  {vname}: {len(case_metrics)} cases processed, {len(failed_cases[vname])} failed")

    # --- Print comparison table ---
    print("\n" + "=" * 120)
    print("STAGE 1 ABLATION METRICS COMPARISON")
    print("=" * 120)

    key_metrics = [
        ("num_candidates", "Candidate Pool Size"),
        ("candidate_score_spread", "Score Spread (max-min)"),
        ("source_diversity", "Source Diversity"),
        ("has_llm_candidate", "Has LLM Candidate (%)"),
        ("has_rule_candidate", "Has Rule Candidate (%)"),
        ("selected_score", "Selected Score"),
        ("sb_final_score", "Final Score (breakdown)"),
        ("sb_component_coverage", "Component Coverage"),
        ("sb_signal_coverage", "Signal Coverage"),
        ("sb_criteria_coverage", "Criteria Coverage"),
        ("sb_constraint_completeness", "Constraint Completeness"),
        ("sb_regime_coverage", "Regime Coverage"),
        ("sb_topology_alignment", "Topology Alignment"),
        ("sb_chain_completeness", "Chain Completeness"),
        ("sb_requirement_grounding", "Requirement Grounding"),
        ("num_tasks", "Tasks per Candidate"),
        ("total_required_signals", "Total Required Signals"),
        ("total_signal_specs", "Total Signal Specs"),
        ("total_acceptance_criteria", "Total Acceptance Criteria"),
        ("total_constraints", "Total Constraints"),
        ("avg_signals_per_task", "Avg Signals/Task"),
        ("criteria_nonempty_rate", "Criteria Non-empty Rate"),
        ("spec_grounding_rate", "Spec Grounding Rate"),
        ("is_grounded", "Grounded Rate (%)"),
        ("num_grounded_components", "Grounded Components"),
        ("num_grounded_ports", "Grounded Ports"),
        ("p_value", "P-value (conformal)"),
        ("conformal_accepted", "Conformal Accepted (%)"),
        ("has_conformal", "Has Conformal Info (%)"),
        ("num_signal_chains", "Signal Chains"),
        ("avg_chain_length", "Avg Chain Length"),
        ("task_grounded_rate", "Task Grounded Rate"),
        ("task_llm_sanitized_rate", "Task LLM Sanitized Rate"),
    ]

    header = f"{'Metric':<35} | "
    header += " | ".join(f"{v:>20}" for v in VARIANTS.keys())
    print(header)
    print("-" * len(header))

    discriminative_metrics = []

    for key, label in key_metrics:
        mean_key = f"{key}_mean"
        std_key = f"{key}_std"
        n_key = f"{key}_n"

        values = []
        row = f"{label:<35} | "
        parts = []
        for vname in VARIANTS.keys():
            agg = all_results[vname]
            mean_val = agg.get(mean_key)
            std_val = agg.get(std_key)
            n_val = agg.get(n_key, 0)
            if mean_val is not None:
                values.append(mean_val)
                if key in ("has_llm_candidate", "has_rule_candidate", "is_grounded",
                           "conformal_accepted", "has_conformal"):
                    parts.append(f"{mean_val * 100:>17.1f}%  ")
                else:
                    parts.append(f"{mean_val:>15.4f} ±{std_val:.3f}" if std_val else f"{mean_val:>15.4f}      ")
            else:
                parts.append(f"{'N/A':>20}")
                values.append(None)
        row += " | ".join(parts)

        # Check discriminability
        valid_values = [v for v in values if v is not None]
        if len(valid_values) >= 2:
            vmax = max(valid_values)
            vmin = min(valid_values)
            ref = max(abs(vmax), abs(vmin), 1e-9)
            rel_diff = (vmax - vmin) / ref
            if rel_diff > 0.10:
                row += f"  <<< {rel_diff*100:.1f}%"
                discriminative_metrics.append((label, key, rel_diff, valid_values))

        print(row)

    # Generation source distribution
    print("\n" + "=" * 80)
    print("GENERATION SOURCE DISTRIBUTION")
    print("=" * 80)
    for vname in VARIANTS.keys():
        agg = all_results[vname]
        dist = agg.get("generation_source_dist", {})
        total = agg.get("total_cases", 1)
        print(f"\n  {vname}:")
        for src, cnt in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    {src:<35} {cnt:>4} ({cnt/total*100:.1f}%)")

    # Grounding status distribution
    print("\n" + "=" * 80)
    print("GROUNDING STATUS DISTRIBUTION")
    print("=" * 80)
    for vname in VARIANTS.keys():
        agg = all_results[vname]
        dist = agg.get("grounding_status_dist", {})
        total = agg.get("total_cases", 1)
        print(f"\n  {vname}:")
        for gs, cnt in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    {gs:<35} {cnt:>4} ({cnt/total*100:.1f}%)")

    # Summary of discriminative metrics
    print("\n" + "=" * 80)
    print("DISCRIMINATIVE METRICS (>10% relative difference)")
    print("=" * 80)
    discriminative_metrics.sort(key=lambda x: -x[2])
    for label, key, rel_diff, vals in discriminative_metrics:
        vnames = list(VARIANTS.keys())
        print(f"\n  {label} (rel_diff={rel_diff*100:.1f}%):")
        for i, vn in enumerate(vnames):
            if i < len(vals) and vals[i] is not None:
                print(f"    {vn:<30} {vals[i]:.4f}")

    # Save raw results
    output_path = RUNS_DIR / "stage1_ablation_metrics.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nRaw results saved to: {output_path}")

    # Failed cases summary
    for vname, failures in failed_cases.items():
        if failures:
            print(f"\n  {vname}: {len(failures)} failed cases")
            for cid, reason in failures[:5]:
                print(f"    {cid}: {reason}")


if __name__ == "__main__":
    main()
