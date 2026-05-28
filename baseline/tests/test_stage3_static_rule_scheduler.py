"""Focused tests for the baseline static-rule Stage-3 scheduler."""

from __future__ import annotations

import pytest

import baseline.common as common
import baseline.stage3.static_rule_scheduler as scheduler_module
from pipeline.types import (
    DiscrepancyEdge,
    FMU,
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


def _matching_result(
    *,
    async_edge: bool = False,
    requires_loop_handling: bool = False,
    branch: bool = False,
) -> MatchingResult:
    task_set = TaskSet(
        tasks=[
            VerificationTask(
                task_id="task-0",
                objective="verify chain execution",
                grounded_components=["Sensor", "Controller", "Plant"],
                operating_regime=OperatingRegime(start_time=0.0, end_time=0.3),
            )
        ],
        task_set_id="taskset-chain",
    )
    selected_fmus = [
        FMU(
            uid="controller",
            name="Controller",
            meta={"default_experiment": {"stepSize": 0.2 if async_edge else 0.1, "stopTime": 0.3}},
        ),
        FMU(uid="plant", name="Plant", meta={"default_experiment": {"stepSize": 0.1, "stopTime": 0.3}}),
        FMU(uid="sensor", name="Sensor", meta={"default_experiment": {"stepSize": 0.1, "stopTime": 0.3}}),
    ]
    bindings = [
        PortBinding(source_fmu="controller", source_signal="cmd", target_fmu="plant", target_signal="u", score=0.8),
        PortBinding(source_fmu="sensor", source_signal="y", target_fmu="controller", target_signal="feedback", score=0.9),
    ]
    if requires_loop_handling:
        bindings.append(
            PortBinding(
                source_fmu="plant",
                source_signal="y_hat",
                target_fmu="sensor",
                target_signal="u",
                score=0.7,
            )
        )
    if branch:
        bindings.append(
            PortBinding(
                source_fmu="sensor",
                source_signal="y_aux",
                target_fmu="plant",
                target_signal="u_aux",
                score=0.6,
            )
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
        "ablation_stage3_static_rule_scheduler",
        "baseline_b1_rule_sequential",
        "baseline_b2_llm_retrieval_rule",
    ],
)
def test_static_rule_scheduler_stage3_builds_deterministic_chain_schedule(method_name: str) -> None:
    result = scheduler_module.static_rule_scheduler_stage3(
        _matching_result(),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config(method_name),
    )

    assert result.adapters == []
    assert result.loop_resolution == []
    assert result.schedule["family"] == "chain"
    assert result.schedule["node_order"] == ["sensor", "controller", "plant"]
    assert result.diagnostics["validation_issues"] == []
    assert [fmu.uid for fmu in result.simulation_config.fmus] == ["sensor", "controller", "plant"]
    assert [item["source"] for item in result.simulation_config.connections] == [
        "sensor.y",
        "controller.cmd",
    ]
    assert [item["target"] for item in result.simulation_config.connections] == [
        "controller.feedback",
        "plant.u",
    ]
    assert result.simulation_config.scheduler["family"] == "chain"
    assert result.simulation_config.scheduler["node_order"] == ["sensor", "controller", "plant"]
    assert result.simulation_config.scheduler["execution_plan"][0]["active_nodes"] == [
        "sensor",
        "controller",
        "plant",
    ]
    assert result.simulation_config.step_size == pytest.approx(0.1)


def test_static_rule_scheduler_stage3_uses_coarse_step_for_rate_mismatch() -> None:
    result = scheduler_module.static_rule_scheduler_stage3(
        _matching_result(async_edge=True),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_static_rule_scheduler"),
    )

    assert result.simulation_config.step_size == pytest.approx(0.2)
    assert result.schedule["per_node_period"] == {
        "sensor": pytest.approx(0.2),
        "controller": pytest.approx(0.2),
        "plant": pytest.approx(0.2),
    }


def test_static_rule_scheduler_stage3_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        scheduler_module.static_rule_scheduler_stage3(
            _matching_result(),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config={
                "method_name": "ablation_stage3_static_rule_scheduler",
                "workspace_root": str(common.method_workspace("baseline_b2_llm_retrieval_rule").resolve()),
            },
        )


def test_static_rule_scheduler_stage3_rejects_discrepancy_set() -> None:
    with pytest.raises(ValueError, match="discrepancy_set"):
        scheduler_module.static_rule_scheduler_stage3(
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
            config=_workspace_config("ablation_stage3_static_rule_scheduler"),
        )


def test_static_rule_scheduler_stage3_rejects_non_chain_topology() -> None:
    with pytest.raises(ValueError, match="strict chain topology"):
        scheduler_module.static_rule_scheduler_stage3(
            _matching_result(branch=True),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config=_workspace_config("ablation_stage3_static_rule_scheduler"),
        )


def test_static_rule_scheduler_stage3_rejects_loop_handling_requirement() -> None:
    with pytest.raises(ValueError, match="loop handling"):
        scheduler_module.static_rule_scheduler_stage3(
            _matching_result(requires_loop_handling=True),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config=_workspace_config("ablation_stage3_static_rule_scheduler"),
        )
