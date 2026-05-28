"""Tests for current stage wrappers and bundle construction helpers."""

from pathlib import Path

import pytest

from baseline.common import build_bundle, current_stage1, current_stage2, current_stage3
from baseline.common import bundle_factory, current_stages


def test_current_stage1_matches_evaluator_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """current_stage1 should forward evaluator.current_pipeline defaults."""
    captured: dict[str, object] = {}

    def fake_decompose(requirement, *, mbse_context, confidence, max_candidates):
        captured["requirement"] = requirement
        captured["mbse_context"] = mbse_context
        captured["confidence"] = confidence
        captured["max_candidates"] = max_candidates
        return ["taskset"]

    monkeypatch.setattr(current_stages, "decompose", fake_decompose)
    mbse_context = object()

    result = current_stage1("verify pressure", mbse_context=mbse_context, config={})

    assert result == ["taskset"]
    assert captured == {
        "requirement": "verify pressure",
        "mbse_context": mbse_context,
        "confidence": 0.9,
        "max_candidates": 6,
    }


def test_current_stage2_normalizes_sequences_and_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """current_stage2 should copy sequences and coerce evaluator config values."""
    captured: dict[str, object] = {}

    def fake_match(
        task_candidates,
        *,
        mbse_context,
        fmu_library,
        max_revisions,
        top_m_per_task,
        max_port_candidates,
        enable_benchmark_single_fmu_fallback,
        enable_mbse_component_cover_fallback,
    ):
        captured["task_candidates"] = task_candidates
        captured["mbse_context"] = mbse_context
        captured["fmu_library"] = fmu_library
        captured["max_revisions"] = max_revisions
        captured["top_m_per_task"] = top_m_per_task
        captured["max_port_candidates"] = max_port_candidates
        captured["enable_benchmark_single_fmu_fallback"] = enable_benchmark_single_fmu_fallback
        captured["enable_mbse_component_cover_fallback"] = enable_mbse_component_cover_fallback
        return "matching-result"

    monkeypatch.setattr(current_stages, "match", fake_match)
    task_candidates = ("task-a", "task-b")
    fmu_library = ("fmu-1", "fmu-2")
    mbse_context = object()

    result = current_stage2(
        task_candidates,
        mbse_context=mbse_context,
        fmu_library=fmu_library,
        config={
            "max_revisions": "2",
            "top_m_per_task": 7,
            "max_port_candidates": "9",
            "enable_benchmark_single_fmu_fallback": False,
            "enable_mbse_component_cover_fallback": "no",
        },
    )

    assert result == "matching-result"
    assert captured == {
        "task_candidates": ["task-a", "task-b"],
        "mbse_context": mbse_context,
        "fmu_library": ["fmu-1", "fmu-2"],
        "max_revisions": 2,
        "top_m_per_task": 7,
        "max_port_candidates": 9,
        "enable_benchmark_single_fmu_fallback": False,
        "enable_mbse_component_cover_fallback": False,
    }


def test_current_stage3_matches_evaluator_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    """current_stage3 should mirror the evaluator's current-pipeline wrapper."""
    captured: dict[str, object] = {}

    def fake_compose(matching_result, *, mbse_context, scenario_window=None):
        captured["matching_result"] = matching_result
        captured["mbse_context"] = mbse_context
        captured["scenario_window"] = scenario_window
        return "composition-result"

    monkeypatch.setattr(current_stages, "compose", fake_compose)
    matching_result = object()
    mbse_context = object()

    result = current_stage3(
        matching_result,
        mbse_context=mbse_context,
        config={"scenario_window": {"step_size": 0.5}, "ignored": True},
    )

    assert result == "composition-result"
    assert captured == {
        "matching_result": matching_result,
        "mbse_context": mbse_context,
        "scenario_window": {"step_size": 0.5},
    }


def test_build_bundle_injects_workspace_context_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_bundle should normalize configs and inject fixed method workspace context."""
    method_name = "baseline_b1_rule_sequential"
    workspace_root = tmp_path / method_name
    captured: dict[str, dict[str, object]] = {}
    metadata = {"source": "tests", "method_name": "user-value"}
    stage1_defaults = {"alpha": 1, "method_name": "bad-default"}
    stage3_defaults = {"gamma": 3}

    def fake_bootstrap(name: str) -> Path:
        assert name == method_name
        return workspace_root

    def stage1(requirement, *, mbse_context, config):
        captured["stage1"] = {
            "requirement": requirement,
            "mbse_context": mbse_context,
            "config": dict(config),
        }
        return "stage1-result"

    def stage2(task_candidates, *, mbse_context, fmu_library, config):
        captured["stage2"] = {
            "task_candidates": task_candidates,
            "mbse_context": mbse_context,
            "fmu_library": fmu_library,
            "config": dict(config),
        }
        return "stage2-result"

    def stage3(matching_result, *, mbse_context, config):
        captured["stage3"] = {
            "matching_result": matching_result,
            "mbse_context": mbse_context,
            "config": dict(config),
        }
        return "stage3-result"

    monkeypatch.setattr(bundle_factory, "bootstrap_method_workspace", fake_bootstrap)

    bundle = build_bundle(
        name=method_name,
        description="Test bundle",
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage1_config=stage1_defaults,
        stage3_config=stage3_defaults,
        metadata=metadata,
    )

    assert bundle.name == method_name
    assert bundle.description == "Test bundle"
    assert bundle.metadata == {
        "source": "tests",
        "method_name": method_name,
        "workspace_root": str(workspace_root.resolve()),
    }
    assert metadata == {"source": "tests", "method_name": "user-value"}
    assert stage1_defaults == {"alpha": 1, "method_name": "bad-default"}
    assert stage3_defaults == {"gamma": 3}

    mbse_context = object()
    runtime_workspace = "/tmp/override-attempt"
    assert bundle.stage1(
        "req",
        mbse_context=mbse_context,
        config={"alpha": 9, "beta": 2, "workspace_root": runtime_workspace},
    ) == "stage1-result"
    assert bundle.stage2(
        ["taskset"],
        mbse_context=mbse_context,
        fmu_library=["fmu"],
        config={"delta": 4, "method_name": "override-attempt"},
    ) == "stage2-result"
    assert bundle.stage3(
        "matching",
        mbse_context=mbse_context,
        config={"gamma": 8},
    ) == "stage3-result"

    assert captured["stage1"]["config"] == {
        "alpha": 9,
        "beta": 2,
        "method_name": method_name,
        "workspace_root": str(workspace_root.resolve()),
    }
    assert captured["stage2"]["config"] == {
        "delta": 4,
        "method_name": method_name,
        "workspace_root": str(workspace_root.resolve()),
    }
    assert captured["stage3"]["config"] == {
        "gamma": 8,
        "method_name": method_name,
        "workspace_root": str(workspace_root.resolve()),
    }
