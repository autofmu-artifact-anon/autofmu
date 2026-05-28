# FMU Semantic Report: `CoupledClutches_fmi2_Ida.fmu`

## Model Info
- modelName: `CoupledClutches_fmi2_Ida`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`
- generationTool: `Dymola Version 2024x Refresh 1, 2024-05-07`

## Selected Interface
- inputs (1): `step2`
- outputs observed (4 from outputs): `J1_w`, `J2_w`, `J3_w`, `J4_w`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.0075`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.03769 .. 0.1508`

## Variable Features (key)
### `J1_w`
- mean/std/ptp: `4.837` / `2.445` / `7.737`
- rise/settling/overshoot: `0.6599999999999999` / `None` / `0.0381`
- dominant_frequency_hz: `0.6633` (power ratio `0.878`)
- labels: `integrator-like, oscillatory`

### `J2_w`
- mean/std/ptp: `2.611` / `0.8058` / `3.827`
- rise/settling/overshoot: `0.1575` / `1.05` / `0.673`
- dominant_frequency_hz: `0.6633` (power ratio `0.467`)
- labels: `oscillatory`

### `J3_w`
- mean/std/ptp: `1.512` / `1.105` / `2.597`
- rise/settling/overshoot: `0.39` / `1.035` / `0.00901`
- dominant_frequency_hz: `0.6633` (power ratio `0.781`)
- labels: `oscillatory`

### `J4_w`
- mean/std/ptp: `1.356` / `1.125` / `2.597`
- rise/settling/overshoot: `0.4125` / `1.035` / `0.00901`
- dominant_frequency_hz: `0.6633` (power ratio `0.757`)
- labels: `oscillatory`
