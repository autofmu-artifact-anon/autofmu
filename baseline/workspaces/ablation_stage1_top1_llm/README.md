# ablation_stage1_top1_llm

Ablation: Top-1 LLM Decomposition

Stage-1 ablation that swaps in exactly one LLM-style decomposition candidate while keeping the current Stage 2 and Stage 3.

Stage Matrix
- Stage 1: `top1_llm`
- Stage 2: `current_stage2`
- Stage 3: `current_stage3`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
