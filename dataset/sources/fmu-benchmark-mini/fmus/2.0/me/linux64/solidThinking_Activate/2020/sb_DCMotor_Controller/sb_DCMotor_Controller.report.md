# FMU Semantic Report: `sb_DCMotor_Controller.fmu`

## Model Info
- modelName: `sb_DCMotor_Controller`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs (1): `Reference_angle`
- outputs observed (3 from outputs): `DCMotor_angle`, `DCMotot_speed`, `controller_output`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `discrete-event-heavy, oscillatory`
- recommended_step_size_range: `0.0005333 .. 0.002133`

## Variable Features (key)
### `DCMotor_angle`
- mean/std/ptp: `0.1641` / `0.4536` / `1.21`
- rise/settling/overshoot: `4.24` / `7.65` / `0.208`
- dominant_frequency_hz: `3.906` (power ratio `0.949`)
- labels: `oscillatory`

### `DCMotot_speed`
- mean/std/ptp: `0.05056` / `0.3286` / `1.477`
- rise/settling/overshoot: `0.0` / `8.616` / `2.64`
- dominant_frequency_hz: `3.906` (power ratio `0.949`)
- labels: `discrete-event-heavy, oscillatory`

### `controller_output`
- mean/std/ptp: `0.4803` / `80.58` / `890`
- rise/settling/overshoot: `0.0` / `7.97` / `76.7`
- dominant_frequency_hz: `46.88` (power ratio `0.327`)
- labels: `discrete-event-heavy, oscillatory`
