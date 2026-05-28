# FMU Semantic Report: `RoomHeating_OM.RH.fmu`

## Model Info
- modelName: `RoomHeating_OM.RH`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`
- generationTool: `OpenModelica Compiler OMCompiler v1.12.0-dev.131+gc80769b`

## Selected Interface
- inputs (3): `OAT`, `fanspeed`, `valveopen`
- outputs observed (1 from outputs): `RAT`

## Probe Scenario
- start_time: `0.0`
- stop_time: `1.0`
- step_size: `0.005`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `integrator-like, oscillatory`
- recommended_step_size_range: `0.02513 .. 0.1005`

## Variable Features (key)
### `RAT`
- mean/std/ptp: `16` / `0.001554` / `0.00465`
- rise/settling/overshoot: `0.52` / `None` / `0.0728`
- dominant_frequency_hz: `0.995` (power ratio `0.861`)
- labels: `integrator-like, oscillatory`
