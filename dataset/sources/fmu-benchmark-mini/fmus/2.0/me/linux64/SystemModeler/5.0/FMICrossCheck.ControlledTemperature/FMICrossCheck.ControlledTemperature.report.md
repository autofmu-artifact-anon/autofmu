# FMU Semantic Report: `FMICrossCheck.ControlledTemperature.fmu`

## Model Info
- modelName: `FMICrossCheck.ControlledTemperature`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Wolfram SystemModeler 5.0.0.10`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `TRes`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.002`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0128 .. 0.0512`

## Variable Features (key)
### `TRes`
- mean/std/ptp: `310.6` / `9.776` / `31`
- rise/settling/overshoot: `4.836` / `None` / `0.0387`
- dominant_frequency_hz: `1.953` (power ratio `0.906`)
- labels: `integrator-like, oscillatory`
