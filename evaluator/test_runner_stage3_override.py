from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from evaluator.runner import _build_predicted_solution
from pipeline.types import CompositionResult, FMU, OrchestrationGraph, SimulationConfig, TaskSet, VerificationTask


def _loaded_case() -> SimpleNamespace:
    return SimpleNamespace(
        verification_requirement_payload={},
        trajectory_manifest_payload={},
        case_payload={"requirement": {"scenario": {}}},
        case_id="case-x",
    )


def _selected_fmus() -> list[FMU]:
    return [
        FMU(uid="a", name="A", outputs=["y"]),
        FMU(uid="b", name="B", inputs=["u"], outputs=["z"]),
    ]


def _selected_task_set() -> TaskSet:
    return TaskSet(
        tasks=[
            VerificationTask(
                task_id="task-0",
                objective="verify override",
                required_signals=["z"],
                grounded_components=["A", "B"],
            )
        ],
        task_set_id="taskset-override",
    )


def _composition_result(*, final_solution_payload: dict | None) -> CompositionResult:
    meta = {}
    if final_solution_payload is not None:
        meta["final_solution_payload"] = final_solution_payload
    return CompositionResult(
        graph_augmented=OrchestrationGraph(nodes=["a", "b"]),
        adapters=[],
        schedule={"kind": "co_simulation", "step_size": 0.1},
        loop_resolution=[],
        simulation_config=SimulationConfig(
            step_size=0.1,
            duration=1.0,
            fmus=_selected_fmus(),
            connections=[{"source": "a.y", "target": "b.u"}],
            scheduler={"kind": "co_simulation", "step_size": 0.1},
            meta=meta,
        ),
        diagnostics={},
    )


def test_build_predicted_solution_uses_stage3_final_payload_override() -> None:
    override = {
        "selected_asset_ids": ["b"],
        "connections": [],
        "schedule": {
            "kind": "single_fmu",
            "start_time": 0.0,
            "stop_time": 1.0,
            "step_size": 0.2,
        },
        "execution_order": ["b"],
        "adapters": [],
        "loop_resolution": [],
        "extensions": {"stage3": "kept"},
        "notes": ["override-note"],
    }

    def fake_monitored_outputs(*, selected_fmus, **kwargs):
        del kwargs
        assert [fmu.uid for fmu in selected_fmus] == ["b"]
        return ([{"name": "built-monitor", "source": "b.z"}], ["monitor-built"])

    def fake_external_inputs(*, selected_fmus, **kwargs):
        del kwargs
        assert [fmu.uid for fmu in selected_fmus] == ["b"]
        return ([{"name": "ext", "target": "b.u"}], ["ext-built"])

    def fake_initial_conditions(*, selected_fmus, **kwargs):
        del kwargs
        assert [fmu.uid for fmu in selected_fmus] == ["b"]
        return ([{"target": "b.x", "value": 1.0}], ["init-built"])

    with (
        patch("evaluator.runner.build_monitored_outputs", side_effect=fake_monitored_outputs),
        patch("evaluator.runner.build_external_input_bindings", side_effect=fake_external_inputs),
        patch("evaluator.runner.build_initial_condition_bindings", side_effect=fake_initial_conditions),
        patch("evaluator.runner.derive_execution_order", return_value=["a", "b"]),
        patch(
            "evaluator.runner._bootstrap_reference_solution_metadata",
            return_value={
                "external_inputs": [{"name": "ref-ext", "target": "b.u"}],
                "initial_conditions": [{"target": "b.x", "value": 2.0}],
                "monitored_outputs": [{"name": "ref-monitor", "source": "b.z"}],
                "schedule": {"kind": "bootstrap-ref"},
                "execution_order": ["ref-order"],
            },
        ),
        patch(
            "evaluator.runner._bootstrap_source_orchestration",
            return_value={
                "extensions": {"source": "should-not-win"},
                "monitored_outputs": [{"name": "source-monitor", "source": "b.z"}],
                "schedule": {"kind": "bootstrap-source"},
            },
        ),
    ):
        predicted_solution = _build_predicted_solution(
            loaded=_loaded_case(),
            case_id="case-x",
            selected_task_set=_selected_task_set(),
            selected_fmus=_selected_fmus(),
            composition_result=_composition_result(final_solution_payload=override),
        )

    assert predicted_solution["selected_asset_ids"] == ["b"]
    assert predicted_solution["connections"] == []
    assert predicted_solution["schedule"]["kind"] == "single_fmu"
    assert predicted_solution["execution_order"] == ["b"]
    assert predicted_solution["extensions"] == {"stage3": "kept"}
    assert predicted_solution["external_inputs"] == [{"name": "ref-ext", "target": "b.u"}]
    assert predicted_solution["initial_conditions"] == [{"target": "b.x", "value": 2.0}]
    assert predicted_solution["monitored_outputs"] == [{"name": "source-monitor", "source": "b.z"}]
    assert "override-note" in predicted_solution["notes"]
    assert "reference_solution_schedule_bootstrap" not in predicted_solution["notes"]
    assert "reference_solution_execution_order_bootstrap" not in predicted_solution["notes"]
    assert "source_orchestration_schedule_bootstrap" not in predicted_solution["notes"]
    assert "source_orchestration_extension_bootstrap" not in predicted_solution["notes"]


def test_build_predicted_solution_keeps_bootstrap_behavior_without_override() -> None:
    with (
        patch("evaluator.runner.build_monitored_outputs", return_value=([{"name": "built", "source": "a.y"}], [])),
        patch("evaluator.runner.build_external_input_bindings", return_value=([], [])),
        patch("evaluator.runner.build_initial_condition_bindings", return_value=([], [])),
        patch("evaluator.runner.derive_execution_order", return_value=["a", "b"]),
        patch(
            "evaluator.runner._bootstrap_reference_solution_metadata",
            return_value={
                "schedule": {"kind": "bootstrap-ref"},
                "execution_order": ["ref-order"],
            },
        ),
        patch(
            "evaluator.runner._bootstrap_source_orchestration",
            return_value={
                "extensions": {"source": "kept"},
                "schedule": {"kind": "bootstrap-source"},
            },
        ),
    ):
        predicted_solution = _build_predicted_solution(
            loaded=_loaded_case(),
            case_id="case-x",
            selected_task_set=_selected_task_set(),
            selected_fmus=_selected_fmus(),
            composition_result=_composition_result(final_solution_payload=None),
        )

    assert predicted_solution["schedule"] == {"kind": "bootstrap-source"}
    assert predicted_solution["execution_order"] == ["ref-order"]
    assert predicted_solution["extensions"] == {"source": "kept"}
    assert "reference_solution_schedule_bootstrap" in predicted_solution["notes"]
    assert "reference_solution_execution_order_bootstrap" in predicted_solution["notes"]
    assert "source_orchestration_schedule_bootstrap" in predicted_solution["notes"]
    assert "source_orchestration_extension_bootstrap" in predicted_solution["notes"]
