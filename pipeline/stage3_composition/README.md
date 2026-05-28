# Stage 3 - Composition

Goal: `MatchingResult` + MBSE context -> `CompositionResult` and executable `SimulationConfig`.

## Public API

```python
from pipeline.stage3_composition import compose

composition = compose(matching, mbse_context=mbse_context)
config = composition.simulation_config
```

Signature:

```python
compose(
    matching: MatchingResult,
    *,
    mbse_context: MBSEContext,
) -> CompositionResult
```

Full-mode pipeline:
- Read `matching.graph` and `matching.discrepancy_set`.
- Synthesize adapter specs for mismatch edges.
- Materialize adapter artifacts under `pipeline/resources/generated_adapters/`.
- Rewrite the orchestration graph with inserted adapter nodes.
- Build a multi-rate schedule with:
  - `base_tick`
  - `communication_grid`
  - `per_node_period`
  - `per_node_schedule`
  - `per_edge_hold_policy`
- Detect strongly connected components and emit Gauss-Seidel loop wrapper specs.
- Validate the final `SimulationConfig`.

`CompositionResult` includes:
- `graph_augmented`
- `adapters`
- `schedule`
- `loop_resolution`
- `simulation_config`

Stage 3 preserves the top-level pipeline output shape, but the internal schedule and adapter metadata are now substantially richer than the earlier preview-only implementation.

## Ablation

```python
from pipeline.stage3_composition import compose_ablation

composition = compose_ablation(matching, mbse_context=mbse_context)
```

Ablation uses fixed-step scheduling and direct wiring only. It does not synthesize adapters or loop wrapper metadata.
