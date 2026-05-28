"""Register the baseline_b2_llm_retrieval_rule evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle
from ..stage1.top1_llm import top1_llm_stage1
from ..stage2.semantic_retrieval_only import semantic_retrieval_only_stage2
from ..stage3.static_rule_scheduler import static_rule_scheduler_stage3


register_bundle(
    build_bundle(
        name="baseline_b2_llm_retrieval_rule",
        description="LLM decomposition plus semantic retrieval baseline using the top1 LLM stage, semantic-only matching, and static rule scheduling.",
        stage1=top1_llm_stage1,
        stage2=semantic_retrieval_only_stage2,
        stage3=static_rule_scheduler_stage3,
        metadata={
            "family": "baseline",
            "variant": "b2_llm_retrieval_rule",
            "status": "implemented",
        },
    )
)
