# Pipeline Deprecation Inventory

Generated on 2026-03-10.

## Scope

- True entrypoint: `pipeline/main.py`
- Main-path chain: `_cli -> run_case -> run_pipeline -> stage1.decompose -> stage2.match -> stage3.compose`
- `ablation` modules and symbols are intentionally excluded from deprecation candidates.
- `pipeline/resources/generated_adapters/` is treated as generated output, not hand-maintained source.

## Test Files Removed

The following 11 test files were deleted from `pipeline/`:

- `pipeline/stage1_decomposition/test_conformal_semantics.py`
- `pipeline/stage1_decomposition/test_grounding_semantics.py`
- `pipeline/stage1_decomposition/test_stage1_semantics.py`
- `pipeline/stage2_matching/pipeline/planning/test_planning.py`
- `pipeline/stage2_matching/test_smoke.py`
- `pipeline/stage3_composition/pipeline/evaluation/test_interface_coverage.py`
- `pipeline/stage3_composition/pipeline/execution/test_execution_engine_simopt.py`
- `pipeline/stage3_composition/self_check_case_test.py`
- `pipeline/stage3_composition/test_smoke.py`
- `pipeline/test_e2e_smoke.py`
- `pipeline/test_llm_safeguards.py`

## Main-Path Runtime Surface

These modules remain on the supported `pipeline.main` path and should be treated as the active codebase:

- `pipeline/main.py`
  - `_cli`, `run_case`, `run_pipeline`, `_build_predicted_solution`
- `pipeline/dataset_loader.py`
  - `load_case_from_dataset -> load_case -> _mbse_context_from_payload -> _port_from_payload`
- `pipeline/fmu_loader.py`
  - `load_fmu_library -> _expand / _capabilities_from_blob / _ports_from_blob`
- `pipeline/llm_guidance.py`
  - shared prompt and normalization helpers used by Stage 1, Stage 2, and Stage 3
- `pipeline/llm_client.py`
  - `chat_json` plus its internal request/response helpers
- `pipeline/stage1_decomposition/`
  - public entry: `decompose`
  - active support modules: `calibration.py`, `conformal.py`, `grounding.py`, `decomposer.py`
- `pipeline/stage2_matching/`
  - public entry: `match`
  - active support modules: `feasibility.py`, `graph_builder.py`, `revision.py`, `scoring.py`, `transport.py`, `matcher.py`
- `pipeline/stage3_composition/`
  - public entry: `compose`
  - active support modules: `adapter_artifact.py`, `adapter_builder.py`, `composer.py`, `gcd_utils.py`, `graph_utils.py`, `loop_wrappers.py`, `middleware.py`, `ports.py`, `schedule_spec.py`, `scheduler.py`, `validator.py`

## Removed In First Cleanup Batch

These symbols were removed after confirming they are not called anywhere in `pipeline/` outside this inventory:

| Symbol | Location | Removal reason | Replacement / note |
| --- | --- | --- | --- |
| `load_fmus_by_ids` | `pipeline/fmu_loader.py` | `尚未接入主入口` | No supported caller on `pipeline.main` path |
| `adapter_spec_to_fmu` | `pipeline/stage3_composition/middleware.py` | `已有替代实现` | Replaced by `composer.py`'s active `_adapter_to_runtime_fmu` path |
| `adapter_to_runtime_fmu` | `pipeline/stage3_composition/middleware.py` | `已有替代实现` | Replaced by `composer.py`'s active `_adapter_to_runtime_fmu` path |
| `units_compatible` | `pipeline/stage3_composition/ports.py` | `尚未接入主入口` | No supported caller on main path or legacy path |
| `types_compatible` | `pipeline/stage3_composition/ports.py` | `尚未接入主入口` | No supported caller on main path or legacy path |
| `topology.py` | `pipeline/stage3_composition/topology.py` | `尚未接入主入口` | Entire module unused |
| `tiebreaker.py` | `pipeline/stage3_composition/tiebreaker.py` | `尚未接入主入口` | Entire module unused; documented hook never existed in `compose()` |

Notes:

- `tiebreaker.py` was also contract-drift residue: its docstring claimed callers could pass `tiebreaker=...` into `compose()`, but `pipeline/stage3_composition/composer.py` never accepted that parameter.
- `middleware.py` and `composer.py` previously carried overlapping adapter-to-runtime-FMU conversion logic. The `middleware` variants were removed because the supported path already goes through `composer.py`.

## Legacy / Off-Main-Path Subtrees Removed

The following legacy subtrees were deleted after confirming they were off the supported `pipeline.main` path:

- `pipeline/stage1_decomposition/pipeline/`
- `pipeline/stage2_matching/pipeline/`
- `pipeline/stage3_composition/pipeline/`

Classification rules:

- `尚未接入主入口`: only used inside these legacy trees and never reached from `pipeline.main`
- `已有替代实现`: legacy behavior exists, but supported main path already does the job elsewhere
- `重复/覆盖残留`: later definition shadows earlier code in the same module

Resolved exception:

- `pipeline/stage2_matching/pipeline/planning/adapter_fmu.py` was previously kept alive by a dynamic load from `pipeline/stage3_composition/adapter_artifact.py`.
- That builder has been moved onto the supported module path as `pipeline/stage3_composition/adapter_builder.py`, so the legacy file and its parent subtree could be deleted.

No remaining off-main-path runtime dependencies are currently known on the supported `pipeline.main` path.

## Duplicate / Shadowed Residue

The first cleanup batch also removed an internal duplicate block from `pipeline/stage1_decomposition/grounding.py`:

- `_build_signal_indexes`
- `_signal_owner_components`
- `_signal_supported_by_components`

Removal reason: `重复/覆盖残留`

The deleted definitions were already shadowed by later definitions in the same file, so runtime behavior stayed with the later block.

## Variables

No confirmed unread module-level variables were found on the supported main path.

Current residue is function- and module-oriented, not global-variable-oriented. Shared globals such as `BASE_URL`, `API_KEY`, `MODEL`, `LLM_ENABLED`, and `_CAMEL_RE_*` are still referenced.

## Next Simplification Sequence

1. Keep `pipeline.main` green after the legacy subtree removal by re-running targeted Stage 3 adapter artifact checks and static import searches.
2. Continue dead-code sweeps only on modules still present on the supported main path.
3. Treat any future `stage*/pipeline/` reintroduction as unsupported unless it is wired into `pipeline.main` and documented here.
