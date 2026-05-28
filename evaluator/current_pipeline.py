from __future__ import annotations

from typing import Any, Mapping

from .current_pipeline_stage1 import run_current_stage1
from .current_pipeline_stage2 import run_current_stage2
from .current_pipeline_stage3 import run_current_stage3
from .registry import register_bundle
from .types import MethodBundle


def _stage1_current(requirement: str, *, mbse_context, config: Mapping[str, Any]):
    return run_current_stage1(
        requirement,
        mbse_context=mbse_context,
        config=config,
    )


def _stage2_current(task_candidates, *, mbse_context, fmu_library, config: Mapping[str, Any]):
    return run_current_stage2(
        task_candidates,
        mbse_context=mbse_context,
        fmu_library=fmu_library,
        config=config,
    )


def _stage3_current(matching_result, *, mbse_context, config: Mapping[str, Any]):
    return run_current_stage3(
        matching_result,
        mbse_context=mbse_context,
        config=config,
    )


register_bundle(
    MethodBundle(
        name="current_pipeline",
        description="Wraps the current pipeline stage implementations without modifying pipeline/.",
        stage1=_stage1_current,
        stage2=_stage2_current,
        stage3=_stage3_current,
        metadata={"source": "pipeline"},
    )
)
