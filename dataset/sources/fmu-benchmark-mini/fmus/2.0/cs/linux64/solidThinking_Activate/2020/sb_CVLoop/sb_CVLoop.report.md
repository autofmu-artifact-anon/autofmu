# FMU Semantic Report: `sb_CVLoop.fmu`

## Model Info
- modelName: `sb_CVLoop`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (5 from outputs): `Output1`, `Output2`, `Output3`, `Output4`, `Output5`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.02104 .. 0.08417`

## Variable Features (key)
### `Output1`
- mean/std/ptp: `88.89` / `22.2` / `97.46`
- rise/settling/overshoot: `0.05` / `None` / `2.33`
- dominant_frequency_hz: `1.188` (power ratio `0.318`)
- labels: `integrator-like, oscillatory`

### `Output2`
- mean/std/ptp: `45.08` / `52.77` / `307.3`
- rise/settling/overshoot: `0.0` / `None` / `42.1`
- dominant_frequency_hz: `1.188` (power ratio `0.442`)
- labels: `integrator-like, oscillatory`

### `Output3`
- mean/std/ptp: `4.845` / `14.61` / `73.07`
- rise/settling/overshoot: `0.4` / `None` / `8.69`
- dominant_frequency_hz: `1.188` (power ratio `0.144`)
- labels: `integrator-like`

### `Output4`
- mean/std/ptp: `17.18` / `15.55` / `53.13`
- rise/settling/overshoot: `0.0` / `None` / `5.39`
- dominant_frequency_hz: `1.188` (power ratio `0.476`)
- labels: `integrator-like, oscillatory`

### `Output5`
- mean/std/ptp: `24.23` / `9.729` / `42.25`
- rise/settling/overshoot: `0.35000000000000003` / `None` / `2.01`
- dominant_frequency_hz: `1.188` (power ratio `0.411`)
- labels: `integrator-like, oscillatory`
