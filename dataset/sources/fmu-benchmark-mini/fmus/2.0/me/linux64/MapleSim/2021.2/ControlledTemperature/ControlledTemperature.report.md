# FMU Semantic Report: `ControlledTemperature.fmu`

## Model Info
- modelName: `ControlledTemperature`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `MapleSim (1579660/1578573)`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `outputs[1]`, `outputs[2]`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.32 .. 1.28`

## Variable Features (key)
### `outputs[1]`
- mean/std/ptp: `37.9` / `9.606` / `25`
- rise/settling/overshoot: `4.800000000000001` / `7.9` / `2.67e-10`
- dominant_frequency_hz: `0.07813` (power ratio `0.938`)
- labels: `oscillatory`

### `outputs[2]`
- mean/std/ptp: `37.84` / `9.695` / `31`
- rise/settling/overshoot: `4.8` / `None` / `0.0382`
- dominant_frequency_hz: `0.07813` (power ratio `0.915`)
- labels: `integrator-like, oscillatory`
