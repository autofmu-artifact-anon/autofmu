# FMU Semantic Report: `FMICrossCheck.CoupledClutches.fmu`

## Model Info
- modelName: `FMICrossCheck.CoupledClutches`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange`
- generationTool: `Wolfram SystemModeler 5.0.0.10`

## Selected Interface
- inputs (1): `f_normalized`
- outputs observed (4 from outputs): `J1_w`, `J2_w`, `J3_w`, `J4_w`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.5`
- step_size: `0.001`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `0.0064 .. 0.0256`

## Variable Features (key)
### `J1_w`
- mean/std/ptp: `4.783` / `2.423` / `7.741`
- rise/settling/overshoot: `0.667` / `None` / `0.0377`
- dominant_frequency_hz: `3.906` (power ratio `0.836`)
- labels: `oscillatory`

### `J2_w`
- mean/std/ptp: `2.623` / `0.7915` / `3.834`
- rise/settling/overshoot: `0.149` / `1.0489999999999997` / `0.696`
- dominant_frequency_hz: `3.906` (power ratio `0.924`)
- labels: `oscillatory`

### `J3_w`
- mean/std/ptp: `1.534` / `1.104` / `2.599`
- rise/settling/overshoot: `0.38800000000000007` / `1.0309999999999997` / `0.00957`
- dominant_frequency_hz: `3.906` (power ratio `0.936`)
- labels: `oscillatory`

### `J4_w`
- mean/std/ptp: `1.379` / `1.127` / `2.599`
- rise/settling/overshoot: `0.41200000000000003` / `1.0309999999999997` / `0.00957`
- dominant_frequency_hz: `3.906` (power ratio `0.937`)
- labels: `oscillatory`
