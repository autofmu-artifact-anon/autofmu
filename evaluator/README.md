# Evaluator

`evaluator/` wraps the active `pipeline/` main path and scores it against the
normalized `dataset/` contract.

Current flow:

1. Load a normalized case from `dataset/cases/<case-id>/`
2. Use `verification_requirement.json.text` as the end-to-end input
3. Run Stage 1 / 2 / 3 through the registered bundle
4. Build `predicted_solution.json`
5. Run the execution backend
6. Materialize source-ground-truth execution on demand when the dataset case has no archived canonical trajectory yet
7. Score only the end-to-end metrics

## Metrics

Per-case `metrics.json` contains only:

- `retrieval.top1_hit`
- `retrieval.topk_hit`
- `execution.success`
- `execution.execution_time_seconds`
- `numerical_fidelity.mae`
- `numerical_fidelity.rmse`
- `numerical_fidelity.nrmse`
- `decision.correct` (`true` means the case passes the loose decision gate)

Aggregation reports:

- `top1_hit_rate`
- `topk_hit_rate`
- `execution_success_rate`
- `mean_execution_time_seconds`
- `mae`
- `rmse`
- `nrmse`
- `trimmed_mae`
- `trimmed_rmse`
- `trimmed_nrmse`
- `decision_accuracy` (loose pass rate on decision-supported cases)
- `by_case_category.simple.*`
- `by_case_category.complex.*`

Aggregation semantics:

- In a single experiment `experiment_summary.json`, `mean_execution_time_seconds`
  is computed only over cases with `ok == true`, `execution.supported == true`,
  and `execution.success == true`.
- `decision_accuracy` is a loose pass rate, not a strict classification
  accuracy. For `trajectory_tolerance` cases, the pass gate is
  `numerical_fidelity.nrmse <= 0.05`. For `acceptance_criteria` cases, the pass
  gate is the DSL evaluation concluding `pass`.
- Cases are partitioned by `case.json.case_category` using the dataset's
  fixed-threshold hybrid rule:
  - `complex` if `ground_truth_asset_ids` count `> 1`
  - `complex` if single-FMU and summed ground-truth port count `>= 150`
  - otherwise `simple`
- When reading older experiment summaries, legacy row values
  `single_fmu` / `multi_fmu` are remapped into `simple` / `complex`.
- Single-experiment `mae` / `rmse` / `nrmse` are still method-local averages
  over that experiment's own numerically supported cases.
- Single-experiment `trimmed_mae` / `trimmed_rmse` / `trimmed_nrmse` drop the
  upper 5% of per-case numerical metric values within that experiment before
  averaging, so a few extreme cases do not dominate the mean.
- Cross-method comparison is only valid when every experiment summary points to
  the same `dataset_root`. The evaluator rejects mixed-dataset comparisons.
- For cross-method `top1_hit_rate`, `topk_hit_rate`, `execution_success_rate`,
  and `decision_accuracy`, the denominator is the aligned dataset case set from
  `dataset_root`, not the method-local `cases_scored` subset. Missing case rows,
  missing metrics, and unsupported decisions stay in the denominator and count
  as miss / failure / incorrect respectively.
- For cross-method `mean_execution_time_seconds`, the evaluator aligns methods
  on the subset of dataset cases where at least one method has a finite
  successful execution time. Missing or failed execution times are imputed with
  that case's maximum successful execution time observed over all methods.
- For cross-method `mae` / `rmse` / `nrmse`, do not compare the per-experiment
  values directly from different `experiment_summary.json` files. Use the
  cross-method aggregation entrypoint instead. It aligns methods on the subset
  of dataset cases where at least one method has finite numerical fidelity
  metrics, then imputes missing numerical metrics with the per-case maximum
  observed over all methods as a penalty.
- Cross-method `trimmed_mae` / `trimmed_rmse` / `trimmed_nrmse` use the same
  aligned case set and the same casewise-max penalties, then drop the globally
  worst 5% of case ids for each metric so every method is compared on the same
  truncated case subset.
- For cross-method `decision_accuracy`, the evaluator also recomputes stale
  materialized-reference labels from the archived reference execution when
  available before scoring correctness.

## Reference Truth

- Retrieval truth is read from `retrieval_reference.json`.
- `acceptable_asset_sets` is the scoring oracle.
- Benchmark duplicate assets use `oracle_mode=equivalence_class`; any acceptable singleton in that class counts as a hit.
- Numerical and decision truth primarily come from:
  - archived `ground_truth_trajectory.csv` / `verification_result.json`
  - or source-ground-truth solution execution materialized under the evaluator artifact directory for manual / DTaaS cases

## Execution Backends

The current executor uses:

- `fmpy_single` for executable benchmark single-FMU cases
- `mixed_cosim` for native multi-FMU, manual Python FMUs, and UniFMU-backed cases
- `rabbitmq_replay` for archived replay cases such as DRobotti and Flex Cell

## Output Layout

Each case directory contains:

```text
<experiment-id>/<case-id>/
  stage1.raw.json
  stage2.raw.json
  stage3.raw.json
  predicted_solution.json
  reference.json
  execution.raw.json
  metrics.json
  run_status.json
  generated_trajectory.csv   # when available
```

Experiment-level outputs:

```text
<experiment-id>/
  experiment_summary.json
  summary.jsonl
  summary.csv
  summary.md
```

Cross-experiment output:

```text
<out>.json
  schema = EVALUATOR_CROSS_METHOD_SUMMARY_V2
  aggregation_mode = casewise_max_penalty
  dataset_root
  aligned_case_ids
  common_case_ids
  cross_method_execution_time_case_ids
  cross_method_numerical_case_ids
  trimmed_numerical_fidelity_reference
  experiments[].cross_method_aggregate_metrics
```

## Decision Rules

`decision_rule.kind` is consumed directly from `verification_requirement.json`.

- `trajectory_tolerance`
  compares generated vs canonical trajectories on the unified time grid; the
  aggregated decision pass rate uses the loose evaluator gate
  `nrmse <= 0.05`
- `acceptance_criteria`
  evaluates the current manual-case metric DSL over the generated trajectory

Currently supported acceptance-criteria patterns:

- `max(signal)`
- `min(signal)`
- `within_range(signal)`
- `abs(signal) at t=...`
- `abs(lhs - rhs) at t=...`
- `max(abs(signal))_after_t=...`
- `max(abs(lhs - rhs))_after_t=...`
- `max(abs(lhs - rhs))_during_t=[..., ...]`
- `max(abs(wrap_to_pi(signal - constant)))_after_t=...`
- `max(abs(d(signal)/dt))`
- `max(signal)_over_all`

## CLI

Evaluate one case:

```bash
python3 -m evaluator.cli \
  --case-id case_bench_fmu-001280
```

Evaluate all normalized cases:

```bash
python3 -m evaluator.cli \
  --all-cases
```

Reuse already finished case artifacts under the same experiment id:

```bash
python3 -m evaluator.cli \
  --all-cases \
  --experiment-id full_run \
  --resume
```

Build a cross-method penalty-aligned summary from existing experiment roots:

```bash
python3 -m evaluator.aggregate_cli \
  --experiment-root evaluator/runs/current_run \
  --experiment-root evaluator/runs/baseline_run \
  --out evaluator/runs/current_vs_baseline_cross_method.json
```

## Notes

- `Top-K` uses Stage 2 asset-set candidates and scores them against the dataset
  oracle asset sets.
- Cross-method `common_case_ids` are kept only as a diagnostic/back-compat view
  of the intersection of emitted case rows. They do not drive denominators for
  the aligned comparison metrics.
- Cross-method `mean_execution_time_seconds` uses `casewise_max_penalty` over
  successful execution times: if a method has no successful finite execution
  time on a case but another method does, the missing value is replaced with
  that case's maximum successful execution time across methods.
- Cross-method `mae` / `rmse` / `nrmse` use `casewise_max_penalty`: if a method
  has no numerical metric on a case but another method does, the missing value
  is replaced with that case's maximum observed metric across methods.
- Cross-method `trimmed_mae` / `trimmed_rmse` / `trimmed_nrmse` reuse that same
  penalty-aligned case set, then exclude the top 5% highest-penalty case ids
  per metric for every method.
- Alias-aware CSV resolution is used for both time columns and signal columns.
- Per-case wall-clock time is recorded in `metrics.json` as
  `execution.execution_time_seconds`, measured around the end-to-end evaluator
  case rollout.
- Cases still execute in process order.
- `--timeout-seconds` now defaults to `100` and is enforced on each simulation
  execution. When the execution backend exceeds that limit, the evaluator marks
  the case as failed and records a timeout `execution.raw.json`.
