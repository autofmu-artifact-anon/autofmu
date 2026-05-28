# FMU Semantic Report: `TorsionBar.fmu`

## Model Info
- modelName: `TorsionBar`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `20-sim`

## Selected Interface
- inputs: (none)
- outputs observed (2 from outputs): `LoadDiskRev`, `MotorDiskRev`

## Probe Scenario
- start_time: `0.0`
- stop_time: `12.5663706143592`
- step_size: `1e-05`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `oscillatory`
- recommended_step_size_range: `6.4e-05 .. 0.000256`

## Variable Features (key)
### `LoadDiskRev`
- mean/std/ptp: `0.6542` / `0.4876` / `1.398`
- rise/settling/overshoot: `0.06577` / `12.522720000000001` / `0.563`
- dominant_frequency_hz: `390.6` (power ratio `0.95`)
- labels: `oscillatory`

### `MotorDiskRev`
- mean/std/ptp: `2.453` / `1.8` / `4.787`
- rise/settling/overshoot: `0.08114000000000005` / `11.073590000000001` / `0.37`
- dominant_frequency_hz: `390.6` (power ratio `0.95`)
- labels: `oscillatory`
