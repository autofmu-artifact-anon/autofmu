# FMU Semantic Report: `des56_original.fmu`

## Model Info
- modelName: `des56_original`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `HIF2VP`

## Selected Interface
- inputs (3): `indata_0031`, `indata_3263`, `inkey_0031`
- outputs observed (5 from outputs): `outdata_0031`, `outdata_3263`, `c17_out_0031`, `c17_out_3263`, `b1_out`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.025`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone, saturation`
- recommended_step_size_range: `0.0125 .. 0.05`

## Variable Features (key)
### `outdata_0031`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `outdata_3263`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `c17_out_0031`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `c17_out_3263`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `b1_out`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone, saturation`
