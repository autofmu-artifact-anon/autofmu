# FMU Semantic Report: `sb_Boocwen.fmu`

## Model Info
- modelName: `sb_Boocwen`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (1 from outputs): `Output`

## Probe Scenario
- start_time: `0.0`
- stop_time: `0.1`
- step_size: `0.0001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.00064 .. 0.00256`

## Variable Features (key)
### `Output`
- mean/std/ptp: `2.071e-06` / `6.524e-06` / `1.89e-05`
- rise/settling/overshoot: `0.0066999999999999985` / `None` / `0.341`
- dominant_frequency_hz: `39.06` (power ratio `0.923`)
- labels: `integrator-like, oscillatory`
