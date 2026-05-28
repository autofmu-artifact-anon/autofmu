# FMU Semantic Report: `WaterTank.TestSingleWaterTank.fmu`

## Model Info
- modelName: `WaterTank.TestSingleWaterTank`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`
- generationTool: `OpenModelica Compiler OMCompiler v1.12.0-dev.131+gc80769b`

## Selected Interface
- inputs: (none)
- outputs observed (2 from states): `der(tank.valve_outflow_int)`, `der(tank.volume)`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.0`
- step_size: `0.005`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone`
- recommended_step_size_range: `0.0025 .. 0.01`

## Variable Features (key)
### `der(tank.valve_outflow_int)`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`

### `der(tank.volume)`
- mean/std/ptp: `1` / `0` / `0`
- labels: `dead-zone`
