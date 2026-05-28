# FMU Semantic Report: `sb_arenstorf.fmu`

## Model Info
- modelName: `sb_arenstorf`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Activate`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `x_coor`, `y_coor`

## Probe Scenario
- start_time: `0.0`
- stop_time: `20.0`
- step_size: `1e-06`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `discrete-event-heavy, integrator-like, oscillatory`
- recommended_step_size_range: `6.4e-06 .. 2.56e-05`

## Variable Features (key)
### `x_coor`
- mean/std/ptp: `0.2696` / `0.4794` / `1.539`
- rise/settling/overshoot: `1.2823579999999999` / `None` / `0.0376`
- dominant_frequency_hz: `3906` (power ratio `0.95`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`

### `y_coor`
- mean/std/ptp: `0.2853` / `0.2342` / `0.6336`
- rise/settling/overshoot: `0.9119209999999998` / `None` / `0.0295`
- dominant_frequency_hz: `3906` (power ratio `0.95`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`
