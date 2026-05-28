"""Focused tests for the baseline semantic-only Stage-2 module."""

from __future__ import annotations

import importlib

import pytest

import baseline.common as common
import baseline.stage1.top1_llm as top1_module
import baseline.stage2.semantic_retrieval_only as semantic_module
import baseline.stage3.static_rule_scheduler as static_module
import evaluator.registry as registry
from pipeline.types import FMU, MatchingResult, OrchestrationGraph, TaskSet, VerificationTask


def _workspace_config(method_name: str) -> dict[str, str]:
    return {
        "method_name": method_name,
        "workspace_root": str(common.method_workspace(method_name).resolve()),
    }


def test_semantic_retrieval_only_stage2_selects_lowest_cost_taskset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    taskset_a = TaskSet(
        tasks=[
            VerificationTask(task_id="a0", objective="task a0", grounded_components=["Battery"]),
            VerificationTask(task_id="a1", objective="task a1", grounded_components=["Cooling"]),
        ],
        task_set_id="taskset-a",
    )
    taskset_b = TaskSet(
        tasks=[VerificationTask(task_id="b0", objective="task b0", grounded_components=["Controller"])],
        task_set_id="taskset-b",
    )
    fmu_library = [
        FMU(uid="fmu-alpha", name="Alpha"),
        FMU(uid="fmu-beta", name="Beta"),
    ]

    def fake_semantic_matrix(task_set, fmu_library):
        assert list(fmu_library) == fmu_library
        if task_set.task_set_id == "taskset-a":
            return [[0.2, 0.6], [0.8, 0.1]]
        if task_set.task_set_id == "taskset-b":
            return [[0.5, 0.7]]
        raise AssertionError(f"unexpected task set {task_set.task_set_id}")

    monkeypatch.setattr(semantic_module, "build_semantic_cost_matrix", fake_semantic_matrix)
    monkeypatch.setattr(semantic_module, "_apply_source_type_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_runtime_capability_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_grounded_component_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_grounded_component_type_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        semantic_module,
        "instantiate_port_graph",
        lambda task_set, assignments, mbse_context, fmu_by_uid, max_port_candidates, ambiguity_resolver: {
            "graph": OrchestrationGraph(
                nodes=[assignment.fmu_uid for assignment in assignments],
                bindings=[],
                component_to_fmu={"Battery": "fmu-alpha", "Cooling": "fmu-beta"},
                closure_ok=True,
            ),
            "discrepancy_set": [],
            "closure_ok": True,
            "closure_failure": None,
        },
    )

    result = semantic_module.semantic_retrieval_only_stage2(
        [taskset_a, taskset_b],
        mbse_context=object(),
        fmu_library=fmu_library,
        config=_workspace_config("ablation_stage2_semantic_retrieval_only"),
    )

    assert isinstance(result, MatchingResult)
    assert result.task_set is taskset_a
    assert [assignment.fmu_uid for assignment in result.assignments] == ["fmu-alpha", "fmu-beta"]
    assert result.selected_task_set_cost == pytest.approx(0.3)
    assert result.final_cost == pytest.approx(0.3)
    assert [fmu.uid for fmu in result.selected_fmus] == ["fmu-alpha", "fmu-beta"]
    assert result.graph.closure_ok is True
    assert result.graph.component_to_fmu == {"Battery": "fmu-alpha", "Cooling": "fmu-beta"}
    assert result.diagnostics["stage2_variant"] == "semantic_retrieval_only"
    assert [row["task_set_id"] for row in result.taskset_results] == ["taskset-a", "taskset-b"]
    assert result.taskset_results[0]["selected_fmus"] == ["fmu-alpha", "fmu-beta"]
    assert result.taskset_results[1]["selected_fmus"] == ["fmu-alpha"]


def test_semantic_retrieval_only_stage2_clears_selected_fmus_when_graph_does_not_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    taskset = TaskSet(
        tasks=[VerificationTask(task_id="t0", objective="task", grounded_components=["Controller"])],
        task_set_id="taskset-a",
    )
    fmu_library = [FMU(uid="fmu-alpha", name="Alpha")]

    monkeypatch.setattr(semantic_module, "build_semantic_cost_matrix", lambda *args, **kwargs: [[0.1]])
    monkeypatch.setattr(semantic_module, "_apply_source_type_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_runtime_capability_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_grounded_component_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(semantic_module, "_apply_grounded_component_type_prior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        semantic_module,
        "instantiate_port_graph",
        lambda *args, **kwargs: {
            "graph": OrchestrationGraph(nodes=["fmu-alpha"], bindings=[], component_to_fmu={}, closure_ok=False),
            "discrepancy_set": [],
            "closure_ok": False,
            "closure_failure": {"failure_type": "unroutable_segment", "failure_class": "routing_failure"},
        },
    )

    result = semantic_module.semantic_retrieval_only_stage2(
        [taskset],
        mbse_context=object(),
        fmu_library=fmu_library,
        config=_workspace_config("ablation_stage2_semantic_retrieval_only"),
    )

    assert result.selected_fmus == []
    assert result.graph.closure_ok is False
    assert result.diagnostics["status"] == "failed"
    assert result.diagnostics["failure_type"] == "unroutable_segment"
    assert result.taskset_results[0]["selected_fmus"] == ["fmu-alpha"]


def test_semantic_retrieval_only_stage2_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        semantic_module.semantic_retrieval_only_stage2(
            [TaskSet(tasks=[VerificationTask(task_id="t0", objective="task")])],
            mbse_context=object(),
            fmu_library=[FMU(uid="fmu-0", name="FMU 0")],
            config={
                "method_name": "ablation_stage2_semantic_retrieval_only",
                "workspace_root": str(common.method_workspace("baseline_b2_llm_retrieval_rule").resolve()),
            },
        )


def test_stage2_bundles_use_semantic_retrieval_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import baseline.bundles.ablation_stage2_semantic_retrieval_only as ablation_bundle
    import baseline.bundles.baseline_b2_llm_retrieval_rule as b2_bundle

    captured: list[dict[str, object]] = []

    def fake_build_bundle(**kwargs):
        captured.append(dict(kwargs))
        return f"bundle-{len(captured)}"

    def fake_register_bundle(bundle):
        captured[-1]["registered"] = bundle

    monkeypatch.setattr(common, "build_bundle", fake_build_bundle)
    monkeypatch.setattr(registry, "register_bundle", fake_register_bundle)

    importlib.reload(ablation_bundle)
    importlib.reload(b2_bundle)

    assert captured[0]["name"] == "ablation_stage2_semantic_retrieval_only"
    assert captured[0]["stage1"] is common.current_stage1
    assert captured[0]["stage2"] is semantic_module.semantic_retrieval_only_stage2
    assert captured[0]["stage3"] is common.current_stage3
    assert captured[0]["registered"] == "bundle-1"

    assert captured[1]["name"] == "baseline_b2_llm_retrieval_rule"
    assert captured[1]["stage1"] is top1_module.top1_llm_stage1
    assert captured[1]["stage2"] is semantic_module.semantic_retrieval_only_stage2
    assert captured[1]["stage3"] is static_module.static_rule_scheduler_stage3
    assert captured[1]["registered"] == "bundle-2"
