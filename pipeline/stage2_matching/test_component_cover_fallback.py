from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.stage2_matching.matcher import (
    _apply_mbse_component_cover_fallback,
    _resolve_fmu_signal_name,
    _selection_key,
    match,
)
from pipeline.types import (
    AcceptanceCriterion,
    FMU,
    MatchingResult,
    MBSEComponent,
    MBSEConnection,
    MBSEContext,
    MBSEPort,
    OperatingRegime,
    OrchestrationGraph,
    PortBinding,
    PortMeta,
    TaskAssignment,
    TaskSignalSpec,
    TaskSet,
    VerificationTask,
)


class ComponentCoverFallbackTest(unittest.TestCase):
    def _build_fixture(self):
        mbse_context = MBSEContext(
            package_name="pkg",
            system_name="BatteryThermalSystem",
            components=[
                MBSEComponent(
                    name="thermalController",
                    component_type="ThermalController",
                    ports=[
                        MBSEPort(component="thermalController", name="pump_cmd", direction="out"),
                        MBSEPort(component="thermalController", name="temp_cell_C", direction="in"),
                        MBSEPort(component="thermalController", name="temp_ref_C", direction="in"),
                    ],
                ),
                MBSEComponent(
                    name="coolantLoopPlant",
                    component_type="CoolantLoopPlant",
                    ports=[
                        MBSEPort(component="coolantLoopPlant", name="pump_cmd", direction="in"),
                        MBSEPort(component="coolantLoopPlant", name="coolant_temp_C", direction="out"),
                    ],
                ),
                MBSEComponent(
                    name="batteryPackPlant",
                    component_type="BatteryPackPlant",
                    ports=[
                        MBSEPort(component="batteryPackPlant", name="temp_cell_C", direction="out"),
                        MBSEPort(component="batteryPackPlant", name="i_load_A", direction="in"),
                    ],
                ),
            ],
            connections=[
                MBSEConnection(
                    source_component="thermalController",
                    source_signal="pump_cmd",
                    target_component="coolantLoopPlant",
                    target_signal="pump_cmd",
                ),
                MBSEConnection(
                    source_component="batteryPackPlant",
                    source_signal="temp_cell_C",
                    target_component="thermalController",
                    target_signal="temp_cell_C",
                ),
            ],
            metadata={"case_id": "case_manual_005", "source_type": "manual_multi_fmu_case"},
        )
        task_set = TaskSet(
            tasks=[
                VerificationTask(
                    task_id="task_monolithic",
                    objective="battery thermal management",
                    grounded_components=["thermalController", "coolantLoopPlant", "batteryPackPlant"],
                    grounded_component_types=["ThermalController", "CoolantLoopPlant", "BatteryPackPlant"],
                    required_signals=["pump_cmd", "temp_cell_C", "i_load_A", "coolant_temp_C"],
                    acceptance_criteria=[AcceptanceCriterion(metric="max(temp_cell_C)", operator="<=", value=45.0)],
                    signal_specs=[
                        TaskSignalSpec(
                            signal_name="pump_cmd",
                            direction="out",
                            component_hint="thermalController",
                            grounded_component_ref="thermalController",
                            grounded_port_ref="thermalController.io.pump_cmd",
                        ),
                        TaskSignalSpec(
                            signal_name="pump_cmd",
                            direction="in",
                            component_hint="coolantLoopPlant",
                            grounded_component_ref="coolantLoopPlant",
                            grounded_port_ref="coolantLoopPlant.io.pump_cmd",
                        ),
                        TaskSignalSpec(
                            signal_name="temp_cell_C",
                            direction="out",
                            component_hint="batteryPackPlant",
                            grounded_component_ref="batteryPackPlant",
                            grounded_port_ref="batteryPackPlant.io.temp_cell_C",
                        ),
                    ],
                    operating_regime=OperatingRegime(
                        start_time=0.0,
                        end_time=900.0,
                        inputs={"ambient_temp_C_profile": "provided"},
                        initial_conditions={"temp_cell_C": "provided"},
                    ),
                )
            ],
            task_set_id="taskset_0",
        )
        controller = FMU(
            uid="asset_case_case_manual_005__ThermalController",
            name="ThermalController",
            ports=[
                PortMeta(name="pump_cmd", causality="output"),
                PortMeta(name="temp_cell_C", causality="input"),
                PortMeta(name="temp_ref_C", causality="input"),
            ],
            outputs=["pump_cmd"],
            inputs=["temp_cell_C", "temp_ref_C"],
            meta={"source_type": "manual_case_fmu"},
        )
        coolant = FMU(
            uid="asset_case_case_manual_005__CoolantLoopPlant",
            name="CoolantLoopPlant",
            ports=[PortMeta(name="pump_cmd", causality="input"), PortMeta(name="coolant_temp_C", causality="output")],
            outputs=["coolant_temp_C"],
            inputs=["pump_cmd"],
            meta={"source_type": "manual_case_fmu"},
        )
        battery = FMU(
            uid="asset_case_case_manual_005__BatteryPackPlant",
            name="BatteryPackPlant",
            ports=[PortMeta(name="temp_cell_C", causality="output"), PortMeta(name="i_load_A", causality="input")],
            outputs=["temp_cell_C"],
            inputs=["i_load_A"],
            meta={"source_type": "manual_case_fmu"},
        )
        initial = MatchingResult(
            task_set=task_set,
            assignments=[
                TaskAssignment(
                    task_id="task_monolithic",
                    task_index=0,
                    fmu_uid=controller.uid,
                    score=1.0,
                    cost=0.1,
                    hard_ok=True,
                    semantic_cost=0.1,
                    hard_mask_value=0.0,
                    transport_mass=1.0,
                )
            ],
            selected_fmus=[controller],
            graph=OrchestrationGraph(nodes=[controller.uid], closure_ok=True),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=0.1,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=0.1,
            diagnostics={"status": "ok"},
        )
        return mbse_context, task_set, controller, coolant, battery, initial

    def test_component_cover_fallback_replaces_partial_monolithic_match(self) -> None:
        mbse_context, task_set, controller, coolant, battery, initial = self._build_fixture()

        fallback = _apply_mbse_component_cover_fallback(initial, mbse_context, [controller, coolant, battery])

        self.assertEqual(
            [fmu.uid for fmu in fallback.selected_fmus],
            [controller.uid, coolant.uid, battery.uid],
        )
        self.assertEqual(fallback.diagnostics["status"], "mbse_component_cover_fallback")
        self.assertEqual(len(fallback.graph.bindings), 2)
        self.assertTrue(all(task.operating_regime is not None for task in fallback.task_set.tasks))
        self.assertTrue(all(task.acceptance_criteria for task in fallback.task_set.tasks))
        controller_task = next(task for task in fallback.task_set.tasks if task.grounded_components == ["thermalController"])
        coolant_task = next(task for task in fallback.task_set.tasks if task.grounded_components == ["coolantLoopPlant"])
        battery_task = next(task for task in fallback.task_set.tasks if task.grounded_components == ["batteryPackPlant"])
        self.assertEqual(controller_task.operating_regime.end_time, 900.0)
        self.assertIn("pump_cmd", controller_task.required_signals)
        self.assertTrue(any(spec.grounded_component_ref == "thermalController" for spec in controller_task.signal_specs))
        self.assertTrue(any(spec.grounded_component_ref == "coolantLoopPlant" for spec in coolant_task.signal_specs))
        self.assertTrue(any(spec.grounded_component_ref == "batteryPackPlant" for spec in battery_task.signal_specs))

    def test_selection_key_prefers_full_component_cover_over_partial_single_fmu_match(self) -> None:
        mbse_context, _, controller, coolant, battery, initial = self._build_fixture()
        fallback = _apply_mbse_component_cover_fallback(initial, mbse_context, [controller, coolant, battery])
        self.assertLess(_selection_key(fallback, mbse_context), _selection_key(initial, mbse_context))

    def test_selection_key_prefers_richer_mbse_connection_coverage(self) -> None:
        mbse_context, task_set, controller, coolant, battery, _ = self._build_fixture()
        sparse = MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[controller, coolant, battery],
            graph=OrchestrationGraph(
                nodes=[controller.uid, coolant.uid, battery.uid],
                bindings=[
                    PortBinding(
                        source_fmu=controller.uid,
                        source_signal="pump_cmd",
                        target_fmu=coolant.uid,
                        target_signal="pump_cmd",
                        score=1.0,
                        chain_id="chain_0",
                        segment_id="seg_0",
                    )
                ],
                closure_ok=True,
            ),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=-1.0,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=-1.0,
            diagnostics={"status": "ok"},
        )
        dense = MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[controller, coolant, battery],
            graph=OrchestrationGraph(
                nodes=[controller.uid, coolant.uid, battery.uid],
                bindings=[
                    PortBinding(
                        source_fmu=controller.uid,
                        source_signal="pump_cmd",
                        target_fmu=coolant.uid,
                        target_signal="pump_cmd",
                        score=1.0,
                        chain_id="chain_0",
                        segment_id="seg_0",
                    ),
                    PortBinding(
                        source_fmu=battery.uid,
                        source_signal="temp_cell_C",
                        target_fmu=controller.uid,
                        target_signal="temp_cell_C",
                        score=1.0,
                        chain_id="chain_1",
                        segment_id="seg_1",
                    ),
                ],
                closure_ok=True,
            ),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=-1.0,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=-1.0,
            diagnostics={"status": "ok"},
        )
        self.assertLess(_selection_key(dense, mbse_context), _selection_key(sparse, mbse_context))

    def test_component_cover_fallback_replaces_low_alignment_component_even_when_component_count_is_full(self) -> None:
        mbse_context = MBSEContext(
            package_name="pkg",
            system_name="CartPoleEstimatorLoop",
            components=[
                MBSEComponent(
                    name="controller",
                    component_type="HybridController",
                    ports=[
                        MBSEPort(component="controller", name="x_m", direction="in"),
                        MBSEPort(component="controller", name="x_dot_mps", direction="in"),
                        MBSEPort(component="controller", name="theta_hat_rad", direction="in"),
                        MBSEPort(component="controller", name="theta_dot_hat_rps", direction="in"),
                        MBSEPort(component="controller", name="x_ref_m", direction="in"),
                        MBSEPort(component="controller", name="enable", direction="in"),
                        MBSEPort(component="controller", name="force_cmd_N", direction="out"),
                        MBSEPort(component="controller", name="mode", direction="out"),
                    ],
                ),
                MBSEComponent(
                    name="estimator",
                    component_type="AngleEstimator",
                    ports=[MBSEPort(component="estimator", name="theta_hat_rad", direction="out")],
                ),
                MBSEComponent(
                    name="plant",
                    component_type="CartPolePlant",
                    ports=[MBSEPort(component="plant", name="x_m", direction="out")],
                ),
            ],
            connections=[],
            metadata={"case_id": "case_manual_002", "source_type": "manual_case_fmu"},
        )
        task_set = TaskSet(
            tasks=[
                VerificationTask(
                    task_id="task_controller",
                    objective="controller-estimator-plant closed loop",
                    grounded_components=["controller", "estimator", "plant"],
                    grounded_component_types=["HybridController", "AngleEstimator", "CartPolePlant"],
                    required_signals=["x_m", "x_dot_mps", "theta_hat_rad", "theta_dot_hat_rps", "x_ref_m", "enable", "force_cmd_N", "mode"],
                    operating_regime=OperatingRegime(start_time=0.0, end_time=10.0),
                )
            ],
            task_set_id="taskset_0",
        )
        good_controller = FMU(
            uid="asset_case_case_manual_002__SwingUpBalanceController",
            name="SwingUpBalanceController",
            ports=[
                PortMeta(name="x_m", causality="input"),
                PortMeta(name="x_dot_mps", causality="input"),
                PortMeta(name="theta_hat_rad", causality="input"),
                PortMeta(name="theta_dot_hat_rps", causality="input"),
                PortMeta(name="x_ref_m", causality="input"),
                PortMeta(name="enable", causality="input"),
                PortMeta(name="force_cmd_N", causality="output"),
                PortMeta(name="mode", causality="output"),
            ],
            inputs=["x_m", "x_dot_mps", "theta_hat_rad", "theta_dot_hat_rps", "x_ref_m", "enable"],
            outputs=["force_cmd_N", "mode"],
            meta={"source_type": "manual_case_fmu"},
        )
        bad_controller = FMU(
            uid="asset_case_case_manual_003__PendulumController",
            name="PendulumController",
            ports=[
                PortMeta(name="x_m", causality="input"),
                PortMeta(name="x_dot_mps", causality="input"),
                PortMeta(name="x_ref_m", causality="input"),
                PortMeta(name="force_cmd_N", causality="output"),
            ],
            inputs=["x_m", "x_dot_mps", "x_ref_m"],
            outputs=["force_cmd_N"],
            meta={"source_type": "manual_case_fmu"},
        )
        estimator = FMU(
            uid="asset_case_case_manual_002__PoleAngleEstimator",
            name="PoleAngleEstimator",
            ports=[PortMeta(name="theta_hat_rad", causality="output")],
            outputs=["theta_hat_rad"],
            meta={"source_type": "manual_case_fmu"},
        )
        plant = FMU(
            uid="asset_case_case_manual_002__CartPolePlant",
            name="CartPolePlant",
            ports=[PortMeta(name="x_m", causality="output")],
            outputs=["x_m"],
            meta={"source_type": "manual_case_fmu"},
        )
        initial = MatchingResult(
            task_set=task_set,
            assignments=[
                TaskAssignment(
                    task_id="task_controller",
                    task_index=0,
                    fmu_uid=bad_controller.uid,
                    score=1.0,
                    cost=0.1,
                    hard_ok=True,
                    semantic_cost=0.1,
                    hard_mask_value=0.0,
                    transport_mass=1.0,
                )
            ],
            selected_fmus=[bad_controller, estimator, plant],
            graph=OrchestrationGraph(nodes=[bad_controller.uid, estimator.uid, plant.uid], closure_ok=True),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=0.1,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=0.1,
            diagnostics={"status": "ok"},
        )

        fallback = _apply_mbse_component_cover_fallback(
            initial,
            mbse_context,
            [good_controller, bad_controller, estimator, plant],
        )

        self.assertEqual(
            [fmu.uid for fmu in fallback.selected_fmus],
            [good_controller.uid, estimator.uid, plant.uid],
        )
        self.assertEqual(fallback.diagnostics["status"], "mbse_component_cover_fallback")
        self.assertGreater(
            fallback.diagnostics["fallback_component_alignment"],
            fallback.diagnostics["selected_component_alignment"],
        )

    def test_resolve_fmu_signal_name_handles_common_renamed_ports(self) -> None:
        fmu = FMU(
            uid="asset_case_case_manual_001__CoolingLoop",
            name="CoolingLoop",
            ports=[
                PortMeta(name="pump_cmd", causality="input"),
                PortMeta(name="fan_cmd", causality="input"),
                PortMeta(name="T_batt_surface_C", causality="input"),
                PortMeta(name="heat_load_W", causality="input"),
                PortMeta(name="coolant_in_temp_C", causality="output"),
            ],
            inputs=["pump_cmd", "fan_cmd", "T_batt_surface_C", "heat_load_W"],
            outputs=["coolant_in_temp_C"],
            meta={"source_type": "manual_case_fmu"},
        )
        self.assertEqual(_resolve_fmu_signal_name(fmu, "pumpCommand"), "pump_cmd")
        self.assertEqual(_resolve_fmu_signal_name(fmu, "fanCommand"), "fan_cmd")
        self.assertEqual(_resolve_fmu_signal_name(fmu, "batterySurfaceTemperature_C"), "T_batt_surface_C")
        self.assertEqual(_resolve_fmu_signal_name(fmu, "heatLoad_W"), "heat_load_W")
        self.assertEqual(_resolve_fmu_signal_name(fmu, "coolantInletTemperature_C"), "coolant_in_temp_C")

    def test_component_cover_fallback_drops_empty_operating_regime(self) -> None:
        mbse_context = MBSEContext(
            package_name="pkg",
            system_name="ThreeTank",
            components=[
                MBSEComponent(
                    name="tank1",
                    component_type="tank",
                    ports=[MBSEPort(component="tank1", name="outPort", direction="out")],
                ),
                MBSEComponent(
                    name="tank2",
                    component_type="tank",
                    ports=[MBSEPort(component="tank2", name="inPort", direction="in")],
                ),
            ],
            connections=[
                MBSEConnection(source_component="tank1", source_signal="outPort", target_component="tank2", target_signal="inPort")
            ],
            metadata={"case_id": "case_dtaas_three_tank", "source_type": "dtaas_example_fmu"},
        )
        task_set = TaskSet(
            tasks=[
                VerificationTask(
                    task_id="task_tank",
                    objective="three tank cascade",
                    grounded_components=["tank1", "tank2"],
                    grounded_component_types=["tank", "tank"],
                    required_signals=["outPort", "inPort"],
                    operating_regime=OperatingRegime(start_time=0.0, end_time=10.0),
                )
            ],
            task_set_id="taskset_0",
        )
        tank1 = FMU(
            uid="asset_dtaas_three_tank__tank1",
            name="tank1",
            ports=[PortMeta(name="outPort", causality="output")],
            outputs=["outPort"],
            meta={"source_type": "dtaas_example_fmu"},
        )
        tank2 = FMU(
            uid="asset_dtaas_three_tank__tank2",
            name="tank2",
            ports=[PortMeta(name="inPort", causality="input")],
            inputs=["inPort"],
            meta={"source_type": "dtaas_example_fmu"},
        )
        initial = MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[],
            graph=OrchestrationGraph(nodes=[], closure_ok=False),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=1.0,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=1.0,
            diagnostics={"status": "failed"},
        )

        fallback = _apply_mbse_component_cover_fallback(initial, mbse_context, [tank1, tank2])

        self.assertTrue(all(task.operating_regime is None for task in fallback.task_set.tasks))

    def test_match_can_disable_component_cover_fallback(self) -> None:
        mbse_context, task_set, controller, coolant, battery, initial = self._build_fixture()

        with patch("pipeline.stage2_matching.matcher._run_taskset_transport", return_value=initial):
            result = match(
                [task_set],
                mbse_context=mbse_context,
                fmu_library=[controller, coolant, battery],
                enable_mbse_component_cover_fallback=False,
            )

        self.assertEqual([fmu.uid for fmu in result.selected_fmus], [controller.uid])
        self.assertEqual(result.diagnostics["status"], "ok")
        self.assertNotEqual(result.task_set.generation_source, "stage2_fallback")

    def test_match_can_disable_benchmark_single_fmu_fallback(self) -> None:
        mbse_context = MBSEContext(
            package_name="pkg",
            system_name="BenchmarkSystem",
            metadata={"case_id": "case_bench_fmu-009999", "source_type": "benchmark_single_fmu_case"},
        )
        task_set = TaskSet(
            tasks=[VerificationTask(task_id="task_bench", objective="benchmark single-fmu task")],
            task_set_id="taskset_0",
        )
        benchmark_fmu = FMU(
            uid="asset_bench_fmu-009999",
            name="BenchmarkPlant",
            ports=[PortMeta(name="y", causality="output")],
            outputs=["y"],
            meta={"source_type": "benchmark_single_fmu"},
        )
        initial = MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[],
            graph=OrchestrationGraph(nodes=[], closure_ok=False),
            discrepancy_set=[],
            revision_trace=[],
            final_cost=1.0,
            transport_plans=[],
            mask_history=[],
            taskset_results=[],
            selected_task_set_cost=1.0,
            diagnostics={"status": "failed"},
        )

        with patch("pipeline.stage2_matching.matcher._run_taskset_transport", return_value=initial):
            result = match(
                [task_set],
                mbse_context=mbse_context,
                fmu_library=[benchmark_fmu],
                enable_benchmark_single_fmu_fallback=False,
            )

        self.assertEqual(result.selected_fmus, [])
        self.assertEqual(result.diagnostics["status"], "failed")


if __name__ == "__main__":
    unittest.main()
