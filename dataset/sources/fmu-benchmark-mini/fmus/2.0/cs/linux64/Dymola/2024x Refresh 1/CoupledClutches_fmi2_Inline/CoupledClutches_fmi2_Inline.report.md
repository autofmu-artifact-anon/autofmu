# FMU Semantic Report: `CoupledClutches_fmi2_Inline.fmu`

## Model Info
- modelName: `CoupledClutches_fmi2_Inline`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Dymola Version 2024x Refresh 1, 2024-04-12 (using Inline integration method Explicit Euler and internal fixed step size 0.001)`

## Selected Interface
- inputs (1): `step2`
- outputs observed (4 from outputs): `J1_w`, `J2_w`, `J3_w`, `J4_w`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `J1_w`
- mean/std/ptp: `4.835` / `2.435` / `7.741`
- rise/settling/overshoot: `0.781` / `None` / `0.0375`
- dominant_frequency_hz: `3.906` (power ratio `0.825`)
- labels: `integrator-like, oscillatory`

### `J2_w`
- mean/std/ptp: `2.614` / `0.7963` / `3.826`
- rise/settling/overshoot: `0.15` / `1.049` / `0.683`
- dominant_frequency_hz: `3.906` (power ratio `0.919`)
- labels: `oscillatory`

### `J3_w`
- mean/std/ptp: `1.514` / `1.104` / `2.599`
- rise/settling/overshoot: `0.38700000000000007` / `1.032` / `0.00943`
- dominant_frequency_hz: `3.906` (power ratio `0.919`)
- labels: `oscillatory`

### `J4_w`
- mean/std/ptp: `1.355` / `1.124` / `2.6`
- rise/settling/overshoot: `0.41200000000000003` / `1.032` / `0.00943`
- dominant_frequency_hz: `3.906` (power ratio `0.921`)
- labels: `oscillatory`
