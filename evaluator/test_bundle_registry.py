from __future__ import annotations

EXPECTED_BASELINE_BUNDLES = {
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
}


def test_available_bundles_includes_all_baseline_stubs() -> None:
    import evaluator.runner  # noqa: F401
    from evaluator.registry import available_bundles

    assert EXPECTED_BASELINE_BUNDLES.issubset(set(available_bundles()))
