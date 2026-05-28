from __future__ import annotations

import unittest

from pipeline.scenario_binding import (
    build_external_input_bindings,
    build_initial_condition_bindings,
    derive_execution_order,
)
from pipeline.stage1_decomposition.decomposer import _extract_operating_regime
from pipeline.types import FMU, OperatingRegime, PortMeta, TaskSet, TaskSignalSpec, VerificationTask


class ScenarioBindingTest(unittest.TestCase):
    def test_extract_operating_regime_separates_inputs_from_initial_conditions(self) -> None:
        regime = _extract_operating_regime(
            "Scenario time window 0s to 20s; inputs: disturbance_N_profile, theta_ref_rad, "
            "x_ref_m_profile; initial conditions: force_act_N, theta_rad, x_m. Acceptance criteria: max(abs(theta_rad)) <= 0.35."
        )
        self.assertIsNotNone(regime)
        assert regime is not None
        self.assertEqual(
            list(regime.inputs.keys()),
            ["disturbance_N_profile", "theta_ref_rad", "x_ref_m_profile"],
        )
        self.assertEqual(list(regime.initial_conditions.keys()), ["force_act_N", "theta_rad", "x_m"])

    def test_build_external_input_bindings_maps_profiles_to_driven_ports(self) -> None:
        selected_fmus = [
            FMU(
                uid="asset_controller",
                name="PendulumController",
                ports=[
                    PortMeta(name="x_ref_m", causality="input"),
                    PortMeta(name="theta_ref_rad", causality="input"),
                ],
                inputs=["x_ref_m", "theta_ref_rad"],
                outputs=["force_cmd_N"],
            ),
            FMU(
                uid="asset_plant",
                name="InvertedPendulumPlant",
                ports=[PortMeta(name="disturbance_N", causality="input")],
                inputs=["disturbance_N"],
                outputs=["x_m"],
            ),
        ]
        task_set = TaskSet(
            tasks=[
                VerificationTask(
                    task_id="controller_task",
                    objective="controller",
                    signal_specs=[
                        TaskSignalSpec(signal_name="x_ref_m", direction="in", role="driven", component_hint="controller"),
                        TaskSignalSpec(signal_name="theta_ref_rad", direction="in", role="driven", component_hint="controller"),
                    ],
                    operating_regime=OperatingRegime(inputs={"x_ref_m_profile": "provided", "theta_ref_rad": "provided"}),
                ),
                VerificationTask(
                    task_id="plant_task",
                    objective="plant",
                    signal_specs=[
                        TaskSignalSpec(signal_name="disturbance_N", direction="in", role="driven", component_hint="plant"),
                    ],
                    operating_regime=OperatingRegime(inputs={"disturbance_N_profile": "provided"}),
                ),
            ]
        )

        bindings, warnings = build_external_input_bindings(
            selected_fmus=selected_fmus,
            selected_task_set=task_set,
            scenario_inputs={
                "x_ref_m_profile": [{"t_s": 0, "value_m": 0.0}],
                "theta_ref_rad": 0.0,
                "disturbance_N_profile": [{"t_s": 0, "value_N": 0.0}],
            },
            verification_requirement_payload={},
        )
        bound_map = {item["name"]: item["targets"] for item in bindings}
        self.assertEqual(bound_map["x_ref_m"], ["asset_controller.x_ref_m"])
        self.assertEqual(bound_map["theta_ref_rad"], ["asset_controller.theta_ref_rad"])
        self.assertEqual(bound_map["disturbance_N"], ["asset_plant.disturbance_N"])
        self.assertEqual(warnings, [])

    def test_build_initial_condition_bindings_uses_qualified_aliases(self) -> None:
        selected_fmus = [
            FMU(
                uid="asset_controller",
                name="PendulumController",
                ports=[PortMeta(name="theta_rad", causality="input")],
                inputs=["theta_rad"],
            ),
            FMU(
                uid="asset_plant",
                name="InvertedPendulumPlant",
                ports=[PortMeta(name="theta_rad", causality="output")],
                outputs=["theta_rad"],
            ),
        ]
        task_set = TaskSet(tasks=[VerificationTask(task_id="plant_task", objective="plant")])
        bindings, warnings = build_initial_condition_bindings(
            selected_fmus=selected_fmus,
            selected_task_set=task_set,
            initial_conditions={"theta_rad": 0.12},
            verification_requirement_payload={
                "signal_aliases": {"theta_rad": ["theta_rad", "asset_plant.theta_rad"]},
            },
        )
        self.assertEqual(bindings, [{"name": "theta_rad", "targets": ["asset_plant.theta_rad"]}])
        self.assertEqual(warnings, [])

    def test_derive_execution_order_follows_task_order(self) -> None:
        selected_fmus = [
            FMU(uid="asset_plant", name="InvertedPendulumPlant"),
            FMU(uid="asset_controller", name="PendulumController"),
        ]
        task_set = TaskSet(
            tasks=[
                VerificationTask(task_id="controller_task", objective="controller", grounded_component_types=["PendulumController"]),
                VerificationTask(task_id="plant_task", objective="plant", grounded_component_types=["InvertedPendulumPlant"]),
            ]
        )
        self.assertEqual(
            derive_execution_order(selected_fmus=selected_fmus, selected_task_set=task_set),
            ["asset_controller", "asset_plant"],
        )


if __name__ == "__main__":
    unittest.main()
