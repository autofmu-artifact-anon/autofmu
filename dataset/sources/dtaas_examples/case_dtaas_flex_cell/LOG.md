# case_dtaas_flex_cell

Original example: `digital_twins/flex-cell`
Title: Flex Cell Digital Twin with Two Industrial Robots

Generated FMUs:
- rabbitmq

Stages:
- stage1: asset_dtaas_flex_cell__rabbitmq, asset_dtaas_flex_cell__kuka, asset_dtaas_flex_cell__ur5e

Expected behavior: The RabbitMQ FMU injects target Cartesian positions and motion durations for both robot FMUs, and the logged robot states track those commands over fixed-step co-simulation.
