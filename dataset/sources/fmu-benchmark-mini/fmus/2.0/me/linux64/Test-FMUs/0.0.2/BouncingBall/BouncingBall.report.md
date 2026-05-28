# FMU Semantic Report: `BouncingBall.fmu`

## Model Info
- modelName: `BouncingBall`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `h`, `v`

## Probe Scenario
- start_time: `0.0`
- stop_time: `3.0`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `h`
- mean/std/ptp: `0.2082` / `0.2658` / `1`
- rise/settling/overshoot: `0.215` / `2.21` / `-0`
- dominant_frequency_hz: `3.906` (power ratio `0.893`)
- labels: `oscillatory`

### `v`
- mean/std/ptp: `-0.337` / `1.392` / `7.545`
- rise/settling/overshoot: `0.0` / `2.604` / `2.12`
- dominant_frequency_hz: `3.906` (power ratio `0.576`)
- labels: `oscillatory`
