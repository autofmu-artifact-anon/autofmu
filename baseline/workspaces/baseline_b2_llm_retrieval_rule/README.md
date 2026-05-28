# baseline_b2_llm_retrieval_rule

B2 LLM + Local Retrieval + Rule Orchestration

LLM-style top-1 decomposition plus semantic retrieval and deterministic rule scheduling.

Stage Matrix
- Stage 1: `top1_llm`
- Stage 2: `semantic_retrieval_only`
- Stage 3: `static_rule_scheduler`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
