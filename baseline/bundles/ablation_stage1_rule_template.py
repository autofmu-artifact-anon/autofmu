"""Register the ablation_stage1_rule_template evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage2, current_stage3
from ..stage1.rule_template import rule_template_stage1


register_bundle(
    build_bundle(
        name="ablation_stage1_rule_template",
        description="Stage-1 rule-template ablation using the baseline rule-template stage and current stage2/stage3 wrappers.",
        stage1=rule_template_stage1,
        stage2=current_stage2,
        stage3=current_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage1_rule_template",
            "status": "implemented",
        },
    )
)
