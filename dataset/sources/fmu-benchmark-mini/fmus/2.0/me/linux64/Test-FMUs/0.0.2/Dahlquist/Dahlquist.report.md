# FMU Semantic Report: `Dahlquist.fmu`

## Model Info
- modelName: `Dahlquist`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `x`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.1`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.2525 .. 1.01`

## Variable Features (key)
### `x`
- mean/std/ptp: `0.09901` / `0.2057` / `1`
- rise/settling/overshoot: `2.0` / `4.2` / `2.78e-05`
- dominant_frequency_hz: `0.09901` (power ratio `0.968`)
- labels: `oscillatory`
