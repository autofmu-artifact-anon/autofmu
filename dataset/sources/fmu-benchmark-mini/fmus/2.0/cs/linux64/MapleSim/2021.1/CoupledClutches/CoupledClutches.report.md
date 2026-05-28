# FMU Semantic Report: `CoupledClutches.fmu`

## Model Info
- modelName: `CoupledClutches`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `MapleSim (1543232/1543232)`

## Selected Interface
- inputs (1): `inputs`
- outputs observed (4 from outputs): `outputs[1]`, `outputs[2]`, `outputs[3]`, `outputs[4]`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `outputs[1]`
- mean/std/ptp: `4.827` / `2.438` / `7.749`
- rise/settling/overshoot: `0.668` / `None` / `0.0376`
- dominant_frequency_hz: `3.906` (power ratio `0.825`)
- labels: `integrator-like, oscillatory`

### `outputs[2]`
- mean/std/ptp: `2.62` / `0.8016` / `3.844`
- rise/settling/overshoot: `0.15` / `1.049` / `0.695`
- dominant_frequency_hz: `3.906` (power ratio `0.919`)
- labels: `oscillatory`

### `outputs[3]`
- mean/std/ptp: `1.513` / `1.107` / `2.603`
- rise/settling/overshoot: `0.38900000000000007` / `1.032` / `0.00948`
- dominant_frequency_hz: `3.906` (power ratio `0.92`)
- labels: `oscillatory`

### `outputs[4]`
- mean/std/ptp: `1.357` / `1.127` / `2.606`
- rise/settling/overshoot: `0.41300000000000003` / `1.032` / `0.00947`
- dominant_frequency_hz: `3.906` (power ratio `0.922`)
- labels: `oscillatory`
