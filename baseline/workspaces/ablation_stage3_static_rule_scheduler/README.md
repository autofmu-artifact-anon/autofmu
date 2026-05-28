# ablation_stage3_static_rule_scheduler

Ablation: Static Rule Scheduler

Stage-3 ablation that uses deterministic schedule templates with the current Stage 1 and Stage 2.

Stage Matrix
- Stage 1: `current_stage1`
- Stage 2: `current_stage2`
- Stage 3: `static_rule_scheduler`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
