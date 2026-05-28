# case_ship_propulsion

Ship Propulsion System Verification

## Requirement Decomposition

- Verification requirement: re-convergence and safety for 8 signals over 300 s, 5 phases
- Decomposer sampled 5 candidate task sets; conformal thresholding (q=0.68, n=30) retained 3
- Retained scores: 0.71, 0.78, 0.86; filtered scores: 0.45, 0.58
- Selected task set (score 0.86) with 8 sub-tasks:
  K_T recovery, RPM tracking, Thrust equilibrium, Cavitation safety,
  Resistance envelope, Shaft stress limit, Thermal safety, Fuel efficiency

## FMU Matching

- Candidate library: 18 FMUs
- Iteration 1: shaft_dynamics_v2 assigned to shaft line role -> failed (shaft_RPM is input) -> mask updated
- Iteration 2: engine_model_legacy assigned to engine role -> failed (missing engine_state_vector) -> mask updated
- Iteration 3: all 10 correct FMUs assigned, topological verification passed
- 8 candidates rejected (2 by mask, 6 by hard constraint)

## Selected FMUs

controller, ce_wrapper, engine_model, gearbox, shaft_line_model,
propeller_design, fuel_consumption_model, hull_load_estimator,
cavitation_proxy, exhaust_thermal_monitor

## Graph Topology

- 10 FMU nodes, 2 environment nodes, 2 wrapper nodes, 22 directed edges
- SCC1: controller + ce_wrapper + engine_model (K_T/RPM feedback)
- SCC2: gearbox + shaft_line_model + propeller_design (shaft_RPM/resistance_torque feedback)

## Wrappers

1. CE Wrapper: [0,1] -> RPM [40,120] linear mapping
2. Projection: 4-component engine_state_vector -> 2 components (engine_power, engine_RPM)
3. Unit: fuel_flow_rate kg/h -> g/s (factor 1000/3600)

## Schedule

- 6 distinct step sizes: 0.005, 0.05, 0.1, 0.5, 1.0, 2.0 s
- Base tick: 0.005 s -> 60,000 ticks for 300 s
- Cross-rate interpolation: zero-order hold

## Convergence

- SCC1: 600 communication points, mean 2.8 iters, max 4
- SCC2: 6,000 communication points, mean 3.1 (Phases 2,4), 5.6 (Phase 3), max 12 at t=118 s

## Acceptance

All 14 criteria pass. Closest margins: cavitation (0.12 vs 0.1), shaft stress (0.82 vs 0.85).
