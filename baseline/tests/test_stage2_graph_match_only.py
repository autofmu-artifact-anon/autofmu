"""Focused tests for the baseline structure-first Stage-2 module."""

from __future__ import annotations

from dataclasses import replace

import pytest

import baseline.common as common
import baseline.stage2.graph_match_only as graph_module
from pipeline.types import FMU, MatchingResult, OrchestrationGraph, TaskSet, VerificationTask


def _workspace_config(method_name: str) -> dict[str, str]:
    return {
        "method_name": method_name,
        "workspace_root": str(common.method_workspace(method_name).resolve()),
    }


def _taskset(task_set_id: str, *components: str) -> TaskSet:
    return TaskSet(
        tasks=[
            VerificationTask(
                task_id=f"{task_set_id}-0",
                objective=f"verify {task_set_id}",
                grounded_components=list(components) or ["Component"],
                required_signals=["y"],
            )
        ],
        task_set_id=task_set_id,
    )


def test_graph_match_only_stage2_prefers_closure_ok_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    taskset_a = _taskset("taskset-a", "Battery")
    taskset_b = _taskset("taskset-b", "Cooling")
    fmu_library = [FMU(uid="fmu-alpha", name="Alpha"), FMU(uid="fmu-beta", name="Beta")]

    def fake_structural_matrix(task_set, *, mbse_context, fmu_library):
        if task_set.task_set_id == "taskset-a":
            return [[0.05, 0.4]], [[0.95, 0.6]], [[["signal_support"], ["signal_support"]]]
        return [[0.2, 0.3]], [[0.8, 0.7]], [[["signal_support"], ["signal_support"]]]

    def fake_graph(task_set, assignments, mbse_context, fmu_by_uid, max_port_candidates, ambiguity_resolver):
        assert max_port_candidates == 8
        assert ambiguity_resolver is not None
        if task_set.task_set_id == "taskset-a":
            failure = {"failure_type": "unroutable_segment", "failure_class": "routing_failure"}
            return {
                "graph": OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False),
                "discrepancy_set": [],
                "closure_ok": False,
                "closure_failure": failure,
            }
        return {
            "graph": OrchestrationGraph(nodes=["fmu-alpha"], bindings=[], component_to_fmu={"Cooling": "fmu-alpha"}, closure_ok=True),
            "discrepancy_set": [],
            "closure_ok": True,
            "closure_failure": None,
        }

    monkeypatch.setattr(graph_module, "_build_structural_cost_matrix", fake_structural_matrix)
    monkeypatch.setattr(graph_module, "instantiate_port_graph", fake_graph)

    result = graph_module.graph_match_only_stage2(
        [taskset_a, taskset_b],
        mbse_context=object(),
        fmu_library=fmu_library,
        config=_workspace_config("ablation_stage2_graph_match_only"),
    )

    assert isinstance(result, MatchingResult)
    assert result.task_set is taskset_b
    assert result.diagnostics["stage2_variant"] == "graph_match_only"
    assert result.diagnostics["fallback_used"] is False
    assert result.diagnostics["failure_type"] == ""
    assert result.graph.closure_ok is True
    assert [assignment.fmu_uid for assignment in result.assignments] == ["fmu-alpha"]
    assert [row["task_set_id"] for row in result.taskset_results] == ["taskset-a", "taskset-b"]
    assert result.taskset_results[0]["status"] == "failed"
    assert result.taskset_results[0]["selected_fmus"] == ["fmu-alpha"]
    assert result.taskset_results[1]["status"] == "ok"
    assert result.taskset_results[1]["selected_fmus"] == ["fmu-alpha"]


def test_graph_match_only_stage2_uses_component_cover_fallback_only_after_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    taskset = _taskset("taskset-a", "Battery")
    fmu_library = [FMU(uid="fmu-alpha", name="Alpha")]

    monkeypatch.setattr(
        graph_module,
        "_build_structural_cost_matrix",
        lambda *args, **kwargs: (
            [[0.2]],
            [[0.8]],
            [[["signal_support"]]],
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "instantiate_port_graph",
        lambda *args, **kwargs: {
            "graph": OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False),
            "discrepancy_set": [],
            "closure_ok": False,
            "closure_failure": {"failure_type": "unroutable_segment", "failure_class": "routing_failure"},
        },
    )

    def fake_fallback(result, mbse_context, fmu_library):
        assert result.selected_fmus == []
        return replace(
            result,
            selected_fmus=list(fmu_library),
            final_cost=0.1,
            selected_task_set_cost=0.1,
            diagnostics={"status": "mbse_component_cover_fallback"},
        )

    monkeypatch.setattr(graph_module, "_apply_mbse_component_cover_fallback", fake_fallback)

    result = graph_module.graph_match_only_stage2(
        [taskset],
        mbse_context=object(),
        fmu_library=fmu_library,
        config=_workspace_config("baseline_b1_rule_sequential"),
    )

    assert [fmu.uid for fmu in result.selected_fmus] == ["fmu-alpha"]
    assert result.diagnostics["stage2_variant"] == "graph_match_only"
    assert result.diagnostics["fallback_used"] is True
    assert result.diagnostics["fallback_source"] == "mbse_component_cover"
    assert result.taskset_results[0]["task_set_id"] == "taskset-a"
    assert result.taskset_results[0]["selected_fmus"] == ["fmu-alpha"]


def test_graph_match_only_stage2_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        graph_module.graph_match_only_stage2(
            [_taskset("taskset-a", "Battery")],
            mbse_context=object(),
            fmu_library=[FMU(uid="fmu-0", name="FMU 0")],
            config={
                "method_name": "ablation_stage2_graph_match_only",
                "workspace_root": str(common.method_workspace("baseline_b1_rule_sequential").resolve()),
            },
        )
