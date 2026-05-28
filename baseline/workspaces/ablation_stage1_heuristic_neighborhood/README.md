# ablation_stage1_heuristic_neighborhood

Ablation: Heuristic Neighborhood Decomposition

Stage-1 ablation that anchors requirements to MBSE neighborhoods before handing off to the current Stage 2 and Stage 3.

Stage Matrix
- Stage 1: `heuristic_neighborhood`
- Stage 2: `current_stage2`
- Stage 3: `current_stage3`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
