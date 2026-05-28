# FMU Semantic Report: `Feedthrough.fmu`

## Model Info
- modelName: `Feedthrough`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`

## Selected Interface
- inputs (3): `real_continuous_in`, `real_discrete_in`, `int_in`
- outputs observed (4 from outputs): `real_continuous_out`, `real_discrete_out`, `int_out`, `bool_out`

## Probe Scenario
- start_time: `0.0`
- stop_time: `2.0`
- step_size: `0.01`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone, oscillatory`
- recommended_step_size_range: `0.05025 .. 0.201`

## Variable Features (key)
### `real_continuous_out`
- mean/std/ptp: `0.1965` / `0.4598` / `1`
- rise/settling/overshoot: `0.0` / `0.61` / `0`
- dominant_frequency_hz: `0.4975` (power ratio `0.798`)
- labels: `oscillatory`

### `real_discrete_out`
- mean/std/ptp: `0.1915` / `0.4619` / `1`
- rise/settling/overshoot: `0.0` / `0.62` / `0`
- dominant_frequency_hz: `0.4975` (power ratio `0.798`)
- labels: `oscillatory`

### `int_out`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `bool_out`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`
