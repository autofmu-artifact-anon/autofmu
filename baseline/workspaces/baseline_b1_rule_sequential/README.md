# baseline_b1_rule_sequential

B1 Rule-Based Sequential Pipeline

Deterministic end-to-end baseline using rule decomposition, structure-first FMU matching, and a static scheduler.

Stage Matrix
- Stage 1: `rule_template`
- Stage 2: `graph_match_only`
- Stage 3: `static_rule_scheduler`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
