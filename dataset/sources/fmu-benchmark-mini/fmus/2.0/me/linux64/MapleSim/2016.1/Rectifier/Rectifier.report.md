# FMU Semantic Report: `Rectifier.fmu`

## Model Info
- modelName: `Rectifier`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `MapleSim (1132425/1132425/1132425)`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `outputs`

## Probe Scenario
- start_time: `0.0`
- stop_time: `0.1`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `discrete-event-heavy, integrator-like, oscillatory`
- recommended_step_size_range: `7.224e-05 .. 0.000289`

## Variable Features (key)
### `outputs`
- mean/std/ptp: `264.5` / `4.983` / `43.37`
- rise/settling/overshoot: `0.0004934424799732451` / `None` / `7.38`
- dominant_frequency_hz: `346.1` (power ratio `0.4`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`
