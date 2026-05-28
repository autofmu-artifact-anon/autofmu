# Stage 1 - Decomposition

Goal: requirement text + MBSE context -> calibrated candidate `TaskSet` list.

## Public API

```python
from pipeline.stage1_decomposition import decompose

task_sets = decompose(
    "control battery temperature below 45 C",
    mbse_context=mbse_context,
    confidence=0.9,
    max_candidates=6,
)
```

Signature:

```python
decompose(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    confidence: float = 0.9,
    max_candidates: int = 6,
) -> list[TaskSet]
```

Full-mode pipeline:
- Generate raw task sets from rules and optional LLM extraction.
- Ground each candidate to MBSE components, ports, and signals.
- Repair invalid grounding with bounded retries.
- Score each grounded candidate with a verifiability breakdown.
- Apply conformal filtering using `pipeline/resources/stage1_calibration.json`.
- Return the calibrated `TaskSet` list for Stage 2.

Returned `TaskSet` objects now carry:
- `task_set_id`
- `generation_source`
- `grounding_status`
- `score`
- `p_value`
- `score_breakdown`

LLM use is optional. If no LLM credentials are configured, the stage falls back to deterministic rule-based generation.

## Ablation

```python
from pipeline.stage1_decomposition import decompose_ablation

task_sets = decompose_ablation(
    "control battery temperature below 45 C",
    mbse_context=mbse_context,
)
```

Ablation returns a single minimal `TaskSet`. It does not perform grounding repair or conformal filtering.
