# FMU Semantic Report: `Van der Pol oscillator.fmu`

## Model Info
- modelName: `Van der Pol oscillator`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `x0`, `x1`

## Probe Scenario
- start_time: `0.0`
- stop_time: `20.0`
- step_size: `0.01`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.064 .. 0.256`

## Variable Features (key)
### `x0`
- mean/std/ptp: `-0.01346` / `1.44` / `4.056`
- rise/settling/overshoot: `0.72` / `None` / `2.04`
- dominant_frequency_hz: `0.3906` (power ratio `0.905`)
- labels: `integrator-like, oscillatory`

### `x1`
- mean/std/ptp: `0.0008638` / `1.442` / `5.385`
- rise/settling/overshoot: `5.12` / `None` / `0.409`
- dominant_frequency_hz: `0.3906` (power ratio `0.796`)
- labels: `integrator-like, oscillatory`
