"""Focused tests for the baseline greedy multi-rate Stage-3 scheduler."""

from __future__ import annotations

import pytest

import baseline.common as common
import baseline.stage3.greedy_multirate_scheduler as scheduler_module
from pipeline.types import (
    DiscrepancyEdge,
    FMU,
    FMUCapabilities,
    MBSEContext,
    MatchingResult,
    OperatingRegime,
    OrchestrationGraph,
    PortBinding,
    TaskAssignment,
    TaskSet,
    VerificationTask,
)


def _workspace_config(method_name: str) -> dict[str, str]:
    return {
        "method_name": method_name,
        "workspace_root": str(common.method_workspace(method_name).resolve()),
    }


def _matching_result(*, unsupported_rate: bool = False, cycle: bool = False) -> MatchingResult:
    task_set = TaskSet(
        tasks=[
            VerificationTask(
                task_id="task-0",
                objective="verify greedy multirate execution",
                grounded_components=["Sensor", "Controller", "Plant"],
                operating_regime=OperatingRegime(start_time=0.0, end_time=0.3),
            )
        ],
        task_set_id="taskset-greedy",
    )
    selected_fmus = [
        FMU(uid="controller", name="Controller", meta={"default_experiment": {"stepSize": 0.15, "stopTime": 0.3}}),
        FMU(
            uid="plant",
            name="Plant",
            meta={"default_experiment": {"stepSize": 0.35, "stopTime": 0.3}},
            capabilities=FMUCapabilities(
                can_handle_variable_communication_step_size=not unsupported_rate,
                fixed_internal_step_size=0.35 if unsupported_rate else None,
            ),
        ),
        FMU(uid="sensor", name="Sensor", meta={"default_experiment": {"stepSize": 0.1, "stopTime": 0.3}}),
    ]
    bindings = [
        PortBinding(source_fmu="sensor", source_signal="y", target_fmu="controller", target_signal="feedback", score=0.9),
        PortBinding(source_fmu="controller", source_signal="cmd", target_fmu="plant", target_signal="u", score=0.8),
    ]
    if cycle:
        bindings.append(
            PortBinding(source_fmu="plant", source_signal="y", target_fmu="sensor", target_signal="u", score=0.7)
        )
    return MatchingResult(
        task_set=task_set,
        assignments=[
            TaskAssignment(task_id="task-0", task_index=0, fmu_uid="sensor"),
            TaskAssignment(task_id="task-0", task_index=0, fmu_uid="controller"),
            TaskAssignment(task_id="task-0", task_index=0, fmu_uid="plant"),
        ],
        selected_fmus=selected_fmus,
        graph=OrchestrationGraph(
            nodes=["plant", "sensor", "controller"],
            bindings=bindings,
            component_to_fmu={"Sensor": "sensor", "Controller": "controller", "Plant": "plant"},
            closure_ok=True,
        ),
        diagnostics={"stage2_variant": "fixture"},
    )


@pytest.mark.parametrize(
    "method_name",
    [
        "ablation_stage3_greedy_multirate",
        "baseline_b3_graph_aware",
    ],
)
def test_greedy_multirate_scheduler_stage3_adjusts_periods_and_orders_nodes(method_name: str) -> None:
    result = scheduler_module.greedy_multirate_scheduler_stage3(
        _matching_result(),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config(method_name),
    )

    assert result.adapters == []
    assert result.loop_resolution == []
    assert result.schedule["family"] == "greedy_multirate"
    assert result.schedule["node_order"] == ["sensor", "controller", "plant"]
    assert result.schedule["base_tick"] == pytest.approx(0.35)
    assert result.schedule["adjusted_nodes"]["controller"]["new_step"] == pytest.approx(0.7)
    assert result.schedule["adjusted_nodes"]["plant"]["new_step"] == pytest.approx(0.7)
    assert result.simulation_config.scheduler["family"] == "greedy_multirate"
    assert result.simulation_config.scheduler["node_order"] == ["sensor", "controller", "plant"]
    assert result.simulation_config.scheduler["adjusted_nodes"]["controller"]["aligned_with"] == ""
    assert result.simulation_config.scheduler["adjusted_nodes"]["plant"]["aligned_with"] == ""
    assert result.simulation_config.scheduler["async_edges"]
    assert result.simulation_config.scheduler["execution_plan"][0]["active_nodes"] == [
        "sensor",
        "controller",
        "plant",
    ]
    assert result.diagnostics["stage3_variant"] == "greedy_multirate_scheduler"


def test_greedy_multirate_scheduler_stage3_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        scheduler_module.greedy_multirate_scheduler_stage3(
            _matching_result(),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config={
                "method_name": "ablation_stage3_greedy_multirate",
                "workspace_root": str(common.method_workspace("baseline_b3_graph_aware").resolve()),
            },
        )


def test_greedy_multirate_scheduler_stage3_rejects_discrepancy_set() -> None:
    with pytest.raises(ValueError, match="discrepancy_set"):
        scheduler_module.greedy_multirate_scheduler_stage3(
            MatchingResult(
                **{
                    **_matching_result().__dict__,
                    "discrepancy_set": [
                        DiscrepancyEdge(
                            source_fmu="sensor",
                            source_signal="y",
                            target_fmu="controller",
                            target_signal="feedback",
                            kind="unit_mismatch",
                        )
                    ],
                }
            ),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config=_workspace_config("ablation_stage3_greedy_multirate"),
        )


def test_greedy_multirate_scheduler_stage3_linearizes_cycle() -> None:
    result = scheduler_module.greedy_multirate_scheduler_stage3(
        _matching_result(cycle=True),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_greedy_multirate"),
    )

    assert [item["source"] for item in result.simulation_config.connections] == [
        "sensor.y",
        "controller.cmd",
    ]
    assert [item["target"] for item in result.simulation_config.connections] == [
        "controller.feedback",
        "plant.u",
    ]


def test_greedy_multirate_scheduler_stage3_keeps_coarse_rate_even_for_fixed_step_nodes() -> None:
    result = scheduler_module.greedy_multirate_scheduler_stage3(
        _matching_result(unsupported_rate=True),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_greedy_multirate"),
    )

    assert result.simulation_config.step_size == pytest.approx(0.35)
    assert result.simulation_config.scheduler["per_node_period"] == {
        "sensor": pytest.approx(0.35),
        "controller": pytest.approx(0.7),
        "plant": pytest.approx(0.7),
    }
