# Stage 2 - Matching

Goal: calibrated `TaskSet` candidates + FMU library -> `MatchingResult`.

## Public API

```python
from pipeline.stage2_matching import match

matching = match(
    task_sets,
    mbse_context=mbse_context,
    fmu_library=fmu_library,
    max_revisions=6,
    top_m_per_task=5,
    max_port_candidates=8,
    enable_benchmark_single_fmu_fallback=True,
    enable_mbse_component_cover_fallback=True,
)
```

Signature:

```python
match(
    task_sets: list[TaskSet],
    *,
    mbse_context: MBSEContext,
    fmu_library: list[FMU],
    max_revisions: int = 6,
    top_m_per_task: int = 5,
    max_port_candidates: int = 8,
    enable_benchmark_single_fmu_fallback: bool = True,
    enable_mbse_component_cover_fallback: bool = True,
) -> MatchingResult
```

Full-mode pipeline:
- Build a semantic cost matrix from task/FMU text similarity.
- Build a separate hard mask matrix from topology and signal feasibility.
- Solve a row-constrained transport problem over the fused matrix.
- Extract task-to-FMU assignments with transport mass and semantic cost.
- Instantiate the required port graph and record mismatch edges as `discrepancy_set`.
- If graph closure fails, update only the local hard mask entry and retry.
- Evaluate each candidate `TaskSet` independently and select the best feasible result.
- Optional fallback flags can disable the benchmark single-FMU recovery path or the MBSE component-cover recovery path when an experiment needs stricter ablation isolation.

`MatchingResult` includes:
- `task_set`
- `assignments`
- `selected_fmus`
- `graph`
- `discrepancy_set`
- `transport_plans`
- `mask_history`
- `revision_trace`
- `taskset_results`
- `selected_task_set_cost`

Mismatch edges are deferred to Stage 3. They are not dropped during matching.

## Ablation

```python
from pipeline.stage2_matching import match_ablation

matching = match_ablation(
    task_sets,
    mbse_context=mbse_context,
    fmu_library=fmu_library,
)
```

Ablation performs single-FMU semantic ranking only. It does not run transport, graph revision, or discrepancy-aware closure.
