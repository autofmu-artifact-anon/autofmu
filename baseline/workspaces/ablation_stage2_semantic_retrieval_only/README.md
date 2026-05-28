# ablation_stage2_semantic_retrieval_only

Ablation: Semantic Retrieval Only

Stage-2 ablation that relies on semantic retrieval alone while keeping the current Stage 1 and Stage 3.

Stage Matrix
- Stage 1: `current_stage1`
- Stage 2: `semantic_retrieval_only`
- Stage 3: `current_stage3`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
