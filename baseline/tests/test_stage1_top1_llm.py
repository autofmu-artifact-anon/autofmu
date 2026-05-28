"""Focused tests for the baseline top-1 LLM Stage-1 module."""

from __future__ import annotations

import importlib

import pytest

import baseline.common as common
import baseline.stage1.top1_llm as top1_module
import evaluator.registry as registry
from pipeline.types import MBSEComponent, MBSEContext, MBSEPort, TaskSet, VerificationTask


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
            MBSEComponent(
                name="Controller",
                component_type="Controller",
                ports=[
                    MBSEPort(component="Controller", name="feedback", direction="in"),
                    MBSEPort(component="Controller", name="command", direction="out"),
                ],
            )
        ],
    )


def test_top1_llm_stage1_forces_single_candidate_and_strips_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_first = TaskSet(
        tasks=[VerificationTask(task_id="task_raw_0", objective="first raw candidate")],
        rationale="raw-first",
    )
    raw_second = TaskSet(
        tasks=[VerificationTask(task_id="task_raw_1", objective="second raw candidate")],
        rationale="raw-second",
    )
    captured: dict[str, object] = {}

    def fake_llm(requirement, *, mbse_context, max_candidates):
        captured["requirement"] = requirement
        captured["mbse_context"] = mbse_context
        captured["max_candidates"] = max_candidates
        return [raw_first, raw_second]

    def fake_ground_and_score(raw_taskset, *, requirement, mbse_context):
        captured["raw_taskset"] = raw_taskset
        captured["ground_requirement"] = requirement
        captured["ground_mbse_context"] = mbse_context
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            task_set_id="taskset_calibrated",
            score=0.72,
            p_value=0.84,
            conformal_info={"accepted": True, "selection_semantics": "calibrated_set"},
            meta={
                "accepted": True,
                "calibration_size": 8,
                "keep": "yes",
                "selection_semantics": "calibrated_set",
            },
        )

    monkeypatch.setattr(top1_module, "_generate_raw_tasksets_via_llm", fake_llm)
    monkeypatch.setattr(top1_module, "_ground_and_score_candidate", fake_ground_and_score)
    mbse_context = object()

    result = top1_module.top1_llm_stage1(
        "verify coolant temperature",
        mbse_context=mbse_context,
        config=_workspace_config("ablation_stage1_top1_llm"),
    )

    assert captured == {
        "requirement": "verify coolant temperature",
        "mbse_context": mbse_context,
        "max_candidates": 1,
        "raw_taskset": raw_first,
        "ground_requirement": "verify coolant temperature",
        "ground_mbse_context": mbse_context,
    }
    assert result == [
        TaskSet(
            tasks=list(raw_first.tasks),
            rationale="raw-first",
            task_set_id="taskset_calibrated",
            score=0.72,
            p_value=0.0,
            conformal_info={},
            meta={"keep": "yes"},
        )
    ]


def test_top1_llm_stage1_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        top1_module.top1_llm_stage1(
            "verify coolant temperature",
            mbse_context=object(),
            config={
                "method_name": "ablation_stage1_top1_llm",
                "workspace_root": str(common.method_workspace("baseline_b2_llm_retrieval_rule").resolve()),
            },
        )


def test_ablation_bundle_uses_top1_stage1(monkeypatch: pytest.MonkeyPatch) -> None:
    import baseline.bundles.ablation_stage1_top1_llm as bundle_module

    captured: dict[str, object] = {}

    def fake_build_bundle(**kwargs):
        captured.update(kwargs)
        return "bundle-sentinel"

    def fake_register_bundle(bundle):
        captured["registered"] = bundle

    monkeypatch.setattr(common, "build_bundle", fake_build_bundle)
    monkeypatch.setattr(registry, "register_bundle", fake_register_bundle)

    importlib.reload(bundle_module)

    assert captured["name"] == "ablation_stage1_top1_llm"
    assert captured["stage1"] is top1_module.top1_llm_stage1
    assert captured["stage2"] is common.current_stage2
    assert captured["stage3"] is common.current_stage3
    assert captured["stage2_config"] == {
        "enable_benchmark_single_fmu_fallback": False,
        "enable_mbse_component_cover_fallback": False,
    }
    assert captured["registered"] == "bundle-sentinel"


def test_top1_llm_stage1_fallback_is_local_and_single_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, TaskSet] = {}

    monkeypatch.setattr(top1_module, "_generate_raw_tasksets_via_llm", lambda *args, **kwargs: [])

    def fail_decompose_ablation(*args, **kwargs):
        raise AssertionError("top1_llm_stage1 fallback should not call decompose_ablation")

    def fake_ground_and_score(raw_taskset, *, requirement, mbse_context):
        assert requirement == "verify controller feedback"
        assert mbse_context == _mbse_context()
        captured["raw"] = raw_taskset
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            generation_source=raw_taskset.generation_source,
            task_set_id="taskset_local_fallback",
            score=0.41,
            p_value=0.61,
            conformal_info={"accepted": True},
            meta={
                **dict(raw_taskset.meta),
                "accepted": True,
                "selection_semantics": "calibrated_set",
            },
        )

    monkeypatch.setattr(top1_module, "decompose_ablation", fail_decompose_ablation, raising=False)
    monkeypatch.setattr(top1_module, "_ground_and_score_candidate", fake_ground_and_score)

    result = top1_module.top1_llm_stage1(
        "verify controller feedback",
        mbse_context=_mbse_context(),
        config=_workspace_config("ablation_stage1_top1_llm"),
    )

    raw = captured["raw"]
    assert raw.generation_source == "llm_fallback_raw"
    assert len(raw.tasks) == 1
    assert raw.tasks[0].grounded_components == ["Controller"]
    assert raw.tasks[0].diagnostics["llm_fallback"] is True
    assert result[0].task_set_id == "taskset_local_fallback"
    assert result[0].p_value == 0.0
    assert result[0].conformal_info == {}
