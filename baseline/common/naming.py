"""Stable names and metadata for baseline bundles and workspaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodSpec:
    """Human-readable metadata and stage matrix for one evaluator bundle."""

    name: str
    title: str
    family: str
    variant: str
    summary: str
    stage1_key: str
    stage2_key: str
    stage3_key: str


METHOD_SPECS: dict[str, MethodSpec] = {
    "baseline_b1_rule_sequential": MethodSpec(
        name="baseline_b1_rule_sequential",
        title="B1 Rule-Based Sequential Pipeline",
        family="baseline",
        variant="b1_rule_sequential",
        summary="Deterministic end-to-end baseline using rule decomposition, structure-first FMU matching, and a static scheduler.",
        stage1_key="rule_template",
        stage2_key="graph_match_only",
        stage3_key="static_rule_scheduler",
    ),
    "baseline_b2_llm_retrieval_rule": MethodSpec(
        name="baseline_b2_llm_retrieval_rule",
        title="B2 LLM + Local Retrieval + Rule Orchestration",
        family="baseline",
        variant="b2_llm_retrieval_rule",
        summary="LLM-style top-1 decomposition plus semantic retrieval and deterministic rule scheduling.",
        stage1_key="top1_llm",
        stage2_key="semantic_retrieval_only",
        stage3_key="static_rule_scheduler",
    ),
    "baseline_b3_graph_aware": MethodSpec(
        name="baseline_b3_graph_aware",
        title="B3 Heuristic Graph-Aware Pipeline",
        family="baseline",
        variant="b3_graph_aware",
        summary="Graph-aware baseline using neighborhood heuristics, greedy hybrid matching, and a greedy multi-rate scheduler.",
        stage1_key="heuristic_neighborhood",
        stage2_key="greedy_hybrid",
        stage3_key="greedy_multirate_scheduler",
    ),
    "ablation_stage1_top1_llm": MethodSpec(
        name="ablation_stage1_top1_llm",
        title="Ablation: Top-1 LLM Decomposition",
        family="ablation",
        variant="stage1_top1_llm",
        summary="Stage-1 ablation that swaps in exactly one LLM-style decomposition candidate while keeping the current Stage 2 and Stage 3.",
        stage1_key="top1_llm",
        stage2_key="current_stage2",
        stage3_key="current_stage3",
    ),
    "ablation_stage1_rule_template": MethodSpec(
        name="ablation_stage1_rule_template",
        title="Ablation: Rule Template Decomposition",
        family="ablation",
        variant="stage1_rule_template",
        summary="Stage-1 ablation that uses deterministic rule-template decomposition with the current Stage 2 and Stage 3.",
        stage1_key="rule_template",
        stage2_key="current_stage2",
        stage3_key="current_stage3",
    ),
    "ablation_stage1_heuristic_neighborhood": MethodSpec(
        name="ablation_stage1_heuristic_neighborhood",
        title="Ablation: Heuristic Neighborhood Decomposition",
        family="ablation",
        variant="stage1_heuristic_neighborhood",
        summary="Stage-1 ablation that anchors requirements to MBSE neighborhoods before handing off to the current Stage 2 and Stage 3.",
        stage1_key="heuristic_neighborhood",
        stage2_key="current_stage2",
        stage3_key="current_stage3",
    ),
    "ablation_stage2_semantic_retrieval_only": MethodSpec(
        name="ablation_stage2_semantic_retrieval_only",
        title="Ablation: Semantic Retrieval Only",
        family="ablation",
        variant="stage2_semantic_retrieval_only",
        summary="Stage-2 ablation that relies on semantic retrieval alone while keeping the current Stage 1 and Stage 3.",
        stage1_key="current_stage1",
        stage2_key="semantic_retrieval_only",
        stage3_key="current_stage3",
    ),
    "ablation_stage2_graph_match_only": MethodSpec(
        name="ablation_stage2_graph_match_only",
        title="Ablation: Graph Match Only",
        family="ablation",
        variant="stage2_graph_match_only",
        summary="Stage-2 ablation that uses structural graph matching only while keeping the current Stage 1 and Stage 3.",
        stage1_key="current_stage1",
        stage2_key="graph_match_only",
        stage3_key="current_stage3",
    ),
    "ablation_stage2_greedy_hybrid": MethodSpec(
        name="ablation_stage2_greedy_hybrid",
        title="Ablation: Greedy Hybrid Match",
        family="ablation",
        variant="stage2_greedy_hybrid",
        summary="Stage-2 ablation that combines semantic and structural evidence greedily while keeping the current Stage 1 and Stage 3.",
        stage1_key="current_stage1",
        stage2_key="greedy_hybrid",
        stage3_key="current_stage3",
    ),
    "ablation_stage3_static_rule_scheduler": MethodSpec(
        name="ablation_stage3_static_rule_scheduler",
        title="Ablation: Static Rule Scheduler",
        family="ablation",
        variant="stage3_static_rule_scheduler",
        summary="Stage-3 ablation that uses deterministic schedule templates with the current Stage 1 and Stage 2.",
        stage1_key="current_stage1",
        stage2_key="current_stage2",
        stage3_key="static_rule_scheduler",
    ),
    "ablation_stage3_greedy_multirate": MethodSpec(
        name="ablation_stage3_greedy_multirate",
        title="Ablation: Greedy Multi-Rate Scheduler",
        family="ablation",
        variant="stage3_greedy_multirate",
        summary="Stage-3 ablation that uses a greedy multi-rate schedule with the current Stage 1 and Stage 2.",
        stage1_key="current_stage1",
        stage2_key="current_stage2",
        stage3_key="greedy_multirate_scheduler",
    ),
    "ablation_stage3_llm_generated_script": MethodSpec(
        name="ablation_stage3_llm_generated_script",
        title="Ablation: LLM-Generated Orchestration Script",
        family="ablation",
        variant="stage3_llm_generated_script",
        summary="Stage-3 ablation that emits an orchestration script/config payload while keeping the current Stage 1 and Stage 2.",
        stage1_key="current_stage1",
        stage2_key="current_stage2",
        stage3_key="llm_generated_script",
    ),
}

METHOD_NAMES = tuple(METHOD_SPECS)


def method_spec(method_name: str) -> MethodSpec:
    """Return the metadata record for a known method name."""
    try:
        return METHOD_SPECS[method_name]
    except KeyError as exc:
        known = ", ".join(sorted(METHOD_SPECS))
        raise ValueError(f"Unknown method name {method_name!r}. Valid names: {known}") from exc


def workspace_readme_content(method_name: str) -> str:
    """Render the checked-in README content for a method workspace."""
    spec = method_spec(method_name)
    return (
        f"# {spec.name}\n\n"
        f"{spec.title}\n\n"
        f"{spec.summary}\n\n"
        "Stage Matrix\n"
        f"- Stage 1: `{spec.stage1_key}`\n"
        f"- Stage 2: `{spec.stage2_key}`\n"
        f"- Stage 3: `{spec.stage3_key}`\n\n"
        "Workspace Policy\n"
        "- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.\n"
        "- Do not place duplicated dataset or pipeline trees here.\n"
        "- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.\n"
    )


__all__ = [
    "METHOD_NAMES",
    "METHOD_SPECS",
    "MethodSpec",
    "method_spec",
    "workspace_readme_content",
]
