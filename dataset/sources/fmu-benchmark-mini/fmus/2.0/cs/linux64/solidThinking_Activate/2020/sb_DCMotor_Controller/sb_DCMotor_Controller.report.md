# FMU Semantic Report: `sb_DCMotor_Controller.fmu`

## Model Info
- modelName: `sb_DCMotor_Controller`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Activate`

## Selected Interface
- inputs (1): `Reference_angle`
- outputs observed (3 from outputs): `DCMotor_angle`, `DCMotot_speed`, `controller_output`

## Probe Scenario
- start_time: `0.0`
- stop_time: `10.0`
- step_size: `0.01`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.064 .. 0.256`

## Variable Features (key)
### `DCMotor_angle`
- mean/std/ptp: `0.171` / `0.4508` / `1.21`
- rise/settling/overshoot: `4.25` / `7.66` / `0.211`
- dominant_frequency_hz: `0.3906` (power ratio `0.933`)
- labels: `oscillatory`

### `DCMotot_speed`
- mean/std/ptp: `0.05002` / `0.3282` / `1.472`
- rise/settling/overshoot: `0.0` / `8.620000000000001` / `2.65`
- dominant_frequency_hz: `0.3906` (power ratio `0.923`)
- labels: `oscillatory`

### `controller_output`
- mean/std/ptp: `0.4995` / `80.3` / `890`
- rise/settling/overshoot: `0.0` / `7.96` / `73.2`
- dominant_frequency_hz: `0.3906` (power ratio `0.923`)
- labels: `oscillatory`
