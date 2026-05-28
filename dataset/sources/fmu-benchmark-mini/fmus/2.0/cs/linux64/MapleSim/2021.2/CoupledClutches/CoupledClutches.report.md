# FMU Semantic Report: `CoupledClutches.fmu`

## Model Info
- modelName: `CoupledClutches`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `MapleSim (1579660/1578573)`

## Selected Interface
- inputs (1): `inputs`
- outputs observed (4 from outputs): `outputs[1]`, `outputs[2]`, `outputs[3]`, `outputs[4]`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.01`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.03775 .. 0.151`

## Variable Features (key)
### `outputs[1]`
- mean/std/ptp: `4.81` / `2.465` / `7.801`
- rise/settling/overshoot: `0.67` / `None` / `0.0371`
- dominant_frequency_hz: `0.6623` (power ratio `0.876`)
- labels: `integrator-like, oscillatory`

### `outputs[2]`
- mean/std/ptp: `2.634` / `0.8397` / `3.928`
- rise/settling/overshoot: `0.15` / `1.06` / `0.75`
- dominant_frequency_hz: `0.6623` (power ratio `0.52`)
- labels: `oscillatory`

### `outputs[3]`
- mean/std/ptp: `1.506` / `1.12` / `2.619`
- rise/settling/overshoot: `0.39000000000000007` / `1.04` / `0.00897`
- dominant_frequency_hz: `0.6623` (power ratio `0.777`)
- labels: `oscillatory`

### `outputs[4]`
- mean/std/ptp: `1.363` / `1.153` / `2.665`
- rise/settling/overshoot: `0.42000000000000004` / `1.04` / `0.00882`
- dominant_frequency_hz: `0.6623` (power ratio `0.755`)
- labels: `oscillatory`
