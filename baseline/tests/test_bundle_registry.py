"""Integration checks for baseline bundle registration and stage wiring."""

from __future__ import annotations

import baseline  # noqa: F401
import baseline.common as common
import baseline.stage1.heuristic_neighborhood as heuristic_module
import baseline.stage1.rule_template as rule_template_module
import baseline.stage1.top1_llm as top1_module
import baseline.stage2.graph_match_only as graph_match_module
import baseline.stage2.greedy_hybrid as greedy_hybrid_module
import baseline.stage2.semantic_retrieval_only as semantic_module
import baseline.stage3.greedy_multirate_scheduler as greedy_multirate_module
import baseline.stage3.llm_generated_script as llm_script_module
import baseline.stage3.static_rule_scheduler as static_module
from evaluator.registry import available_bundles, get_bundle


def _unwrap_stage(wrapper, freevar_name: str):
    closure = {
        name: cell.cell_contents
        for name, cell in zip(wrapper.__code__.co_freevars, wrapper.__closure__ or ())
    }
    return closure[freevar_name]


def _stage_callable(stage_key: str):
    mapping = {
        "current_stage1": common.current_stage1,
        "current_stage2": common.current_stage2,
        "current_stage3": common.current_stage3,
        "top1_llm": top1_module.top1_llm_stage1,
        "rule_template": rule_template_module.rule_template_stage1,
        "heuristic_neighborhood": heuristic_module.heuristic_neighborhood_stage1,
        "semantic_retrieval_only": semantic_module.semantic_retrieval_only_stage2,
        "graph_match_only": graph_match_module.graph_match_only_stage2,
        "greedy_hybrid": greedy_hybrid_module.greedy_hybrid_stage2,
        "static_rule_scheduler": static_module.static_rule_scheduler_stage3,
        "greedy_multirate_scheduler": greedy_multirate_module.greedy_multirate_scheduler_stage3,
        "llm_generated_script": llm_script_module.llm_generated_script_stage3,
    }
    return mapping[stage_key]


def test_all_baseline_bundles_are_registered() -> None:
    for method_name in common.METHOD_NAMES:
        assert method_name in available_bundles()


def test_registered_bundle_metadata_matches_method_specs() -> None:
    for method_name, spec in common.METHOD_SPECS.items():
        bundle = get_bundle(method_name)
        assert bundle.metadata["family"] == spec.family
        assert bundle.metadata["variant"] == spec.variant
        assert bundle.metadata["method_name"] == spec.name
        assert bundle.metadata["workspace_root"] == str(common.method_workspace(spec.name).resolve())


def test_registered_bundle_stage_matrix_matches_method_specs() -> None:
    for method_name, spec in common.METHOD_SPECS.items():
        bundle = get_bundle(method_name)
        assert _unwrap_stage(bundle.stage1, "stage1") is _stage_callable(spec.stage1_key)
        assert _unwrap_stage(bundle.stage2, "stage2") is _stage_callable(spec.stage2_key)
        assert _unwrap_stage(bundle.stage3, "stage3") is _stage_callable(spec.stage3_key)
