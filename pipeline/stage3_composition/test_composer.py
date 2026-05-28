from __future__ import annotations

import unittest

from pipeline.stage3_composition.composer import compose
from pipeline.types import (
    FMU,
    FMUCapabilities,
    MatchingResult,
    MBSEContext,
    OrchestrationGraph,
    PortBinding,
    PortMeta,
    TaskSet,
    VerificationTask,
)


class ComposerScenarioWindowTest(unittest.TestCase):
    def test_compose_respects_declared_scenario_step_size_for_variable_step_fmus(self) -> None:
        fmu_a = FMU(
            uid="asset_a",
            name="A",
            ports=[PortMeta(name="x", causality="output")],
            outputs=["x"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 10.0}},
        )
        fmu_b = FMU(
            uid="asset_b",
            name="B",
            ports=[PortMeta(name="x", causality="input")],
            inputs=["x"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 10.0}},
        )
        matching = MatchingResult(
            task_set=TaskSet(tasks=[VerificationTask(task_id="task_0", objective="test")]),
            assignments=[],
            selected_fmus=[fmu_a, fmu_b],
            graph=OrchestrationGraph(nodes=[fmu_a.uid, fmu_b.uid], closure_ok=True),
            diagnostics={"status": "ok"},
        )

        result = compose(
            matching,
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            scenario_window={"step_size": 0.001},
        )

        self.assertEqual(result.simulation_config.step_size, 0.001)
        self.assertEqual(result.schedule["base_tick"], 0.001)
        self.assertEqual(result.schedule["fmu_steps"]["asset_a"], 0.001)
        self.assertEqual(result.schedule["fmu_steps"]["asset_b"], 0.001)
        self.assertTrue(
            any("scenario_step_size_refine=0.01->0.001" in item for item in result.schedule.get("warnings", []))
        )

    def test_compose_does_not_coarsen_schedule_from_declared_scenario_step_size(self) -> None:
        fmu_a = FMU(
            uid="asset_a",
            name="A",
            ports=[PortMeta(name="x", causality="output")],
            outputs=["x"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 1.0}},
        )
        fmu_b = FMU(
            uid="asset_b",
            name="B",
            ports=[PortMeta(name="x", causality="input")],
            inputs=["x"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 1.0}},
        )
        matching = MatchingResult(
            task_set=TaskSet(tasks=[VerificationTask(task_id="task_0", objective="test")]),
            assignments=[],
            selected_fmus=[fmu_a, fmu_b],
            graph=OrchestrationGraph(nodes=[fmu_a.uid, fmu_b.uid], closure_ok=True),
            diagnostics={"status": "ok"},
        )

        result = compose(
            matching,
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            scenario_window={"step_size": 0.5},
        )

        self.assertEqual(result.simulation_config.step_size, 0.01)
        self.assertEqual(result.schedule["base_tick"], 0.01)
        self.assertEqual(result.schedule["fmu_steps"]["asset_a"], 0.01)
        self.assertEqual(result.schedule["fmu_steps"]["asset_b"], 0.01)
        self.assertFalse(
            any("scenario_step_size_refine=" in item for item in result.schedule.get("warnings", []))
        )

    def test_compose_orders_loop_wrappers_by_derived_execution_order(self) -> None:
        controller = FMU(
            uid="asset_controller",
            name="PendulumController",
            ports=[
                PortMeta(name="force_cmd_N", causality="output"),
                PortMeta(name="theta_rad", causality="input"),
            ],
            inputs=["theta_rad"],
            outputs=["force_cmd_N"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 1.0}},
        )
        plant = FMU(
            uid="asset_plant",
            name="InvertedPendulumPlant",
            ports=[
                PortMeta(name="force_cmd_N", causality="input"),
                PortMeta(name="theta_rad", causality="output"),
            ],
            inputs=["force_cmd_N"],
            outputs=["theta_rad"],
            capabilities=FMUCapabilities(can_handle_variable_communication_step_size=True),
            meta={"default_experiment": {"stepSize": 0.01, "stopTime": 1.0}},
        )
        matching = MatchingResult(
            task_set=TaskSet(
                tasks=[
                    VerificationTask(
                        task_id="controller_task",
                        objective="controller",
                        grounded_component_types=["PendulumController"],
                    ),
                    VerificationTask(
                        task_id="plant_task",
                        objective="plant",
                        grounded_component_types=["InvertedPendulumPlant"],
                    ),
                ]
            ),
            assignments=[],
            selected_fmus=[plant, controller],
            graph=OrchestrationGraph(
                nodes=[plant.uid, controller.uid],
                bindings=[
                    PortBinding(
                        source_fmu=controller.uid,
                        source_signal="force_cmd_N",
                        target_fmu=plant.uid,
                        target_signal="force_cmd_N",
                        score=1.0,
                    ),
                    PortBinding(
                        source_fmu=plant.uid,
                        source_signal="theta_rad",
                        target_fmu=controller.uid,
                        target_signal="theta_rad",
                        score=1.0,
                    ),
                ],
                closure_ok=True,
            ),
            diagnostics={"status": "ok"},
        )

        result = compose(
            matching,
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        )

        self.assertEqual(len(result.schedule["loop_wrappers"]), 1)
        self.assertEqual(
            result.schedule["loop_wrappers"][0]["node_order"],
            ["asset_controller", "asset_plant"],
        )


if __name__ == "__main__":
    unittest.main()
