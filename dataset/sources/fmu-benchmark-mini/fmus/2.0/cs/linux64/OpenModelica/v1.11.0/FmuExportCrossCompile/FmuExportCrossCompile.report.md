# FMU Semantic Report: `FmuExportCrossCompile.fmu`

## Model Info
- modelName: `FmuExportCrossCompile`
- fmiVersion: `2.0`
- fmiTypes: `ModelExchange,CoSimulation`
- generationTool: `OpenModelica Compiler OMCompiler v1.12.0-dev.131+gc80769b`

## Selected Interface
- inputs: (none)
- outputs observed (2 from states): `der(h)`, `der(v)`

## Probe Scenario
- start_time: `0.0`
- stop_time: `0.45`
- step_size: `0.0022500000000000003`
- narrative: Generic excitation on representative inputs (step/ramp/sine).

## FMU Profile
- typical_dynamic_labels: `dead-zone, discrete-event-heavy, integrator-like, oscillatory`
- recommended_step_size_range: `0.01131 .. 0.04523`

## Variable Features (key)
### `der(h)`
- mean/std/ptp: `-2.207` / `1.281` / `4.415`
- rise/settling/overshoot: `0.32625000000000004` / `None` / `0.0525`
- dominant_frequency_hz: `2.211` (power ratio `0.95`)
- labels: `discrete-event-heavy, integrator-like, oscillatory`

### `der(v)`
- mean/std/ptp: `-9.81` / `1.776e-15` / `0`
- labels: `dead-zone`
