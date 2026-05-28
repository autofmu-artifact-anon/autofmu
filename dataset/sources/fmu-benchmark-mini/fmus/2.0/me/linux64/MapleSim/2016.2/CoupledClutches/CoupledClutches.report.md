# FMU Semantic Report: `CoupledClutches.fmu`

## Model Info
- modelName: `CoupledClutches`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `MapleSim (1196527/1196706/1196706)`

## Selected Interface
- inputs (1): `inputs`
- outputs observed (4 from outputs): `outputs[1]`, `outputs[2]`, `outputs[3]`, `outputs[4]`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.0075`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.048 .. 0.192`

## Variable Features (key)
### `outputs[1]`
- mean/std/ptp: `4.604` / `2.325` / `7.738`
- rise/settling/overshoot: `0.7724999999999999` / `None` / `0.0414`
- dominant_frequency_hz: `0.5208` (power ratio `0.882`)
- labels: `oscillatory`

### `outputs[2]`
- mean/std/ptp: `2.67` / `0.7684` / `3.834`
- rise/settling/overshoot: `0.135` / `1.0575` / `0.749`
- dominant_frequency_hz: `0.5208` (power ratio `0.438`)
- labels: `oscillatory`

### `outputs[3]`
- mean/std/ptp: `1.595` / `1.084` / `2.601`
- rise/settling/overshoot: `0.3899999999999999` / `1.035` / `0.00961`
- dominant_frequency_hz: `0.5208` (power ratio `0.791`)
- labels: `oscillatory`

### `outputs[4]`
- mean/std/ptp: `1.435` / `1.125` / `2.601`
- rise/settling/overshoot: `0.41249999999999987` / `1.035` / `0.00961`
- dominant_frequency_hz: `0.5208` (power ratio `0.766`)
- labels: `oscillatory`
