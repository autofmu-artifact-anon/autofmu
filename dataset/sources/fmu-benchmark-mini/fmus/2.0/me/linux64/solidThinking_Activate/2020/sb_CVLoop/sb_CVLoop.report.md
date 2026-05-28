# FMU Semantic Report: `sb_CVLoop.fmu`

## Model Info
- modelName: `sb_CVLoop`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (5 from outputs): `Output1`, `Output2`, `Output3`, `Output4`, `Output5`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.0001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `discrete-event-heavy, integrator-like, oscillatory`
- recommended_step_size_range: `2.416e-05 .. 9.664e-05`

## Variable Features (key)
### `Output1`
- mean/std/ptp: `85.49` / `23.88` / `155`
- rise/settling/overshoot: `0.0` / `None` / `2.03`
- dominant_frequency_hz: `1035` (power ratio `0.942`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`

### `Output2`
- mean/std/ptp: `40.94` / `47.07` / `307.2`
- rise/settling/overshoot: `0.0` / `None` / `13.6`
- dominant_frequency_hz: `1035` (power ratio `0.947`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`

### `Output3`
- mean/std/ptp: `6.067` / `18.47` / `148.1`
- rise/settling/overshoot: `9.999999999999994e-05` / `None` / `139`
- dominant_frequency_hz: `1035` (power ratio `0.943`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`

### `Output4`
- mean/std/ptp: `16.83` / `15.79` / `54.22`
- rise/settling/overshoot: `0.0` / `None` / `8.79`
- dominant_frequency_hz: `1035` (power ratio `0.949`)
- labels: `integrator-like, oscillatory`

### `Output5`
- mean/std/ptp: `23.7` / `9.869` / `42.29`
- rise/settling/overshoot: `0.001599999999999999` / `None` / `6.22`
- dominant_frequency_hz: `1035` (power ratio `0.941`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`
