# FMU Semantic Report: `uart.fmu`

## Model Info
- modelName: `uart`
- fmiVersion: `2.0`
- fmiTypes: `CoSimulation`
- generationTool: `HIF2VP`

## Selected Interface
- inputs (3): `paddr`, `pwdata`, `presetn`
- outputs observed (5 from outputs): `prdata`, `stx`, `dtrn`, `rtsn`, `out1n`

## Probe Scenario
- start_time: `0.0`
- stop_time: `5.0`
- step_size: `0.025`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone, oscillatory, saturation`
- recommended_step_size_range: `0.1256 .. 0.5025`

## Variable Features (key)
### `prdata`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone, saturation`

### `stx`
- mean/std/ptp: `0.995` / `0.07036` / `1`
- rise/settling/overshoot: `0.0` / `0.025` / `0`
- dominant_frequency_hz: `0.199` (power ratio `1`)
- labels: `oscillatory`

### `dtrn`
- mean/std/ptp: `0.995` / `0.07036` / `1`
- rise/settling/overshoot: `0.0` / `0.025` / `0`
- dominant_frequency_hz: `0.199` (power ratio `1`)
- labels: `oscillatory`

### `rtsn`
- mean/std/ptp: `0.995` / `0.07036` / `1`
- rise/settling/overshoot: `0.0` / `0.025` / `0`
- dominant_frequency_hz: `0.199` (power ratio `1`)
- labels: `oscillatory`

### `out1n`
- mean/std/ptp: `0.995` / `0.07036` / `1`
- rise/settling/overshoot: `0.0` / `0.025` / `0`
- dominant_frequency_hz: `0.199` (power ratio `1`)
- labels: `oscillatory`
