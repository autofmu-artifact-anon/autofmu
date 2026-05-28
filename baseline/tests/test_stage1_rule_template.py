"""Focused tests for the baseline rule-template Stage-1 module."""

from __future__ import annotations

import importlib

import pytest

import baseline.common as common
import baseline.stage1.rule_template as rule_module
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
                name="Pump",
                component_type="Pump",
                ports=[MBSEPort(component="Pump", name="pressure", direction="out")],
            ),
            MBSEComponent(
                name="Valve",
                component_type="Valve",
                ports=[MBSEPort(component="Valve", name="command", direction="in")],
            ),
        ],
    )


def test_rule_template_stage1_selects_single_best_rule_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_component = TaskSet(
        tasks=[VerificationTask(task_id="component", objective="component candidate")],
        rationale="component-first",
        generation_source="rules_component",
    )
    raw_connection = TaskSet(
        tasks=[VerificationTask(task_id="connection", objective="connection candidate")],
        rationale="connection-second",
        generation_source="rules_connection",
    )
    raw_monolithic = TaskSet(
        tasks=[VerificationTask(task_id="monolithic", objective="monolithic candidate")],
        rationale="monolithic-third",
        generation_source="rules_monolithic",
    )
    captured: list[TaskSet] = []

    def fake_generate(requirement, mbse_context):
        assert requirement == "verify coolant pressure"
        assert mbse_context is not None
        return [raw_component, raw_connection, raw_monolithic]

    def fake_ground(raw_taskset, *, requirement, mbse_context):
        del requirement, mbse_context
        captured.append(raw_taskset)
        score_map = {
            "rules_component": 0.7,
            "rules_connection": 0.7,
            "rules_monolithic": 0.4,
        }
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            generation_source=raw_taskset.generation_source,
            task_set_id="taskset_candidate",
            score=score_map[raw_taskset.generation_source],
            p_value=0.82,
            conformal_info={"accepted": True},
            meta={
                "accepted": True,
                "selection_semantics": "calibrated_set",
                "keep": raw_taskset.generation_source,
            },
        )

    monkeypatch.setattr(rule_module, "_generate_raw_tasksets_via_rules", fake_generate)
    monkeypatch.setattr(rule_module, "_ground_and_score_candidate", fake_ground)

    result = rule_module.rule_template_stage1(
        "verify coolant pressure",
        mbse_context=object(),
        config=_workspace_config("ablation_stage1_rule_template"),
    )

    assert captured == [raw_component, raw_connection, raw_monolithic]
    assert result == [
        TaskSet(
            tasks=list(raw_component.tasks),
            rationale="component-first",
            generation_source="rules_component",
            task_set_id="taskset_candidate",
            score=0.7,
            p_value=0.0,
            conformal_info={},
            meta={
                "keep": "rules_component",
                "generation_source": "rules_component",
                "generation_family": "rules",
                "selection_mode": "single_best_rule_template",
                "candidate_count": 3,
            },
        )
    ]


def test_rule_template_stage1_rejects_workspace_root_for_another_method() -> None:
    with pytest.raises(common.WorkspaceError, match="workspace_root"):
        rule_module.rule_template_stage1(
            "verify coolant pressure",
            mbse_context=object(),
            config={
                "method_name": "ablation_stage1_rule_template",
                "workspace_root": str(common.method_workspace("baseline_b1_rule_sequential").resolve()),
            },
        )


def test_ablation_bundle_uses_rule_template_stage1(monkeypatch: pytest.MonkeyPatch) -> None:
    import baseline.bundles.ablation_stage1_rule_template as bundle_module

    captured: dict[str, object] = {}

    def fake_build_bundle(**kwargs):
        captured.update(kwargs)
        return "bundle-sentinel"

    def fake_register_bundle(bundle):
        captured["registered"] = bundle

    monkeypatch.setattr(common, "build_bundle", fake_build_bundle)
    monkeypatch.setattr(registry, "register_bundle", fake_register_bundle)

    importlib.reload(bundle_module)

    assert captured["name"] == "ablation_stage1_rule_template"
    assert captured["stage1"] is rule_module.rule_template_stage1
    assert captured["stage2"] is common.current_stage2
    assert captured["stage3"] is common.current_stage3
    assert captured["stage2_config"] == {
        "enable_benchmark_single_fmu_fallback": False,
        "enable_mbse_component_cover_fallback": False,
    }
    assert captured["registered"] == "bundle-sentinel"


def test_rule_template_stage1_fallback_is_local_and_single_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, TaskSet] = {}

    monkeypatch.setattr(rule_module, "_generate_raw_tasksets_via_rules", lambda *args, **kwargs: [])

    def fail_decompose_ablation(*args, **kwargs):
        raise AssertionError("rule_template_stage1 fallback should not call decompose_ablation")

    def fake_ground(raw_taskset, *, requirement, mbse_context):
        assert requirement == "verify valve command"
        assert mbse_context == _mbse_context()
        captured["raw"] = raw_taskset
        return TaskSet(
            tasks=list(raw_taskset.tasks),
            rationale=raw_taskset.rationale,
            generation_source=raw_taskset.generation_source,
            task_set_id="taskset_rule_fallback",
            score=0.33,
            p_value=0.52,
            conformal_info={"accepted": True},
            meta={
                **dict(raw_taskset.meta),
                "accepted": True,
                "selection_semantics": "calibrated_set",
            },
        )

    monkeypatch.setattr(rule_module, "decompose_ablation", fail_decompose_ablation, raising=False)
    monkeypatch.setattr(rule_module, "_ground_and_score_candidate", fake_ground)

    result = rule_module.rule_template_stage1(
        "verify valve command",
        mbse_context=_mbse_context(),
        config=_workspace_config("ablation_stage1_rule_template"),
    )

    raw = captured["raw"]
    assert raw.generation_source == "rules_fallback"
    assert len(raw.tasks) == 1
    assert raw.tasks[0].diagnostics["rule_template_fallback"] is True
    assert result[0].task_set_id == "taskset_rule_fallback"
    assert result[0].p_value == 0.0
    assert result[0].conformal_info == {}
