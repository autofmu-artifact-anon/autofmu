# FMU Semantic Report: `ControlledTemperature.fmu`

## Model Info
- modelName: `ControlledTemperature`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `MapleSim (1087698/1087698/1087698)`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `outputs[1]`, `outputs[2]`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `outputs[1]`
- mean/std/ptp: `37.5` / `9.683` / `25`
- rise/settling/overshoot: `4.800000000000001` / `7.88` / `0`
- dominant_frequency_hz: `3.906` (power ratio `0.948`)
- labels: `oscillatory`

### `outputs[2]`
- mean/std/ptp: `37.45` / `9.784` / `31.01`
- rise/settling/overshoot: `4.843` / `None` / `0.0388`
- dominant_frequency_hz: `3.906` (power ratio `0.93`)
- labels: `integrator-like, oscillatory`
