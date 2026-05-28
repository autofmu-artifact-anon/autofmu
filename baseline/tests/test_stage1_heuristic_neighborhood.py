"""Focused tests for the baseline heuristic-neighborhood Stage-1 module."""

from __future__ import annotations

import importlib

import pytest

import baseline.common as common
import baseline.stage1.heuristic_neighborhood as heuristic_module
import evaluator.registry as registry
from pipeline.types import MBSEComponent, MBSEConnection, MBSEContext, MBSEPort, TaskSet


def _workspace_config(method_name: str) -> dict[str, str]:
    return {
        "method_name": method_name,
        "workspace_root": str(common.method_workspace(method_name).resolve()),
    }


def _mbse_context() -> MBSEContext:
    return MBSEContext(
        package_name="pkg",
        system_name="sys",
        components=[
            MBSEComponent(name="Sensor", component_type="Sensor", ports=[MBSEPort(component="Sensor", name="feedback", direction="out")]),
            MBSEComponent(name="Controller", component_type="Controller", ports=[MBSEPort(component="Controller", name="command", direction="out")]),
            MBSEComponent(name="Plant", component_type="Plant", ports=[MBSEPort(component="Plant", name="pressure", direction="out")]),
        ],
        adjacency={"Sensor": ["Controller"], "Controller": ["Plant"]},
        connections=[
            MBSEConnection(source_component="Sensor", source_signal="feedback", target_component="Controller", target_signal="feedback"),
            MBSEConnection(source_component="Controller", source_signal="command", target_component="Plant", target_signal="command"),
        ],
    )


def test_heuristic_neighborhood_stage1_builds_single_candidate_and_strips_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, TaskSet] = {}

    def fake_ground(raw_taskset, *, requirement, mbse_context):
        assert requirement == "verify controller feedback"
        assert mbse_context == _mbse_context()
        captured["raw"] = raw_taskset
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            generation_source=raw_taskset.generation_source,
            task_set_id="taskset_heuristic",
            score=0.66,
            p_value=0.73,
            conformal_info={"accepted": True},
            meta={
                **dict(raw_taskset.meta),
                "accepted": True,
                "selection_semantics": "calibrated_set",
            },
        )

    monkeypatch.setattr(heuristic_module, "_ground_and_score_candidate", fake_ground)

    result = heuristic_module.heuristic_neighborhood_stage1(
        "verify controller feedback",
        mbse_context=_mbse_context(),
        config=_workspace_config("ablation_stage1_heuristic_neighborhood"),
    )

    raw = captured["raw"]
    assert raw.generation_source == "heuristic_neighborhood_raw"
    assert raw.meta["generation_family"] == "heuristic"
    assert raw.meta["seed_components"]
    assert "Controller" in raw.meta["expanded_components"]
    assert any(task.diagnostics["anchor_score"] >= 0.0 for task in raw.tasks)
    assert result[0].p_value == 0.0
    assert result[0].conformal_info == {}
    assert result[0].meta["generation_family"] == "heuristic"
    assert result[0].meta["selection_mode"] == "single_heuristic_neighborhood"


def test_heuristic_neighborhood_stage1_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        heuristic_module.heuristic_neighborhood_stage1(
            "verify controller feedback",
            mbse_context=_mbse_context(),
            config={
                "method_name": "ablation_stage1_heuristic_neighborhood",
                "workspace_root": str(common.method_workspace("baseline_b3_graph_aware").resolve()),
            },
        )


def test_ablation_bundle_uses_heuristic_stage1(monkeypatch: pytest.MonkeyPatch) -> None:
    import baseline.bundles.ablation_stage1_heuristic_neighborhood as bundle_module

    captured: dict[str, object] = {}

    def fake_build_bundle(**kwargs):
        captured.update(kwargs)
        return "bundle-sentinel"

    def fake_register_bundle(bundle):
        captured["registered"] = bundle

    monkeypatch.setattr(common, "build_bundle", fake_build_bundle)
    monkeypatch.setattr(registry, "register_bundle", fake_register_bundle)

    importlib.reload(bundle_module)

    assert captured["name"] == "ablation_stage1_heuristic_neighborhood"
    assert captured["stage1"] is heuristic_module.heuristic_neighborhood_stage1
    assert captured["stage2"] is common.current_stage2
    assert captured["stage3"] is common.current_stage3
    assert captured["stage2_config"] == {
        "enable_benchmark_single_fmu_fallback": False,
        "enable_mbse_component_cover_fallback": False,
    }
    assert captured["registered"] == "bundle-sentinel"


def test_heuristic_neighborhood_stage1_fallback_is_local_and_single_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, TaskSet] = {}

    empty_context = MBSEContext(package_name="pkg", system_name="sys")

    monkeypatch.setattr(heuristic_module, "_seed_component_names", lambda *args, **kwargs: ([], {}))

    def fail_decompose_ablation(*args, **kwargs):
        raise AssertionError("heuristic_neighborhood_stage1 fallback should not call decompose_ablation")

    def fake_ground(raw_taskset, *, requirement, mbse_context):
        assert requirement == "verify orphan signal"
        assert mbse_context == empty_context
        captured["raw"] = raw_taskset
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            generation_source=raw_taskset.generation_source,
            task_set_id="taskset_heuristic_fallback",
            score=0.27,
            p_value=0.49,
            conformal_info={"accepted": True},
            meta={
                **dict(raw_taskset.meta),
                "accepted": True,
                "selection_semantics": "calibrated_set",
            },
        )

    monkeypatch.setattr(heuristic_module, "decompose_ablation", fail_decompose_ablation, raising=False)
    monkeypatch.setattr(heuristic_module, "_ground_and_score_candidate", fake_ground)

    result = heuristic_module.heuristic_neighborhood_stage1(
        "verify orphan signal",
        mbse_context=empty_context,
        config=_workspace_config("ablation_stage1_heuristic_neighborhood"),
    )

    raw = captured["raw"]
    assert raw.generation_source == "heuristic_neighborhood_fallback"
    assert len(raw.tasks) == 1
    assert raw.tasks[0].diagnostics["heuristic_neighborhood_fallback"] is True
    assert result[0].task_set_id == "taskset_heuristic_fallback"
    assert result[0].p_value == 0.0
    assert result[0].conformal_info == {}
