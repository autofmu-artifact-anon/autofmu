# FMU Semantic Report: `CoupledClutches_fmi2_Dassl.fmu`

## Model Info
- modelName: `CoupledClutches_fmi2_Dassl`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Dymola Version 2025x, 2024-10-11 (using dassl with tolerance 0.0001)`

## Selected Interface
- inputs (1): `step2`
- outputs observed (4 from outputs): `J1_w`, `J2_w`, `J3_w`, `J4_w`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.0075`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.03769 .. 0.1508`

## Variable Features (key)
### `J1_w`
- mean/std/ptp: `4.84` / `2.444` / `7.739`
- rise/settling/overshoot: `0.6599999999999999` / `None` / `0.0385`
- dominant_frequency_hz: `0.6633` (power ratio `0.878`)
- labels: `integrator-like, oscillatory`

### `J2_w`
- mean/std/ptp: `2.611` / `0.8058` / `3.827`
- rise/settling/overshoot: `0.1575` / `1.05` / `0.672`
- dominant_frequency_hz: `0.6633` (power ratio `0.468`)
- labels: `oscillatory`

### `J3_w`
- mean/std/ptp: `1.512` / `1.106` / `2.598`
- rise/settling/overshoot: `0.39` / `1.035` / `0.00903`
- dominant_frequency_hz: `0.6633` (power ratio `0.781`)
- labels: `oscillatory`

### `J4_w`
- mean/std/ptp: `1.356` / `1.125` / `2.598`
- rise/settling/overshoot: `0.4125` / `1.035` / `0.00903`
- dominant_frequency_hz: `0.6633` (power ratio `0.757`)
- labels: `oscillatory`
