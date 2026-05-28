"""Stage 1 ablation: single, minimal task-set extraction."""

from __future__ import annotations

from typing import List

from pipeline.types import MBSEContext, TaskSet, VerificationTask


def decompose(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    confidence: float = 0.9,
    max_candidates: int = 1,
) -> List[TaskSet]:
    del confidence, max_candidates
    signals = []
    components = []
    component_types = []
    for component in mbse_context.components:
        components.append(component.name)
        component_types.append(component.component_type)
        for port in component.ports:
            if port.direction == "out":
                signals.append(port.name)
    task = VerificationTask(
        task_id="ablation_task_0",
        objective=(requirement or "").strip() or "verify system behavior",
        required_signals=signals[:12],
        grounded_components=components,
        grounded_component_types=component_types,
        diagnostics={"ablation": True},
    )
    return [
        TaskSet(
            tasks=[task],
            rationale="ablation: single minimal task set",
            score=0.1,
            p_value=0.0,
            meta={"ablation": True},
        )
    ]
