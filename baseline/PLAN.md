# Baseline / Ablation Construction Plan

This directory hosts evaluator-loadable method bundles for three full baselines and nine single-module ablations.

The design goal is strict isolation: each method gets a clearly bounded code workspace, a predictable artifact namespace, and a narrow responsibility boundary so cron slices can stay small and non-overlapping.

## Target layout

```text
baseline/
  PLAN.md
  __init__.py
  common/
    __init__.py
    bundle_factory.py
    current_stages.py
    io.py
    naming.py
    paths.py
    workspace.py
  stage1/
    __init__.py
    top1_llm.py
    rule_template.py
    heuristic_neighborhood.py
  stage2/
    __init__.py
    semantic_retrieval_only.py
    graph_match_only.py
    greedy_hybrid.py
  stage3/
    __init__.py
    static_rule_scheduler.py
    greedy_multirate_scheduler.py
    llm_generated_script.py
  bundles/
    __init__.py
    baseline_b1_rule_sequential.py
    baseline_b2_llm_retrieval_rule.py
    baseline_b3_graph_aware.py
    ablation_stage1_top1_llm.py
    ablation_stage1_rule_template.py
    ablation_stage1_heuristic_neighborhood.py
    ablation_stage2_semantic_retrieval_only.py
    ablation_stage2_graph_match_only.py
    ablation_stage2_greedy_hybrid.py
    ablation_stage3_static_rule_scheduler.py
    ablation_stage3_greedy_multirate.py
    ablation_stage3_llm_generated_script.py
  workspaces/
    README.md
    baseline_b1_rule_sequential/
    baseline_b2_llm_retrieval_rule/
    baseline_b3_graph_aware/
    ablation_stage1_top1_llm/
    ablation_stage1_rule_template/
    ablation_stage1_heuristic_neighborhood/
    ablation_stage2_semantic_retrieval_only/
    ablation_stage2_graph_match_only/
    ablation_stage2_greedy_hybrid/
    ablation_stage3_static_rule_scheduler/
    ablation_stage3_greedy_multirate/
    ablation_stage3_llm_generated_script/
  artifacts/
    README.md
  tests/
    __init__.py
    test_bundle_registry.py
    test_stage1_variants.py
    test_stage2_variants.py
    test_stage3_variants.py
```

## Architectural boundaries

There are three layers only:

1. `baseline/stage*/` contains atomic reusable method logic.
2. `baseline/bundles/` contains only bundle composition and registration.
3. `baseline/common/` contains shared glue, path management, workspace policy, and wrappers around current pipeline stages.

Everything else is forbidden:

- no baseline-specific logic inside `evaluator/`
- no dumping method-specific helpers directly into `pipeline/`
- no method implementation logic inside `bundles/`
- no ad hoc scratch files in repo root

## Workspace policy

Each of the 12 methods gets a dedicated workspace root under:

`~/projects/experiments/baseline/workspaces/<method_name>/`

That workspace is not a second codebase. It is a bounded scratch/artifact namespace for that method only.

Allowed contents inside each method workspace:

- `README.md` — what the method is, expected inputs/outputs
- `notes.md` — method-specific implementation notes if needed
- `prompts/` — only for LLM-invoking methods
- `fixtures/` — only if a method needs method-local deterministic templates/examples
- `cache/` — optional local reusable cache, safe to delete
- `runs/` — optional method-local debug outputs, separate from evaluator official outputs

Not allowed inside method workspaces:

- duplicated copies of `dataset/`
- duplicated copies of `pipeline/`
- standalone evaluators
- random one-off scripts unless they are clearly method-scoped and checked in intentionally

## Workspace contract by method

### Baseline bundles

#### `baseline_b1_rule_sequential`
Workspace: `baseline/workspaces/baseline_b1_rule_sequential/`
Purpose:
- deterministic rule-based end-to-end pipeline
Allowed method-local assets:
- rule templates
- deterministic parsing dictionaries
- scheduler templates
Should not contain:
- prompts
- semantic retrieval indices

#### `baseline_b2_llm_retrieval_rule`
Workspace: `baseline/workspaces/baseline_b2_llm_retrieval_rule/`
Purpose:
- LLM decomposition + local retrieval + rule scheduling
Allowed method-local assets:
- prompts for top1 decomposition and script synthesis fallback if needed
- retrieval tuning notes
- deterministic scheduler templates
Should not contain:
- graph-only structural heuristics that belong to B3

#### `baseline_b3_graph_aware`
Workspace: `baseline/workspaces/baseline_b3_graph_aware/`
Purpose:
- heuristic graph-aware end-to-end pipeline
Allowed method-local assets:
- graph heuristic notes
- topology scoring weights
- greedy multirate scheduling heuristics
Should not contain:
- LLM prompt assets unless absolutely necessary

### Stage-1 ablation bundles

#### `ablation_stage1_top1_llm`
Workspace: `baseline/workspaces/ablation_stage1_top1_llm/`
Scope:
- only the decomposition module differs from current pipeline
Method-local assets:
- top1 decomposition prompt/config

#### `ablation_stage1_rule_template`
Workspace: `baseline/workspaces/ablation_stage1_rule_template/`
Scope:
- deterministic rule-template decomposition only
Method-local assets:
- regex/template definitions
- entity alias tables

#### `ablation_stage1_heuristic_neighborhood`
Workspace: `baseline/workspaces/ablation_stage1_heuristic_neighborhood/`
Scope:
- MBSE-neighborhood decomposition only
Method-local assets:
- lexical anchor heuristics
- neighborhood expansion knobs

### Stage-2 ablation bundles

#### `ablation_stage2_semantic_retrieval_only`
Workspace: `baseline/workspaces/ablation_stage2_semantic_retrieval_only/`
Scope:
- semantic-only FMU matching
Method-local assets:
- retrieval scoring notes
- rank/debug dumps if needed

#### `ablation_stage2_graph_match_only`
Workspace: `baseline/workspaces/ablation_stage2_graph_match_only/`
Scope:
- structure-only FMU matching
Method-local assets:
- structural compatibility rules
- graph alignment diagnostics

#### `ablation_stage2_greedy_hybrid`
Workspace: `baseline/workspaces/ablation_stage2_greedy_hybrid/`
Scope:
- local greedy hybrid matching
Method-local assets:
- weighting configs
- greedy decision traces

### Stage-3 ablation bundles

#### `ablation_stage3_static_rule_scheduler`
Workspace: `baseline/workspaces/ablation_stage3_static_rule_scheduler/`
Scope:
- deterministic static orchestration
Method-local assets:
- schedule templates
- deterministic adapter policies

#### `ablation_stage3_greedy_multirate`
Workspace: `baseline/workspaces/ablation_stage3_greedy_multirate/`
Scope:
- heuristic multi-rate orchestration only
Method-local assets:
- step-size heuristics
- local schedule diagnostics

#### `ablation_stage3_llm_generated_script`
Workspace: `baseline/workspaces/ablation_stage3_llm_generated_script/`
Scope:
- script/config generation only
Method-local assets:
- prompts
- script templates
- generation fallback examples

## Artifact policy

There are two kinds of outputs:

### 1. Official evaluator outputs
These must stay under the existing evaluator namespace only:

`~/projects/experiments/evaluator/runs/<bundle>_<timestamp>/`

This is the only location considered authoritative for reported experiment results.

### 2. Method-local debug outputs
These may go under:

`~/projects/experiments/baseline/workspaces/<method>/runs/`

These are for development only and should never be treated as official evaluation outputs.

## Reuse strategy

The evaluator bundle surface is already stable: each method only needs `(stage1, stage2, stage3)` callables wrapped by `MethodBundle` and registered into `evaluator.registry`.

So the lowest-risk strategy is:

1. Keep `pipeline/` untouched as the reference full method.
2. Reuse `pipeline.types` as the canonical contract.
3. Reuse selective helper functions from `pipeline/stage*_*/` where the semantics match.
4. Implement baseline variants under `baseline/` as thin, explicit modules rather than forking the whole pipeline.
5. Register every method as an evaluator bundle so `python -m evaluator.cli --bundle <name>` works unchanged.

## Existing modules worth reusing

### Stage 1
- `pipeline.stage1_decomposition.decomposer_ablation.decompose`
- `pipeline.stage1_decomposition.grounding`
- `pipeline.stage1_decomposition.decomposer`

### Stage 2
- `pipeline.stage2_matching.matcher_ablation.match`
- `pipeline.stage2_matching.scoring`
- `pipeline.stage2_matching.graph_builder`
- `pipeline.stage2_matching.feasibility`
- `pipeline.stage2_matching.revision`

### Stage 3
- `pipeline.stage3_composition.composer_ablation.compose`
- `pipeline.stage3_composition.scheduler`
- `pipeline.stage3_composition.validator`
- `pipeline.stage3_composition.adapter_builder`
- `pipeline.stage3_composition.schedule_spec`
- `pipeline.stage3_composition.gcd_utils`

## Method construction matrix

The cleanest model is: define nine atomic stage modules, then compose them into twelve named bundles.

| Method | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| B1 Rule-Based Sequential Pipeline | rule_template | graph_match_only | static_rule_scheduler |
| B2 LLM + Local Retrieval + Rule Orchestration | top1_llm | semantic_retrieval_only | static_rule_scheduler |
| B3 Heuristic Graph-Aware Pipeline | heuristic_neighborhood | greedy_hybrid | greedy_multirate_scheduler |
| Ablation: Top-1 LLM Decomposition | top1_llm | current pipeline stage2 | current pipeline stage3 |
| Ablation: Rule Template Decomposition | rule_template | current pipeline stage2 | current pipeline stage3 |
| Ablation: Heuristic Neighborhood Decomposition | heuristic_neighborhood | current pipeline stage2 | current pipeline stage3 |
| Ablation: Semantic Retrieval Only | current pipeline stage1 | semantic_retrieval_only | current pipeline stage3 |
| Ablation: Graph Match Only | current pipeline stage1 | graph_match_only | current pipeline stage3 |
| Ablation: Greedy Hybrid Match | current pipeline stage1 | greedy_hybrid | current pipeline stage3 |
| Ablation: Static Rule Scheduler | current pipeline stage1 | current pipeline stage2 | static_rule_scheduler |
| Ablation: Greedy Multi-Rate Scheduler | current pipeline stage1 | current pipeline stage2 | greedy_multirate_scheduler |
| Ablation: LLM-Generated Orch. Script | current pipeline stage1 | current pipeline stage2 | llm_generated_script |

## Atomic module intent

### Stage 1 modules

#### `top1_llm.py`
Purpose:
- produce exactly one LLM-style task decomposition
- no set-valued calibration
- preserve the same `TaskSet` output contract

Implementation direction:
- start from current stage1 decomposition path but force `max_candidates=1`
- drop conformal set calibration metadata
- if the live LLM path is too entangled, adapt from `decomposer_ablation.py` but preserve grounding/criteria extraction

Workspace touch policy:
- may read/write only inside its assigned workspace under `prompts/`, `cache/`, and `runs/`
- no writes outside `baseline/workspaces/ablation_stage1_top1_llm/` or `baseline/workspaces/baseline_b2_llm_retrieval_rule/` except official evaluator outputs

#### `rule_template.py`
Purpose:
- deterministic parser using requirement text patterns + MBSE component/port names

Implementation direction:
- regex / keyword templates for objectives, thresholds, time windows, signals
- deterministic grounding against MBSE component names, port names, and aliases
- no stochastic generation, no calibration

Workspace touch policy:
- may store templates/aliases only under `rule_template`-using method workspaces
- no prompt files

#### `heuristic_neighborhood.py`
Purpose:
- anchor requirement entities to MBSE components and expand by local graph neighborhood

Implementation direction:
- identify seed components/signals from lexical overlap
- use `mbse_context.adjacency` / `connections` to gather nearby candidate tasks
- produce one heuristic task-set with local explainability metadata

Workspace touch policy:
- may persist heuristic configs and debug traces only in heuristic-neighborhood workspaces

### Stage 2 modules

#### `semantic_retrieval_only.py`
Purpose:
- pure semantic retrieval over FMU candidates
- no structural graph reasoning, no iterative topology validation

Implementation direction:
- reuse semantic scoring from `pipeline.stage2_matching.scoring`
- rank FMUs independently or per task
- minimal assembly into `MatchingResult`

Workspace touch policy:
- may store retrieval debug dumps only inside semantic-retrieval method workspaces
- no structural graph templates

#### `graph_match_only.py`
Purpose:
- structure-first selection via MBSE compatibility / graph pattern alignment
- no semantic retrieval score in the decision rule

Implementation direction:
- use component/port grounding + topology compatibility + feasibility checks
- deterministic ranking from structural coverage and closure quality
- remain explainable and reproducible

Workspace touch policy:
- may store graph diagnostics only inside graph-match workspaces
- no prompts

#### `greedy_hybrid.py`
Purpose:
- combine semantic and structural evidence greedily, but remove global optimization

Implementation direction:
- score local candidates with weighted semantic + structural score
- commit selections task-by-task / edge-by-edge
- no revision/global search; one forward greedy pass with optional simple repair

Workspace touch policy:
- may store decision traces and weights only inside greedy-hybrid workspaces

### Stage 3 modules

#### `static_rule_scheduler.py`
Purpose:
- deterministic schedule templates and predefined coordination rules

Implementation direction:
- fixed schedule family chosen by small rule set (single-FMU, chain, star, monitor-loop, etc.)
- static step size defaults and deterministic connection ordering
- reuse validator and config builders

Workspace touch policy:
- may store schedule templates only inside static-scheduler workspaces

#### `greedy_multirate_scheduler.py`
Purpose:
- heuristic multi-rate schedule based on local step-size compatibility

Implementation direction:
- infer preferred step sizes from FMU capability metadata
- assign communication steps greedily and build a deterministic multi-rate execution graph
- still no global optimization

Workspace touch policy:
- may store multirate heuristics only inside greedy-multirate workspaces

#### `llm_generated_script.py`
Purpose:
- construct orchestration script/config directly from selected units + interface metadata

Implementation direction:
- generate the final `UNIFIED_SOLUTION_V1` orchestration payload fields under `simulation_config.meta["final_solution_payload"]`
- let evaluator consume that payload as the authority for stage3 fields in `predicted_solution.json`
- keep outer `CompositionResult` / `SimulationConfig` shape evaluator-compatible without reusing the main `compose(...)` middleware path
- include deterministic fallback when generation is incomplete

Workspace touch policy:
- may read/write prompts, script templates, and generation traces only in its dedicated workspaces
- must not leak generated scratch files into repo root

## Common helper responsibilities

### `common/paths.py`
Defines:
- repo-root-relative path helpers
- per-method workspace resolution
- official artifact path helpers

### `common/workspace.py`
Defines:
- workspace bootstrap helpers
- safe subdir creation (`prompts/`, `runs/`, `cache/`)
- method workspace guard checks

### `common/current_stages.py`
Defines:
- wrappers for current pipeline stage1/stage2/stage3 so ablations can mix baseline modules with current modules cleanly

### `common/bundle_factory.py`
Defines:
- `build_bundle(...)`
- config normalization helpers
- metadata injection for method name / workspace root

### `common/naming.py`
Defines:
- stable bundle ids
- stage module names
- human-readable method titles

### `common/io.py`
Defines:
- small safe helpers for JSON/text read/write under method workspaces only

## Bundle registration plan

`baseline/__init__.py` should eventually import all bundle modules so registration happens once via side effects.

`evaluator/runner.py` should import `baseline` once, near the existing current bundle import, so all baseline bundles register automatically.

## Minimal changes needed outside `baseline/`

1. Add `import baseline  # noqa: F401` in `evaluator/runner.py`.
2. Optionally add bundle names to evaluator README examples.

No other evaluator API changes should be required.

## Recommended implementation order

### Phase 0 — scaffold and boundaries
- create common path/workspace helpers
- create per-method workspace directories + README stubs
- create bundle stubs
- wire evaluator import path
- ensure `available_bundles()` lists all methods even before logic is complete

### Phase 1 — easiest working modules
- `top1_llm.py`
- `semantic_retrieval_only.py`
- `static_rule_scheduler.py`
- B2 bundle wiring + smoke test

### Phase 2 — deterministic structural variants
- `rule_template.py`
- `graph_match_only.py`
- B1 bundle wiring + smoke test
- `greedy_multirate_scheduler.py`

### Phase 3 — graph-aware variants
- `heuristic_neighborhood.py`
- `greedy_hybrid.py`
- B3 bundle wiring + smoke test

### Phase 4 — highest-fragility method
- `llm_generated_script.py`
- final ablation wiring + smoke tests

## Validation plan per implementation step

For each new atomic module:

1. dataclass shape sanity
2. one benchmark single-FMU smoke run
3. one multi-FMU/manual smoke run
4. one evaluator run through the registered bundle
5. save official results only under `evaluator/runs/<bundle>_<timestamp>/`

For each bundle:

1. registration visible in `available_bundles()`
2. workspace root resolved correctly
3. no unintended file writes outside method workspace / evaluator runs

## Naming proposal for evaluator bundles

- `baseline_b1_rule_sequential`
- `baseline_b2_llm_retrieval_rule`
- `baseline_b3_graph_aware`
- `ablation_stage1_top1_llm`
- `ablation_stage1_rule_template`
- `ablation_stage1_heuristic_neighborhood`
- `ablation_stage2_semantic_retrieval_only`
- `ablation_stage2_graph_match_only`
- `ablation_stage2_greedy_hybrid`
- `ablation_stage3_static_rule_scheduler`
- `ablation_stage3_greedy_multirate`
- `ablation_stage3_llm_generated_script`

## Slice backlog for cron

1. `common/paths.py` + `common/workspace.py`
2. workspace README stubs for all 12 methods
3. `common/current_stages.py` + `common/bundle_factory.py`
4. bundle stubs + evaluator import hook
5. `top1_llm.py`
6. `semantic_retrieval_only.py`
7. `static_rule_scheduler.py`
8. B2 wiring + smoke test
9. `rule_template.py`
10. `graph_match_only.py`
11. B1 wiring + smoke test
12. `greedy_multirate_scheduler.py`
13. stage3 multirate ablation wiring + smoke test
14. `heuristic_neighborhood.py`
15. `greedy_hybrid.py`
16. B3 wiring + smoke test
17. `llm_generated_script.py`
18. final ablation wiring + smoke matrix

## Guardrails

- Do not modify `pipeline/` unless a compatibility bug blocks bundle reuse.
- Do not start work if the tmux/Codex worker is still mid-edit.
- Keep each cron slice narrow enough to finish, test, and commit in one run.
- Prefer deterministic implementations for baselines unless the method explicitly requires LLM generation.
- Preserve evaluator input/output schema exactly.
- Every method may write only to its own workspace and to official evaluator run directories.
- No cross-method scratch sharing except through `baseline/common/` checked-in helpers.
