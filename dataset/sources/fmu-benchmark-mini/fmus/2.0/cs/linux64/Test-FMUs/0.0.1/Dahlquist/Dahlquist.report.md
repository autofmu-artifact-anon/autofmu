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
- step_size: `0.05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.2512 .. 1.005`

## Variable Features (key)
### `x`
- mean/std/ptp: `0.0995` / `0.2028` / `1`
- rise/settling/overshoot: `2.1500000000000004` / `4.25` / `3.83e-05`
- dominant_frequency_hz: `0.0995` (power ratio `0.966`)
- labels: `oscillatory`
