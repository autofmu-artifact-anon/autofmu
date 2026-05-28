# FMU Semantic Report: `sb_arenstorf.fmu`

## Model Info
- modelName: `sb_arenstorf`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `x_coor`, `y_coor`

## Probe Scenario
- start_time: `0.0`
- stop_time: `20.0`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `x_coor`
- mean/std/ptp: `-0.3209` / `0.5506` / `2.239`
- rise/settling/overshoot: `0.478` / `None` / `1.33`
- dominant_frequency_hz: `3.906` (power ratio `0.947`)
- labels: `integrator-like, oscillatory`

### `y_coor`
- mean/std/ptp: `0.06563` / `0.6476` / `2.284`
- rise/settling/overshoot: `0.96` / `None` / `1.56`
- dominant_frequency_hz: `3.906` (power ratio `0.948`)
- labels: `integrator-like, oscillatory`
