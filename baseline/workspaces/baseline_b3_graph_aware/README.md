# baseline_b3_graph_aware

B3 Heuristic Graph-Aware Pipeline

Graph-aware baseline using neighborhood heuristics, greedy hybrid matching, and a greedy multi-rate scheduler.

Stage Matrix
- Stage 1: `heuristic_neighborhood`
- Stage 2: `greedy_hybrid`
- Stage 3: `greedy_multirate_scheduler`

Workspace Policy
- Keep prompts, fixtures, cache entries, notes, and debug runs scoped to this method only.
- Do not place duplicated dataset or pipeline trees here.
- Do not place official evaluator outputs here; those belong under `evaluator/runs/`.
