"""Register the baseline_b1_rule_sequential evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle
from ..stage1.rule_template import rule_template_stage1
from ..stage2.graph_match_only import graph_match_only_stage2
from ..stage3.static_rule_scheduler import static_rule_scheduler_stage3


register_bundle(
    build_bundle(
        name="baseline_b1_rule_sequential",
        description="Deterministic rule-sequential baseline using rule-template decomposition, graph-only matching, and static rule scheduling.",
        stage1=rule_template_stage1,
        stage2=graph_match_only_stage2,
        stage3=static_rule_scheduler_stage3,
        metadata={
            "family": "baseline",
            "variant": "b1_rule_sequential",
            "status": "implemented",
        },
    )
)
