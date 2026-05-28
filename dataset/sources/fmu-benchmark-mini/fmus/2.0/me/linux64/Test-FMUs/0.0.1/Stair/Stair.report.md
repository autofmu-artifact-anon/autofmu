# FMU Semantic Report: `Stair.fmu`

## Model Info
- modelName: `Stair`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `counter`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.2512 .. 1.005`

## Variable Features (key)
### `counter`
- mean/std/ptp: `5.527` / `2.891` / `10`
- rise/settling/overshoot: `8.0` / `None` / `0.105`
- dominant_frequency_hz: `0.0995` (power ratio `0.912`)
- labels: `integrator-like, oscillatory`
