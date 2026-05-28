"""Focused tests for the baseline greedy-hybrid Stage-2 module."""

from __future__ import annotations

import pytest

import baseline.common as common
import baseline.stage2.greedy_hybrid as hybrid_module
from pipeline.types import FMU, MatchingResult, OrchestrationGraph, TaskSet, VerificationTask


def _workspace_config(method_name: str) -> dict[str, str]:
    return {
        "method_name": method_name,
        "workspace_root": str(common.method_workspace(method_name).resolve()),
    }


def _taskset(task_set_id: str) -> TaskSet:
    return TaskSet(
        tasks=[VerificationTask(task_id=f"{task_set_id}-0", objective=f"verify {task_set_id}", grounded_components=["Controller"], required_signals=["cmd"])],
        task_set_id=task_set_id,
    )


def test_greedy_hybrid_stage2_repairs_once_from_failure_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    taskset = _taskset("taskset-a")
    fmu_library = [FMU(uid="fmu-alpha", name="Alpha"), FMU(uid="fmu-beta", name="Beta")]

    monkeypatch.setattr(
        hybrid_module,
        "_combined_cost_matrix",
        lambda *args, **kwargs: (
            [[0.1, 0.4]],
            [[0.2, 0.2]],
            [[0.15, 0.30]],
            [[["signal_support"], ["signal_support"]]],
        ),
    )

    calls: list[list[str]] = []

    def fake_graph(task_set, assignments, mbse_context, fmu_by_uid, max_port_candidates, ambiguity_resolver):
        calls.append([assignment.fmu_uid for assignment in assignments])
        assert ambiguity_resolver is not None
        if len(calls) == 1:
            return {
                "graph": OrchestrationGraph(nodes=[], bindings=[], component_to_fmu={}, closure_ok=False),
                "discrepancy_set": [],
                "closure_ok": False,
                "closure_failure": {
                    "failure_type": "component_mapping_conflict",
                    "failure_class": "routing_failure",
                    "responsible_pair": (0, "fmu-alpha"),
                    "eligible_for_mask_revision": True,
                },
            }
        return {
            "graph": OrchestrationGraph(nodes=["fmu-beta"], bindings=[], component_to_fmu={"Controller": "fmu-beta"}, closure_ok=True),
            "discrepancy_set": [],
            "closure_ok": True,
            "closure_failure": None,
        }

    monkeypatch.setattr(hybrid_module, "instantiate_port_graph", fake_graph)

    result = hybrid_module.greedy_hybrid_stage2(
        [taskset],
        mbse_context=object(),
        fmu_library=fmu_library,
        config=_workspace_config("ablation_stage2_greedy_hybrid"),
    )

    assert isinstance(result, MatchingResult)
    assert calls == [["fmu-alpha"], ["fmu-beta"]]
    assert [assignment.fmu_uid for assignment in result.assignments] == ["fmu-beta"]
    assert result.diagnostics["repair_used"] is True
    assert result.diagnostics["repair_attempted"] is True
    assert result.diagnostics["repair_succeeded"] is True
    assert result.diagnostics["stage2_variant"] == "greedy_hybrid"
    assert result.taskset_results[0]["task_set_id"] == "taskset-a"
    assert result.taskset_results[0]["selected_fmus"] == ["fmu-beta"]


def test_greedy_hybrid_stage2_reports_failed_assignment_when_no_candidate_is_feasible(monkeypatch: pytest.MonkeyPatch) -> None:
    taskset = _taskset("taskset-a")
    monkeypatch.setattr(
        hybrid_module,
        "_combined_cost_matrix",
        lambda *args, **kwargs: (
            [[0.1]],
            [[float("inf")]],
            [[float("inf")]],
            [[["signal_support"]]],
        ),
    )

    result = hybrid_module.greedy_hybrid_stage2(
        [taskset],
        mbse_context=object(),
        fmu_library=[FMU(uid="fmu-alpha", name="Alpha")],
        config=_workspace_config("baseline_b3_graph_aware"),
    )

    assert result.assignments == []
    assert result.selected_fmus == []
    assert result.diagnostics["status"] == "failed"
    assert result.diagnostics["failure_type"] == "no_feasible_assignment"
    assert result.taskset_results[0]["task_set_id"] == "taskset-a"
    assert result.taskset_results[0]["selected_fmus"] == []


def test_greedy_hybrid_stage2_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        hybrid_module.greedy_hybrid_stage2(
            [_taskset("taskset-a")],
            mbse_context=object(),
            fmu_library=[FMU(uid="fmu-0", name="FMU 0")],
            config={
                "method_name": "ablation_stage2_greedy_hybrid",
                "workspace_root": str(common.method_workspace("baseline_b3_graph_aware").resolve()),
            },
        )
