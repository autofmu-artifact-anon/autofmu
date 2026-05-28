# FMU Semantic Report: `sb_pendulum.fmu`

## Model Info
- modelName: `sb_pendulum`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `angle`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.04208 .. 0.1683`

## Variable Features (key)
### `angle`
- mean/std/ptp: `-1.526` / `0.7236` / `2.874`
- rise/settling/overshoot: `0.09999999999999998` / `None` / `2.68`
- dominant_frequency_hz: `0.5941` (power ratio `0.567`)
- labels: `integrator-like, oscillatory`
