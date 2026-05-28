"""Evaluator bundle registrations for baselines and ablations."""

from . import baseline_b1_rule_sequential  # noqa: F401
from . import baseline_b2_llm_retrieval_rule  # noqa: F401
from . import baseline_b3_graph_aware  # noqa: F401
from . import ablation_stage1_top1_llm  # noqa: F401
from . import ablation_stage1_rule_template  # noqa: F401
from . import ablation_stage1_heuristic_neighborhood  # noqa: F401
from . import ablation_stage2_semantic_retrieval_only  # noqa: F401
from . import ablation_stage2_graph_match_only  # noqa: F401
from . import ablation_stage2_greedy_hybrid  # noqa: F401
from . import ablation_stage3_static_rule_scheduler  # noqa: F401
from . import ablation_stage3_greedy_multirate  # noqa: F401
from . import ablation_stage3_llm_generated_script  # noqa: F401

__all__ = [
    "baseline_b1_rule_sequential",
    "baseline_b2_llm_retrieval_rule",
    "baseline_b3_graph_aware",
    "ablation_stage1_top1_llm",
    "ablation_stage1_rule_template",
    "ablation_stage1_heuristic_neighborhood",
    "ablation_stage2_semantic_retrieval_only",
    "ablation_stage2_graph_match_only",
    "ablation_stage2_greedy_hybrid",
    "ablation_stage3_static_rule_scheduler",
    "ablation_stage3_greedy_multirate",
    "ablation_stage3_llm_generated_script",
]
