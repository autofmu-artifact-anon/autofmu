# FMU Semantic Report: `sb_pendulum.fmu`

## Model Info
- modelName: `sb_pendulum`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `angle`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `angle`
- mean/std/ptp: `-1.533` / `0.7191` / `2.878`
- rise/settling/overshoot: `0.07199999999999995` / `None` / `3.47`
- dominant_frequency_hz: `3.906` (power ratio `0.945`)
- labels: `integrator-like, oscillatory`
