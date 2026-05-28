# FMU Semantic Report: `WaterTank.Control.fmu`

## Model Info
- modelName: `WaterTank.Control`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`
- generationTool: `OpenModelica Compiler OMCompiler v1.12.0-dev.131+gc80769b`

## Selected Interface
- inputs (1): `level`
- outputs observed (1 from outputs): `valve`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.0`
- step_size: `0.005`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone`
- recommended_step_size_range: `0.0025 .. 0.01`

## Variable Features (key)
### `valve`
- mean/std/ptp: `0` / `0` / `0`
- labels: `dead-zone`
