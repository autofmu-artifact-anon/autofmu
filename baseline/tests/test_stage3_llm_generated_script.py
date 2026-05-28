"""Focused tests for the baseline LLM-generated-script Stage-3 module."""

from __future__ import annotations

import pytest

import baseline.common as common
import baseline.stage3.llm_generated_script as script_module
from pipeline.types import (
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


def _matching_result(*, with_loop: bool = False) -> MatchingResult:
    task_set = TaskSet(
        tasks=[
            VerificationTask(
                task_id="task-0",
                objective="verify scripted orchestration",
                grounded_components=["Sensor", "Controller"],
                operating_regime=OperatingRegime(start_time=0.0, end_time=0.2),
            )
        ],
        task_set_id="taskset-script",
    )
    selected_fmus = [
        FMU(
            uid="sensor",
            name="Sensor",
            outputs=["y"],
            meta={"default_experiment": {"stepSize": 0.1, "stopTime": 0.2}},
        ),
        FMU(
            uid="controller",
            name="Controller",
            inputs=["feedback"],
            outputs=["cmd"],
            meta={"default_experiment": {"stepSize": 0.2, "stopTime": 0.2}},
        ),
    ]
    bindings = [
        PortBinding(source_fmu="sensor", source_signal="y", target_fmu="controller", target_signal="feedback", score=0.9),
    ]
    if with_loop:
        bindings.append(
            PortBinding(source_fmu="controller", source_signal="cmd", target_fmu="sensor", target_signal="u", score=0.8),
        )
        selected_fmus[0] = FMU(
            uid="sensor",
            name="Sensor",
            inputs=["u"],
            outputs=["y"],
            meta={"default_experiment": {"stepSize": 0.1, "stopTime": 0.2}},
        )
    return MatchingResult(
        task_set=task_set,
        assignments=[
            TaskAssignment(task_id="task-0", task_index=0, fmu_uid="sensor"),
            TaskAssignment(task_id="task-0", task_index=0, fmu_uid="controller"),
        ],
        selected_fmus=selected_fmus,
        graph=OrchestrationGraph(
            nodes=["sensor", "controller"],
            bindings=bindings,
            component_to_fmu={"Sensor": "sensor", "Controller": "controller"},
            closure_ok=True,
        ),
        diagnostics={"stage2_variant": "fixture"},
    )


def test_llm_generated_script_stage3_uses_llm_final_payload_when_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompt: dict[str, object] = {}
    monkeypatch.setattr(
        script_module,
        "compose",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("compose() must not be called")),
        raising=False,
    )

    def fake_chat_json(system_prompt, user_prompt, *, temperature, max_tokens):
        del system_prompt, temperature, max_tokens
        captured_prompt.update(script_module.json.loads(user_prompt))
        return {
            "selected_asset_ids": ["sensor", "controller"],
            "connections": [{"source": "sensor.y", "target": "controller.feedback"}],
            "schedule": {
                "kind": "co_simulation",
                "start_time": 0.0,
                "stop_time": 0.2,
                "step_size": 0.05,
                "per_node_period": {"sensor": 0.1, "controller": 0.2},
                "node_order": ["sensor", "controller"],
            },
            "execution_order": ["sensor", "controller"],
            "adapters": [],
            "loop_resolution": [],
            "notes": ["llm-ok"],
        }

    monkeypatch.setattr(script_module, "chat_json", fake_chat_json)

    result = script_module.llm_generated_script_stage3(
        _matching_result(),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_llm_generated_script"),
    )

    assert result.schedule["generation_source"] == "llm"
    assert result.schedule["fallback_used"] is False
    assert result.simulation_config.step_size == pytest.approx(0.05)
    assert result.simulation_config.scheduler["per_node_period"] == {"sensor": 0.1, "controller": 0.2}
    assert [fmu.uid for fmu in result.simulation_config.fmus] == ["sensor", "controller"]
    assert result.simulation_config.meta["final_solution_payload"]["selected_asset_ids"] == ["sensor", "controller"]
    assert result.simulation_config.meta["script_generation_source"] == "llm"
    assert "base_payload" not in captured_prompt
    assert captured_prompt["selected_asset_ids"] == ["sensor", "controller"]
    assert "scenario_window" in captured_prompt


def test_llm_generated_script_stage3_rejects_asset_set_rewrite_and_uses_weak_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        script_module,
        "chat_json",
        lambda *args, **kwargs: {
            "selected_asset_ids": ["controller"],
            "connections": [],
            "schedule": {
                "kind": "single_fmu",
                "start_time": 0.0,
                "stop_time": 0.2,
                "step_size": 0.2,
                "node_order": ["controller"],
            },
            "execution_order": ["controller"],
            "adapters": [],
            "loop_resolution": [],
            "extensions": {"variant": "subset"},
            "notes": ["subset-picked"],
        },
    )

    result = script_module.llm_generated_script_stage3(
        _matching_result(),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_llm_generated_script"),
    )

    assert [fmu.uid for fmu in result.simulation_config.fmus] == ["sensor", "controller"]
    assert result.simulation_config.connections == []
    assert result.simulation_config.scheduler["kind"] == "fixed_step"
    assert result.simulation_config.meta["final_solution_payload"]["extensions"] == {}
    assert result.graph_augmented.nodes == ["sensor", "controller"]
    assert result.diagnostics["fallback_used"] is True


def test_llm_generated_script_stage3_falls_back_when_response_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        script_module,
        "chat_json",
        lambda *args, **kwargs: {
            "selected_asset_ids": ["unknown"],
            "connections": [],
            "schedule": {"kind": "co_simulation", "start_time": 0.0, "stop_time": 0.2, "step_size": 0.1},
            "execution_order": ["unknown"],
        },
    )

    result = script_module.llm_generated_script_stage3(
        _matching_result(),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_llm_generated_script"),
    )

    assert result.schedule["generation_source"] == "deterministic_fallback"
    assert result.schedule["fallback_used"] is True
    assert result.simulation_config.meta["final_solution_payload"]["selected_asset_ids"] == ["sensor", "controller"]
    assert result.simulation_config.meta["final_solution_payload"]["connections"] == []
    assert result.simulation_config.meta["script_generation_source"] == "deterministic_fallback"
    assert result.diagnostics["fallback_used"] is True


def test_llm_generated_script_stage3_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        script_module.llm_generated_script_stage3(
            _matching_result(),
            mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
            config={
                "method_name": "ablation_stage3_llm_generated_script",
                "workspace_root": str(common.method_workspace("ablation_stage3_greedy_multirate").resolve()),
            },
        )


def test_llm_generated_script_stage3_keeps_loop_and_adapter_outputs_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(script_module, "chat_json", lambda *args, **kwargs: {})

    result = script_module.llm_generated_script_stage3(
        _matching_result(with_loop=True),
        mbse_context=MBSEContext(package_name="pkg", system_name="sys"),
        config=_workspace_config("ablation_stage3_llm_generated_script"),
    )

    assert result.adapters == []
    assert result.loop_resolution == []
    assert result.simulation_config.connections == []
    assert result.simulation_config.scheduler["kind"] == "fixed_step"
    assert result.graph_augmented.diagnostics["adapter_generation"] is False
    assert result.graph_augmented.diagnostics["loop_wrapper_generation"] is False
    assert result.diagnostics["validation_issues"] == []
