# ablation_stage2_graph_match_only

Ablation: Graph Match Only

Stage-2 ablation that uses structural graph matching only while keeping the current Stage 1 and Stage 3.

Stage Matrix
- Stage 1: `current_stage1`
- Stage 2: `graph_match_only`
- Stage 3: `current_stage3`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
