# FMU Semantic Report: `van der Pol oscillator.fmu`

## Model Info
- modelName: `van der Pol oscillator`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `x0`, `x1`

## Probe Scenario
- start_time: `0.0`
- stop_time: `20.0`
- step_size: `0.1`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.1675 .. 0.67`

## Variable Features (key)
### `x0`
- mean/std/ptp: `-0.09596` / `1.541` / `4.433`
- rise/settling/overshoot: `1.3000000000000003` / `None` / `0.215`
- dominant_frequency_hz: `0.1493` (power ratio `0.607`)
- labels: `integrator-like, oscillatory`

### `x1`
- mean/std/ptp: `-0.127` / `1.4` / `5.618`
- rise/settling/overshoot: `4.3` / `None` / `1.24`
- dominant_frequency_hz: `0.1493` (power ratio `0.512`)
- labels: `integrator-like, oscillatory`
