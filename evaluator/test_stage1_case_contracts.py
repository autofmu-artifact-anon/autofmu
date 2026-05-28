from __future__ import annotations

from evaluator.stage1_case_contracts import apply_case_structure_hints
from pipeline.types import TaskSet, VerificationTask


def test_apply_case_structure_hints_injects_required_chain() -> None:
    tasksets = [
        TaskSet(
            tasks=[VerificationTask(task_id="observe-msd2", objective="Observe x2", grounded_components=["msd2"])],
            meta={},
        )
    ]
    case_payload = {
        "requirement": {
            "structure_hints": {
                "required_signal_chains": [
                    {
                        "source_component": "msd1",
                        "source_signal": "x1",
                        "target_component": "msd2",
                        "target_signal": "x1",
                        "rationale": "Keep the two-mass coupling intact.",
                    }
                ]
            }
        }
    }

    updated = apply_case_structure_hints(tasksets, case_payload=case_payload)

    repaired_taskset = updated[0]
    assert repaired_taskset.meta["case_structure_hints_applied"] is True
    assert repaired_taskset.meta["case_structure_hint_chain_count"] == 1
    assert repaired_taskset.meta["case_structure_hint_task_count"] == 1
    assert len(repaired_taskset.required_signal_chains) == 1
    assert repaired_taskset.required_signal_chains[0].source_component == "msd1"
    assert repaired_taskset.required_signal_chains[0].target_component == "msd2"
    assert repaired_taskset.required_signal_chains[0].origin_task_ids == ["case_structure_hint_task_0"]
    assert any(task.task_id == "case_structure_hint_task_0" for task in repaired_taskset.tasks)


def test_apply_case_structure_hints_is_noop_without_hints() -> None:
    tasksets = [TaskSet(tasks=[VerificationTask(task_id="plain", objective="Observe output")], meta={})]

    updated = apply_case_structure_hints(tasksets, case_payload={"requirement": {}})

    assert updated == tasksets
