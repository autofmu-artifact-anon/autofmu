# Pipeline Resources

`fmu_library/` is the file-based FMU asset library used by Stage 2 matching.

It is built from `dataset/assets/` and intentionally excludes `.sysml` files.

`stage1_calibration.json` stores the held-out calibration artifact used by Stage 1 conformal filtering.

`generated_adapters/` is the output directory used by Stage 3 adapter materialization. It is created on demand during composition runs.
