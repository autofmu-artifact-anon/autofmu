# FMU Semantic Report: `sb_ActiveRC.fmu`

## Model Info
- modelName: `sb_ActiveRC`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs (1): `Signal_in`
- outputs observed (2 from outputs): `V_in`, `V_out`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.1`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.2525 .. 1.01`

## Variable Features (key)
### `V_in`
- mean/std/ptp: `0.203` / `0.4569` / `1`
- rise/settling/overshoot: `0.0` / `3.0000000000000004` / `0`
- dominant_frequency_hz: `0.09901` (power ratio `0.796`)
- labels: `oscillatory`

### `V_out`
- mean/std/ptp: `0.09117` / `0.3251` / `0.903`
- rise/settling/overshoot: `2.7` / `8.799999999999999` / `0.00764`
- dominant_frequency_hz: `0.09901` (power ratio `0.795`)
- labels: `oscillatory`
