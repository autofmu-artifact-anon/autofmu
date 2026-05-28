# ablation_stage3_llm_generated_script

Ablation: LLM-Generated Orchestration Script

Stage-3 ablation that directly generates the final `UNIFIED_SOLUTION_V1` orchestration payload fields from a deterministic base configuration, with a rule-based fallback.

Stage Matrix
- Stage 1: `current_stage1`
- Stage 2: `current_stage2`
- Stage 3: `llm_generated_script`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
