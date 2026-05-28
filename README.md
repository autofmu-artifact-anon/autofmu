# AutoFMU Reproducibility Package

This package contains the code, dataset, case study material, and precomputed
experiment outputs for the paper:

> AutoFMU: Verifying System Models via Automated Co-Simulation Construction
> using Large Language Models

The main goal of this README is to make the artifact usable without reading the
source code first. It explains how to reproduce the full 13-method experiment,
how to rerun one method or one case, and how to run the ship-propulsion case
study.

## Package Layout

```text
.
+-- pipeline/                   # AutoFMU pipeline implementation
+-- evaluator/                  # Batch evaluation, scoring, aggregation
+-- baseline/                   # Baselines and ablation method bundles
+-- dataset/                    # Unified dataset: 181 assets, 151 cases
+-- reference_case/             # Ship-propulsion case study
+-- runs/                       # Precomputed paper-run outputs
+-- requirements.txt            # Minimal dependency notes
+-- release_manifest.json       # Release metadata
```

The shipped precomputed run is `all13_rerun_20260322T144536Z`.

Important precomputed artifacts:

- `runs/raw/`: full per-method, per-case evaluator outputs.
- `runs/logs/`: logs for each of the 13 method runs.
- `runs/cross_method_summary.json`: penalty-aligned cross-method metrics.
- `runs/paper_table.csv`: compact table generated from the cross-method summary.

## Setup

Use Python 3.10 or newer. The core pipeline uses the Python standard library,
but evaluator execution needs FMU simulation support.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install fmpy numpy matplotlib
```

`matplotlib` is only needed for the optional heatmap figure. `numpy` is also
used by the case study script.

LLM-backed stages use an OpenAI-compatible chat-completions endpoint when
credentials are available. If no key is configured, or if a request fails, the
code falls back to deterministic logic where implemented.

Optional environment variables:

```bash
export PIPELINE_LLM_API_KEY="..."
export PIPELINE_LLM_BASE_URL="https://api.openai.com"
export PIPELINE_LLM_MODEL="GLM-5"

# Alternative key name supported by pipeline/llm_client.py
export OPENAI_API_KEY="..."

# Disable runtime LLM calls for offline reproduction
export PIPELINE_ENABLE_LLM=0
```

## Quick Verification

From the package root, inspect the shipped paper table:

```bash
head -n 5 runs/paper_table.csv
```

Validate the dataset and FMU-library manifest:

```bash
python3 -m dataset.tools.validate_dataset \
  --dataset-root dataset \
  --library-root pipeline/resources/fmu_library
```

The expected dataset size is 181 assets and 151 cases.

Run one small evaluator job:

```bash
python3 -m evaluator.cli \
  --case-id case_bench_fmu-001280 \
  --bundle current_pipeline \
  --out-root runs/local_smoke \
  --experiment-id smoke_current_pipeline
```

The command writes artifacts under:

```text
runs/local_smoke/smoke_current_pipeline/
```

## Reproduce The Full Paper Experiment

The full experiment evaluates 13 method bundles over all 151 dataset cases.
Expect this to take a long time and to write substantial output.

The method bundles are:

```text
current_pipeline
baseline_b1_rule_sequential
baseline_b2_llm_retrieval_rule
baseline_b3_graph_aware
ablation_stage1_top1_llm
ablation_stage1_rule_template
ablation_stage1_heuristic_neighborhood
ablation_stage2_semantic_retrieval_only
ablation_stage2_graph_match_only
ablation_stage2_greedy_hybrid
ablation_stage3_static_rule_scheduler
ablation_stage3_greedy_multirate
ablation_stage3_llm_generated_script
```

Run all methods:

```bash
mkdir -p runs/local_full

for bundle in \
  current_pipeline \
  baseline_b1_rule_sequential \
  baseline_b2_llm_retrieval_rule \
  baseline_b3_graph_aware \
  ablation_stage1_top1_llm \
  ablation_stage1_rule_template \
  ablation_stage1_heuristic_neighborhood \
  ablation_stage2_semantic_retrieval_only \
  ablation_stage2_graph_match_only \
  ablation_stage2_greedy_hybrid \
  ablation_stage3_static_rule_scheduler \
  ablation_stage3_greedy_multirate \
  ablation_stage3_llm_generated_script
do
  python3 -m evaluator.cli \
    --all-cases \
    --bundle "$bundle" \
    --out-root runs/local_full \
    --experiment-id "local_full_${bundle}" \
    --resume
done
```

Each run produces:

```text
runs/local_full/local_full_<bundle>/
+-- experiment_summary.json
+-- summary.csv
+-- summary.jsonl
+-- summary.md
+-- <case-id>/
    +-- stage1.raw.json
    +-- stage2.raw.json
    +-- stage3.raw.json
    +-- predicted_solution.json
    +-- reference.json
    +-- execution.raw.json
    +-- metrics.json
    +-- run_status.json
    +-- generated_trajectory.csv
```

Aggregate the 13 experiment roots into one cross-method summary:

```bash
python3 -m evaluator.aggregate_cli \
  --experiment-root runs/local_full/local_full_current_pipeline \
  --experiment-root runs/local_full/local_full_baseline_b1_rule_sequential \
  --experiment-root runs/local_full/local_full_baseline_b2_llm_retrieval_rule \
  --experiment-root runs/local_full/local_full_baseline_b3_graph_aware \
  --experiment-root runs/local_full/local_full_ablation_stage1_top1_llm \
  --experiment-root runs/local_full/local_full_ablation_stage1_rule_template \
  --experiment-root runs/local_full/local_full_ablation_stage1_heuristic_neighborhood \
  --experiment-root runs/local_full/local_full_ablation_stage2_semantic_retrieval_only \
  --experiment-root runs/local_full/local_full_ablation_stage2_graph_match_only \
  --experiment-root runs/local_full/local_full_ablation_stage2_greedy_hybrid \
  --experiment-root runs/local_full/local_full_ablation_stage3_static_rule_scheduler \
  --experiment-root runs/local_full/local_full_ablation_stage3_greedy_multirate \
  --experiment-root runs/local_full/local_full_ablation_stage3_llm_generated_script \
  --out runs/local_full/cross_method_summary.json
```

Generate the table format used by the paper artifact:

```bash
python3 -m evaluator.gen_paper_table_csv \
  --input runs/local_full/cross_method_summary.json \
  --output runs/local_full/paper_table.csv
```

Optional heatmap:

```bash
python3 -m evaluator.plot_ablation_heatmap \
  --input runs/local_full/paper_table.csv \
  --output runs/local_full/ablation_heatmap.pdf
```

## Reproduce A Single Experiment

Run one method on all cases:

```bash
python3 -m evaluator.cli \
  --all-cases \
  --bundle current_pipeline \
  --out-root runs/local_single_method \
  --experiment-id current_pipeline_all_cases \
  --resume
```

Run one method on one case:

```bash
python3 -m evaluator.cli \
  --case-id case_bench_fmu-001280 \
  --bundle current_pipeline \
  --out-root runs/local_single_case \
  --experiment-id current_pipeline_case_001280
```

Run one method on selected cases:

```bash
python3 -m evaluator.cli \
  --case-id case_bench_fmu-001280 \
  --case-id case_dtaas_three_tank \
  --case-id case_manual_005 \
  --bundle current_pipeline \
  --out-root runs/local_selected_cases \
  --experiment-id current_pipeline_selected
```

Change `--bundle` to any method name listed in the full-experiment section to
rerun a baseline or ablation.

Useful evaluator flags:

- `--resume`: reuse completed case artifacts under the same experiment id.
- `--fail-fast`: stop after the first failed case.
- `--timeout-seconds 100`: set the per-case simulation timeout.
- `--disable-fallback`: disable selected Stage-2 fallback paths.
- `--disable-reference-bootstrap`: skip reference bootstrap overrides.

## Run The Pipeline Without The Evaluator

Use `pipeline.main` when you only want the pipeline output for one dataset case:

```bash
python3 -m pipeline.main \
  --case-id case_bench_fmu-001280 \
  --solution-out runs/local_pipeline/predicted_solution.json \
  --out runs/local_pipeline/pipeline_result.json
```

To also execute the generated simulation package:

```bash
python3 -m pipeline.main \
  --case-id case_bench_fmu-001280 \
  --solution-out runs/local_pipeline/predicted_solution.json \
  --execute-out runs/local_pipeline/execution.raw.json
```

The `--mode` argument supports:

```text
full
ablation_stage1
ablation_stage2
ablation_stage3
ablation_all
```

## Run The Case Study

The paper case study is a ship-propulsion system with a 14-block SysML
architecture, 18 candidate FMUs, 10 selected FMUs, and a 300-second five-phase
scenario.

Run the synthetic case-study simulation:

```bash
cd reference_case
python3 run_case_simulation.py
cd ..
```

Outputs:

```text
reference_case/output/simulated_timeseries.csv
reference_case/output/command_events.csv
```

The case-study inputs and reference artifacts are:

- `reference_case/system.sysml`: SysML architecture.
- `reference_case/requirement.json`: monitored signals and acceptance criteria.
- `reference_case/fmu_list.json`: 18 candidate FMUs.
- `reference_case/orchestration.json`: selected FMUs, connections, adapters, and schedule.
- `reference_case/ground_truth.json`: correct selections, rejected candidates, wrappers, and acceptance results.
- `reference_case/LOG.md`: concise trace of decomposition, matching, scheduling, and acceptance.

## Dataset And Library Notes

The unified dataset contains:

- 181 FMU assets.
- 151 verification cases.
- 107 simple cases and 44 complex cases.
- 137 benchmark single-FMU cases, 9 DTaaS multi-FMU cases, and 5 manual multi-FMU cases.

The FMU library manifest is:

```text
pipeline/resources/fmu_library/manifest.json
```

It points back to `dataset/assets/` through relative paths so the package does
not duplicate the full FMU library tree.

To materialize a standalone library tree:

```bash
python3 -m dataset.tools.build_pipeline_library \
  --dataset-root dataset \
  --library-root pipeline/resources/fmu_library
```

Some files under `dataset/assets/` are relative symlinks into `dataset/sources/`.
If you re-archive the package, prefer `tar.gz` over a plain zip so symlinks are
preserved.

## Troubleshooting

`ModuleNotFoundError: No module named 'fmpy'`

Install the evaluator runtime dependency:

```bash
python3 -m pip install fmpy
```

LLM calls time out or print fallback messages.

This is expected when the remote endpoint is unavailable or slow. The pipeline
uses deterministic fallbacks where implemented. For fully offline runs, set:

```bash
export PIPELINE_ENABLE_LLM=0
```

Full reproduction is slow or produces large outputs.

Use `--case-id` for a small run first, and keep local reruns under a separate
output directory such as `runs/local_full` so the shipped `runs/raw/` snapshot
remains intact.
