"""Register the ablation_stage2_greedy_hybrid evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage1, current_stage3
from ..stage2.greedy_hybrid import greedy_hybrid_stage2


register_bundle(
    build_bundle(
        name="ablation_stage2_greedy_hybrid",
        description="Stage-2 greedy-hybrid ablation using the baseline hybrid matcher and current stage1/stage3 wrappers.",
        stage1=current_stage1,
        stage2=greedy_hybrid_stage2,
        stage3=current_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage2_greedy_hybrid",
            "status": "implemented",
        },
    )
)
