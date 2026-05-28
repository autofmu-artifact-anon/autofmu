# case_dtaas_three_tank

Original example: `digital_twins/three-tank`
Title: Three-Tank System Digital Twin

Generated FMUs:
- none

Stages:
- stage1: asset_dtaas_three_tank__tank1, asset_dtaas_three_tank__tank2, asset_dtaas_three_tank__tank3

Expected behavior: The three tank instances propagate flow from tank1 to tank3 while logging level, in/out flow, leak, and derivative signals over the configured time window.
