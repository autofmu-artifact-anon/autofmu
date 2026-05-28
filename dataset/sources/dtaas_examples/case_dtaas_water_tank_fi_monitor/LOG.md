# case_dtaas_water_tank_fi_monitor

Original example: `digital_twins/water_tank_FI_monitor`
Title: Water Tank Fault Injection with Monitor

Generated FMUs:
- x4

Stages:
- stage1: asset_dtaas_water_tank_fi_monitor__x1, asset_dtaas_water_tank_fi_monitor__x2, asset_dtaas_water_tank_fi_monitor__x3, asset_dtaas_water_tank_fi_monitor__x4

Expected behavior: The injected controller fault drives the tank level beyond the monitor threshold and the generated monitor verdict transitions to violation for the bundled scenario.
