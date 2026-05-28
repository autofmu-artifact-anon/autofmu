"""Register the baseline_b3_graph_aware evaluator bundle."""

from evaluator.registry import register_bundle

from ..common import build_bundle
from ..stage1.heuristic_neighborhood import heuristic_neighborhood_stage1
from ..stage2.greedy_hybrid import greedy_hybrid_stage2
from ..stage3.greedy_multirate_scheduler import greedy_multirate_scheduler_stage3


register_bundle(
    build_bundle(
        name="baseline_b3_graph_aware",
        description="Graph-aware baseline using heuristic neighborhood decomposition, greedy hybrid matching, and greedy multirate scheduling.",
        stage1=heuristic_neighborhood_stage1,
        stage2=greedy_hybrid_stage2,
        stage3=greedy_multirate_scheduler_stage3,
        metadata={
            "family": "baseline",
            "variant": "b3_graph_aware",
            "status": "implemented",
        },
    )
)
