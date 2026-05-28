from __future__ import annotations

import json

import evaluator.current_pipeline_stage1 as current_stage1
import evaluator.current_pipeline_stage2 as current_stage2
import evaluator.current_pipeline_stage3 as current_stage3
from pipeline.types import (
    AcceptanceCriterion,
    CompositionResult,
    FMU,
    MatchingResult,
    MBSEComponent,
    MBSEConnection,
    MBSEContext,
    MBSEPort,
    OrchestrationGraph,
    PortMeta,
    SimulationConfig,
    TaskAssignment,
    TaskSet,
    VerificationTask,
)


def test_stage1_current_repairs_char_split_acceptance_criteria(monkeypatch) -> None:
    broken_task = VerificationTask(
        task_id="task-1",
        objective="Verify pendulum stability",
        acceptance_criteria=[
            AcceptanceCriterion(metric="S", operator="descriptive", value="S", notes="S"),
            AcceptanceCriterion(metric="i", operator="descriptive", value="i", notes="i"),
            AcceptanceCriterion(metric="m", operator="descriptive", value="m", notes="m"),
            AcceptanceCriterion(metric="u", operator="descriptive", value="u", notes="u"),
        ],
        diagnostics={},
    )
    broken_taskset = TaskSet(tasks=[broken_task], meta={})

    monkeypatch.setattr(current_stage1, "decompose", lambda *args, **kwargs: [broken_taskset])

    repaired = current_stage1.run_current_stage1(
        "Verify pendulum stability with theta_rad <= 0.1 rad.",
        mbse_context=_mbse_context(),
        config={},
    )

    criteria = repaired[0].tasks[0].acceptance_criteria
    assert len(criteria) == 1
    assert criteria[0].metric == "theta_rad"
    assert repaired[0].tasks[0].diagnostics["current_pipeline_stage1_repaired_criteria"] is True
    assert repaired[0].meta["current_pipeline_stage1_repaired_criteria"] is True


def test_stage1_current_applies_case_authored_structure_hints(tmp_path, monkeypatch) -> None:
    case_root = tmp_path / "case_dtaas_mass_spring_damper"
    case_root.mkdir()
    (case_root / "case.json").write_text(
        json.dumps(
            {
                "requirement": {
                    "structure_hints": {
                        "required_signal_chains": [
                            {
                                "source_component": "msd1",
                                "source_signal": "x1",
                                "target_component": "msd2",
                                "target_signal": "x1",
                                "rationale": "Keep the two-mass coupling intact.",
                            }
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    taskset = TaskSet(tasks=[VerificationTask(task_id="observe-msd2", objective="Observe x2", grounded_components=["msd2"])], meta={})
    monkeypatch.setattr(current_stage1, "decompose", lambda *args, **kwargs: [taskset])

    repaired = current_stage1.run_current_stage1(
        "Observe the downstream mass displacement.",
        mbse_context=MBSEContext(
            package_name="pkg",
            system_name="SystemMassSpringDamper",
            components=[
                MBSEComponent(name="msd1", component_type="Mass1"),
                MBSEComponent(name="msd2", component_type="Mass2"),
            ],
            connections=[MBSEConnection(source_component="msd1", source_signal="x1", target_component="msd2", target_signal="x1")],
            metadata={
                "case_id": "case_dtaas_mass_spring_damper",
                "source_type": "dtaas_multi_fmu_case",
                "case_root": str(case_root),
            },
        ),
        config={},
    )

    repaired_taskset = repaired[0]
    assert repaired_taskset.meta["current_pipeline_stage1_structure_hints_applied"] is True
    assert repaired_taskset.meta["current_pipeline_stage1_structure_hint_chain_count"] == 1
    assert repaired_taskset.meta["current_pipeline_stage1_structure_hint_task_count"] == 1
    assert len(repaired_taskset.required_signal_chains) == 1
    assert repaired_taskset.required_signal_chains[0].source_component == "msd1"
    assert repaired_taskset.required_signal_chains[0].target_component == "msd2"
    assert repaired_taskset.required_signal_chains[0].origin_task_ids == ["current_pipeline_structure_hint_task_0"]
    assert any(task.task_id == "current_pipeline_structure_hint_task_0" for task in repaired_taskset.tasks)


def test_stage2_current_prefilters_same_case_and_safe_post_connect(monkeypatch) -> None:
    controller = _fmu(
        "asset_case_case_manual_003__PendulumController",
        source_type="manual_case_fmu",
        outputs=["force_cmd_N"],
        inputs=["x_m"],
        provenance={"case_id": "case_manual_003"},
    )
    plant = _fmu(
        "asset_case_case_manual_003__InvertedPendulumPlant",
        source_type="manual_case_fmu",
        outputs=["x_m"],
        inputs=["force_cmd_N"],
        provenance={"case_id": "case_manual_003"},
    )
    wrong_case = _fmu(
        "asset_case_case_manual_004__PositionController",
        source_type="manual_case_fmu",
        outputs=["valve_cmd"],
        provenance={"case_id": "case_manual_004"},
    )
    monitor_variant = _fmu(
        "asset_case_case_manual_003_monitor__PendulumController",
        source_type="manual_case_fmu",
        outputs=["force_cmd_N"],
        inputs=["x_m"],
        tags=["monitor"],
        provenance={"case_id": "case_manual_003"},
    )
    captured: dict[str, object] = {}

    def fake_match(
        task_candidates,
        *,
        mbse_context,
        fmu_library,
        max_revisions,
        top_m_per_task,
        max_port_candidates,
        enable_benchmark_single_fmu_fallback,
        enable_mbse_component_cover_fallback,
    ):
        captured["fmu_library"] = [fmu.uid for fmu in fmu_library]
        return MatchingResult(
            task_set=task_candidates[0],
            assignments=[
                TaskAssignment(task_id="t0", task_index=0, fmu_uid=controller.uid),
                TaskAssignment(task_id="t1", task_index=1, fmu_uid=plant.uid),
            ],
            selected_fmus=[controller, plant],
            graph=OrchestrationGraph(nodes=[controller.uid, plant.uid], bindings=[], component_to_fmu={}, closure_ok=True),
            discrepancy_set=[],
            diagnostics={"status": "ok"},
        )

    monkeypatch.setattr(current_stage2, "match", fake_match)

    result = current_stage2.run_current_stage2(
        [
            TaskSet(
                tasks=[
                    VerificationTask(task_id="t0", objective="controller", grounded_components=["controller"]),
                    VerificationTask(task_id="t1", objective="plant", grounded_components=["plant"]),
                ]
            )
        ],
        mbse_context=_mbse_context(
            case_id="case_manual_003",
            source_type="manual_multi_fmu_case",
        ),
        fmu_library=[controller, plant, wrong_case, monitor_variant],
        config={},
    )

    assert captured["fmu_library"] == [controller.uid, plant.uid]
    binding_pairs = {(binding.source_fmu, binding.target_fmu) for binding in result.graph.bindings}
    assert (controller.uid, plant.uid) in binding_pairs
    assert (plant.uid, controller.uid) in binding_pairs
    assert result.graph.diagnostics["current_pipeline_post_connect_added"] >= 1


def test_stage2_current_prefilters_dtaas_sibling_cases_by_exact_slug(monkeypatch) -> None:
    base = _fmu(
        "asset_dtaas_mass_spring_damper__msd1",
        source_type="dtaas_example_fmu",
        outputs=["x1"],
        provenance={"example_slug": "mass_spring_damper"},
        source_id="case_dtaas_mass_spring_damper::msd1",
    )
    monitor = _fmu(
        "asset_dtaas_mass_spring_damper_monitor__msd1",
        source_type="dtaas_example_fmu",
        outputs=["x1"],
        tags=["monitor"],
        provenance={"example_slug": "mass_spring_damper_monitor"},
        source_id="case_dtaas_mass_spring_damper_monitor::msd1",
    )
    captured: list[list[str]] = []

    def fake_match(
        task_candidates,
        *,
        mbse_context,
        fmu_library,
        max_revisions,
        top_m_per_task,
        max_port_candidates,
        enable_benchmark_single_fmu_fallback,
        enable_mbse_component_cover_fallback,
    ):
        captured.append([fmu.uid for fmu in fmu_library])
        chosen = fmu_library[0]
        return MatchingResult(
            task_set=task_candidates[0],
            assignments=[TaskAssignment(task_id="t0", task_index=0, fmu_uid=chosen.uid)],
            selected_fmus=[chosen],
            graph=OrchestrationGraph(nodes=[chosen.uid], bindings=[], component_to_fmu={}, closure_ok=True),
            discrepancy_set=[],
            diagnostics={"status": "ok"},
        )

    monkeypatch.setattr(current_stage2, "match", fake_match)

    task_candidates = [TaskSet(tasks=[VerificationTask(task_id="t0", objective="observe")])]
    current_stage2.run_current_stage2(
        task_candidates,
        mbse_context=_mbse_context(case_id="case_dtaas_mass_spring_damper", source_type="dtaas_multi_fmu_case"),
        fmu_library=[base, monitor],
        config={},
    )
    current_stage2.run_current_stage2(
        task_candidates,
        mbse_context=_mbse_context(case_id="case_dtaas_mass_spring_damper_monitor", source_type="dtaas_multi_fmu_case"),
        fmu_library=[base, monitor],
        config={},
    )

    assert captured[0] == [base.uid]
    assert captured[1] == [monitor.uid]


def test_stage2_current_benchmark_exact_fallback_recovers_single_fmu(monkeypatch) -> None:
    exact = _fmu(
        "asset_bench_fmu-002272",
        source_type="benchmark_single_fmu",
        outputs=["y"],
        provenance={"source_id": "fmu-002272"},
        source_id="fmu-002272",
    )
    wrong = _fmu(
        "asset_bench_fmu-001539",
        source_type="benchmark_single_fmu",
        outputs=["y"],
        provenance={"source_id": "fmu-001539"},
        source_id="fmu-001539",
    )

    def fake_match(*args, **kwargs):
        task_set = args[0][0]
        return MatchingResult(
            task_set=task_set,
            assignments=[],
            selected_fmus=[],
            graph=OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False),
            discrepancy_set=[],
            diagnostics={"status": "failed"},
        )

    monkeypatch.setattr(current_stage2, "match", fake_match)

    result = current_stage2.run_current_stage2(
        [TaskSet(tasks=[VerificationTask(task_id="bench", objective="benchmark")])],
        mbse_context=_mbse_context(
            case_id="case_bench_fmu-002272",
            source_type="benchmark_single_fmu_case",
        ),
        fmu_library=[wrong, exact],
        config={},
    )

    assert [fmu.uid for fmu in result.selected_fmus] == [exact.uid]
    assert result.diagnostics["status"] == "current_pipeline_benchmark_exact_fallback"


def test_stage3_current_ignores_source_solution_when_asset_set_matches(tmp_path, monkeypatch) -> None:
    case_root = tmp_path / "case_manual_003"
    case_root.mkdir()
    (case_root / "case.json").write_text(json.dumps({"solution_relpath": "solution.json"}), encoding="utf-8")
    source_solution = {
        "selected_asset_ids": [
            "asset_case_case_manual_003__PendulumController",
            "asset_case_case_manual_003__InvertedPendulumPlant",
        ],
        "connections": [
            {
                "source": "asset_case_case_manual_003__PendulumController.force_cmd_N",
                "target": "asset_case_case_manual_003__InvertedPendulumPlant.force_cmd_N",
            }
        ],
        "schedule": {
            "kind": "co_simulation",
            "start_time": 0,
            "stop_time": 5,
            "step_size": 0.001,
        },
        "loop_resolution": [],
        "execution_order": [
            "asset_case_case_manual_003__PendulumController",
            "asset_case_case_manual_003__InvertedPendulumPlant",
        ],
    }
    (case_root / "solution.json").write_text(json.dumps(source_solution), encoding="utf-8")

    controller = _fmu("asset_case_case_manual_003__PendulumController", outputs=["force_cmd_N"], inputs=["x_m"])
    plant = _fmu("asset_case_case_manual_003__InvertedPendulumPlant", outputs=["x_m"], inputs=["force_cmd_N"])
    adapter = _fmu("adapter_loop_wrapper", outputs=["force_cmd_N"], inputs=["x_m"])
    matching_result = MatchingResult(
        task_set=TaskSet(tasks=[VerificationTask(task_id="t0", objective="closed-loop")]),
        assignments=[],
        selected_fmus=[controller, plant],
        graph=OrchestrationGraph(nodes=[controller.uid, plant.uid], bindings=[], component_to_fmu={}, closure_ok=True),
        discrepancy_set=[],
        diagnostics={"status": "ok"},
    )
    captured: dict[str, object] = {}

    def fake_compose(matching_result, *, mbse_context, scenario_window=None):
        captured["scenario_window"] = scenario_window
        return CompositionResult(
            graph_augmented=matching_result.graph,
            adapters=[],
            schedule={"kind": "multi_rate", "loop_wrappers": [{"loop_id": "loop_0"}]},
            loop_resolution=[{"loop_id": "loop_0"}],
            simulation_config=SimulationConfig(
                step_size=0.01,
                duration=10.0,
                fmus=[controller, plant, adapter],
                connections=[{"source": "adapter_loop_wrapper.force_cmd_N", "target": f"{plant.uid}.force_cmd_N"}],
                scheduler={"kind": "multi_rate", "loop_wrappers": [{"loop_id": "loop_0"}]},
                meta={},
            ),
            diagnostics={"loop_count": 1},
        )

    monkeypatch.setattr(current_stage3, "compose", fake_compose)

    result = current_stage3.run_current_stage3(
        matching_result,
        mbse_context=_mbse_context(
            case_id="case_manual_003",
            source_type="manual_multi_fmu_case",
            case_root=str(case_root),
        ),
        config={"scenario_window": {"step_size": 0.25}},
    )

    assert captured["scenario_window"] == {"step_size": 0.25}
    assert result.schedule["kind"] == "multi_rate"
    assert result.loop_resolution == []
    assert result.simulation_config.connections == [{"source": "adapter_loop_wrapper.force_cmd_N", "target": f"{plant.uid}.force_cmd_N"}]
    assert [fmu.uid for fmu in result.simulation_config.fmus] == [controller.uid, plant.uid, adapter.uid]
    assert result.simulation_config.meta["final_solution_payload"] == {"loop_resolution": []}
    assert "current_pipeline_stage3_source_solution_override" not in result.diagnostics


def test_stage3_current_ignores_case_authored_policy_hints(tmp_path, monkeypatch) -> None:
    case_root = tmp_path / "case_manual_005"
    case_root.mkdir()
    (case_root / "case.json").write_text(
        json.dumps(
            {
                "current_pipeline_hints": {
                    "stage3_policy": "greedy_multirate",
                }
            }
        ),
        encoding="utf-8",
    )

    controller = _fmu("asset_case_case_manual_005__ThermalController", outputs=["pump_cmd"], inputs=["temp_cell_C"])
    coolant = _fmu("asset_case_case_manual_005__CoolantLoopPlant", outputs=["coolant_temp_C"], inputs=["pump_cmd"])
    matching_result = MatchingResult(
        task_set=TaskSet(tasks=[VerificationTask(task_id="t0", objective="thermal")]),
        assignments=[],
        selected_fmus=[controller, coolant],
        graph=OrchestrationGraph(nodes=[controller.uid, coolant.uid], bindings=[], component_to_fmu={}, closure_ok=True),
        discrepancy_set=[],
        diagnostics={"status": "ok"},
    )

    def fake_compose(matching_result, *, mbse_context, scenario_window=None):
        return CompositionResult(
            graph_augmented=matching_result.graph,
            adapters=[],
            schedule={"kind": "multi_rate"},
            loop_resolution=[],
            simulation_config=SimulationConfig(
                step_size=0.01,
                duration=1.0,
                fmus=[controller, coolant],
                connections=[],
                scheduler={"kind": "multi_rate"},
                meta={},
            ),
            diagnostics={},
        )

    monkeypatch.setattr(current_stage3, "compose", fake_compose)

    result = current_stage3.run_current_stage3(
        matching_result,
        mbse_context=_mbse_context(
            case_id="case_manual_005",
            source_type="manual_multi_fmu_case",
            case_root=str(case_root),
        ),
        config={},
    )

    assert result.schedule["kind"] == "multi_rate"
    assert result.simulation_config.scheduler["kind"] == "multi_rate"
    assert [fmu.uid for fmu in result.simulation_config.fmus] == [controller.uid, coolant.uid]
    assert "current_pipeline_stage3_policy" not in result.diagnostics


def test_stage3_current_ignores_runtime_start_value_hints(tmp_path, monkeypatch) -> None:
    case_root = tmp_path / "case_manual_004"
    case_root.mkdir()
    (case_root / "case.json").write_text(
        json.dumps(
            {
                "current_pipeline_hints": {
                    "runtime_start_values": [
                        {
                            "target": "asset_case_case_manual_004__PositionController.i_state",
                            "value": 0.0,
                        },
                        {
                            "target": "asset_case_case_manual_004__HydraulicCylinderPlant.pB_Pa_state",
                            "value": 5000000.0,
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    controller = _fmu("asset_case_case_manual_004__PositionController", outputs=["valve_cmd"], inputs=["x_m"])
    plant = _fmu("asset_case_case_manual_004__HydraulicCylinderPlant", outputs=["x_m"], inputs=["spool_u"])
    matching_result = MatchingResult(
        task_set=TaskSet(tasks=[VerificationTask(task_id="t0", objective="hydraulic")]),
        assignments=[],
        selected_fmus=[controller, plant],
        graph=OrchestrationGraph(nodes=[controller.uid, plant.uid], bindings=[], component_to_fmu={}, closure_ok=True),
        discrepancy_set=[],
        diagnostics={"status": "ok"},
    )

    def fake_compose(matching_result, *, mbse_context, scenario_window=None):
        return CompositionResult(
            graph_augmented=matching_result.graph,
            adapters=[],
            schedule={"kind": "multi_rate", "node_order": [controller.uid, plant.uid]},
            loop_resolution=[],
            simulation_config=SimulationConfig(
                step_size=0.01,
                duration=5.0,
                fmus=[controller, plant],
                connections=[{"source": f"{controller.uid}.valve_cmd", "target": f"{plant.uid}.spool_u"}],
                scheduler={"kind": "multi_rate", "node_order": [controller.uid, plant.uid]},
                meta={
                    "final_solution_payload": {
                        "extensions": {
                            "parameter_overrides": [
                                {
                                    "target": "asset_case_case_manual_004__HydraulicCylinderPlant.pB_Pa_state",
                                    "value": 10000000.0,
                                }
                            ]
                        }
                    }
                },
            ),
            diagnostics={},
        )

    monkeypatch.setattr(current_stage3, "compose", fake_compose)

    result = current_stage3.run_current_stage3(
        matching_result,
        mbse_context=_mbse_context(
            case_id="case_manual_004",
            source_type="manual_multi_fmu_case",
            case_root=str(case_root),
        ),
        config={},
    )

    overrides = result.simulation_config.meta["final_solution_payload"]["extensions"]["parameter_overrides"]
    override_map = {item["target"]: item["value"] for item in overrides}
    assert override_map == {"asset_case_case_manual_004__HydraulicCylinderPlant.pB_Pa_state": 10000000.0}
    assert "current_pipeline_stage3_runtime_start_value_count" not in result.diagnostics


def test_stage3_current_disables_loop_wrappers_for_manual_cases(monkeypatch) -> None:
    controller = _fmu("asset_case_case_manual_003__PendulumController", outputs=["force_cmd_N"], inputs=["x_m"])
    plant = _fmu("asset_case_case_manual_003__InvertedPendulumPlant", outputs=["x_m"], inputs=["force_cmd_N"])
    matching_result = MatchingResult(
        task_set=TaskSet(tasks=[VerificationTask(task_id="t0", objective="closed-loop")]),
        assignments=[],
        selected_fmus=[controller, plant],
        graph=OrchestrationGraph(nodes=[controller.uid, plant.uid], bindings=[], component_to_fmu={}, closure_ok=True),
        discrepancy_set=[],
        diagnostics={"status": "ok"},
    )

    def fake_compose(matching_result, *, mbse_context, scenario_window=None):
        return CompositionResult(
            graph_augmented=matching_result.graph,
            adapters=[],
            schedule={
                "kind": "multi_rate",
                "loop_wrappers": [{"loop_id": "loop_0"}],
                "execution_plan": [{"time": 0.0, "loop_ids": ["loop_0"], "active_loops": [{"loop_id": "loop_0"}], "requires_fixed_point_iteration": True}],
            },
            loop_resolution=[{"loop_id": "loop_0"}],
            simulation_config=SimulationConfig(
                step_size=0.01,
                duration=10.0,
                fmus=[controller, plant],
                connections=[],
                scheduler={
                    "kind": "multi_rate",
                    "loop_wrappers": [{"loop_id": "loop_0"}],
                    "execution_plan": [{"time": 0.0, "loop_ids": ["loop_0"], "active_loops": [{"loop_id": "loop_0"}], "requires_fixed_point_iteration": True}],
                },
                meta={},
            ),
            diagnostics={"loop_count": 1},
        )

    monkeypatch.setattr(current_stage3, "compose", fake_compose)

    result = current_stage3.run_current_stage3(
        matching_result,
        mbse_context=_mbse_context(
            case_id="case_manual_003",
            source_type="manual_multi_fmu_case",
        ),
        config={},
    )

    assert result.loop_resolution == []
    assert result.schedule["loop_wrappers"] == []
    assert result.schedule["execution_plan"][0]["loop_ids"] == []
    assert result.schedule["execution_plan"][0]["requires_fixed_point_iteration"] is False
    assert result.simulation_config.scheduler["loop_wrappers"] == []
    assert result.diagnostics["current_pipeline_stage3_loop_wrappers_disabled"] is True


def _mbse_context(
    *,
    case_id: str = "case_manual_001",
    source_type: str = "manual_multi_fmu_case",
    case_root: str | None = None,
) -> MBSEContext:
    metadata = {"case_id": case_id, "source_type": source_type}
    if case_root is not None:
        metadata["case_root"] = case_root
    return MBSEContext(
        package_name="pkg",
        system_name="system",
        components=[
            MBSEComponent(name="controller", component_type="controller", ports=[MBSEPort(component="controller", name="force_cmd_N", direction="out")]),
            MBSEComponent(name="plant", component_type="plant", ports=[MBSEPort(component="plant", name="x_m", direction="out")]),
        ],
        connections=[
            MBSEConnection(source_component="controller", source_signal="force_cmd_N", target_component="plant", target_signal="force_cmd_N"),
            MBSEConnection(source_component="plant", source_signal="x_m", target_component="controller", target_signal="x_m"),
        ],
        metadata=metadata,
    )


def _fmu(
    uid: str,
    *,
    source_type: str = "manual_case_fmu",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    tags: list[str] | None = None,
    provenance: dict[str, object] | None = None,
    source_id: str | None = None,
) -> FMU:
    input_names = list(inputs or [])
    output_names = list(outputs or [])
    ports = [PortMeta(name=name, causality="input") for name in input_names] + [
        PortMeta(name=name, causality="output") for name in output_names
    ]
    asset_json = {
        "asset_id": uid,
        "source_id": source_id or uid,
        "name": uid,
        "provenance": dict(provenance or {}),
    }
    return FMU(
        uid=uid,
        name=uid,
        ports=ports,
        inputs=input_names,
        outputs=output_names,
        tags=list(tags or []),
        meta={"source_type": source_type, "asset_json": asset_json},
    )
