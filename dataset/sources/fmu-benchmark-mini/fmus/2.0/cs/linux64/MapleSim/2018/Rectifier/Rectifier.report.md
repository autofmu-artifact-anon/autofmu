# FMU Semantic Report: `Rectifier.fmu`

## Model Info
- modelName: `Rectifier`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `MapleSim (1357016/1357197/1357197)`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `outputs`

## Probe Scenario
- start_time: `0.0`
- stop_time: `0.1`
- step_size: `1e-07`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `6.4e-07 .. 2.56e-06`

## Variable Features (key)
### `outputs`
- mean/std/ptp: `262.3` / `4.97` / `43.44`
- rise/settling/overshoot: `0.0` / `None` / `24.3`
- dominant_frequency_hz: `3.906e+04` (power ratio `0.95`)
- labels: `integrator-like, oscillatory`
