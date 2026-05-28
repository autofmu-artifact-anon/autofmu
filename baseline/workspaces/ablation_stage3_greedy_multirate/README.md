# ablation_stage3_greedy_multirate

Ablation: Greedy Multi-Rate Scheduler

Stage-3 ablation that uses a greedy multi-rate schedule with the current Stage 1 and Stage 2.

Stage Matrix
- Stage 1: `current_stage1`
- Stage 2: `current_stage2`
- Stage 3: `greedy_multirate_scheduler`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
