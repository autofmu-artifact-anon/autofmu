"""Register the ablation_stage1_heuristic_neighborhood evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage2, current_stage3
from ..stage1.heuristic_neighborhood import heuristic_neighborhood_stage1


register_bundle(
    build_bundle(
        name="ablation_stage1_heuristic_neighborhood",
        description="Stage-1 heuristic-neighborhood ablation using the baseline neighborhood stage and current stage2/stage3 wrappers.",
        stage1=heuristic_neighborhood_stage1,
        stage2=current_stage2,
        stage3=current_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage1_heuristic_neighborhood",
            "status": "implemented",
        },
    )
)
