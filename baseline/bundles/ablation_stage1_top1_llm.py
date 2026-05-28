"""Register the ablation_stage1_top1_llm evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle, current_stage2, current_stage3
from ..stage1.top1_llm import top1_llm_stage1


register_bundle(
    build_bundle(
        name="ablation_stage1_top1_llm",
        description="Stage-1 top1 LLM ablation using the baseline top1 stage and current stage2/stage3 wrappers.",
        stage1=top1_llm_stage1,
        stage2=current_stage2,
        stage3=current_stage3,
        stage2_config={
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": False,
        },
        metadata={
            "family": "ablation",
            "variant": "stage1_top1_llm",
            "status": "implemented",
        },
    )
)
