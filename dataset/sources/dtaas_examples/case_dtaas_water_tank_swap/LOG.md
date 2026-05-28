# case_dtaas_water_tank_swap

Original example: `digital_twins/water_tank_swap`
Title: Water Tank Model Swap

Generated FMUs:
- none

Stages:
- stage1: asset_dtaas_water_tank_swap__x1, asset_dtaas_water_tank_swap__x2
- stage2: asset_dtaas_water_tank_swap__x1, asset_dtaas_water_tank_swap__x2, asset_dtaas_water_tank_swap__x3, asset_dtaas_water_tank_swap__x4

Expected behavior: Stage 1 executes the nominal water-tank co-simulation with injected faults, and stage 2 introduces leak detection plus runtime swap to the leak controller when the swap condition is satisfied.
