"""Register the ablation_stage3_static_rule_scheduler evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage1, current_stage2
from ..stage3.static_rule_scheduler import static_rule_scheduler_stage3


register_bundle(
    build_bundle(
        name="ablation_stage3_static_rule_scheduler",
        description="Stage-3 static-rule scheduler ablation using the baseline static scheduler and current stage1/stage2 wrappers.",
        stage1=current_stage1,
        stage2=current_stage2,
        stage3=static_rule_scheduler_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage3_static_rule_scheduler",
            "status": "implemented",
        },
    )
)
