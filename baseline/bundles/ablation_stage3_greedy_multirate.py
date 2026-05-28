"""Register the ablation_stage3_greedy_multirate evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage1, current_stage2
from ..stage3.greedy_multirate_scheduler import greedy_multirate_scheduler_stage3


register_bundle(
    build_bundle(
        name="ablation_stage3_greedy_multirate",
        description="Stage-3 greedy-multirate ablation using the baseline greedy multi-rate scheduler and current stage1/stage2 wrappers.",
        stage1=current_stage1,
        stage2=current_stage2,
        stage3=greedy_multirate_scheduler_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage3_greedy_multirate",
            "status": "implemented",
        },
    )
)
