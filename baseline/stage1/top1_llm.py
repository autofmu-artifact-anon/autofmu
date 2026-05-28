"""Minimal top-1 LLM Stage-1 wrapper for baseline evaluator bundles.

Ablation: Top-1 LLM decomposition — output a single candidate task set,
no conformal calibration.  Uses the ``openai`` library directly instead of
any ``pipeline.*`` algorithmic module.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request

from pipeline.types import (
    AcceptanceCriterion,
    MBSEComponent,
    MBSEContext,
    OperatingRegime,
    TaskSet,
    VerificationTask,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace

logger = logging.getLogger(__name__)

_ALLOWED_METHOD_NAMES = frozenset(
    {
        "ablation_stage1_top1_llm",
        "baseline_b2_llm_retrieval_rule",
    }
)

_CALIBRATION_META_KEYS = frozenset(
    {
        "accepted",
        "accepted_by",
        "calibrated_member",
        "calibration_artifact_path",
        "calibration_artifact_version",
        "calibration_confidence_levels",
        "calibration_score_summary",
        "calibration_size",
        "candidate_status",
        "confidence",
        "engineering_fallback",
        "fallback_retained",
        "forced_fallback",
        "nonconformity",
        "p_value_threshold",
        "selection_semantics",
    }
)

# ---------------------------------------------------------------------------
# LLM configuration from environment
# ---------------------------------------------------------------------------


def _llm_config() -> dict[str, Any]:
    return {
        "api_key": os.environ.get("PIPELINE_LLM_API_KEY", ""),
        "base_url": os.environ.get("PIPELINE_LLM_BASE_URL") or None,
        "model": os.environ.get("PIPELINE_LLM_MODEL", "gpt-4o"),
        "timeout": float(os.environ.get("PIPELINE_LLM_TIMEOUT_SECONDS", "120")),
    }


# ---------------------------------------------------------------------------
# Local re-implementations of helpers formerly from pipeline internals
# ---------------------------------------------------------------------------

_CRITERION_RE = re.compile(
    r"([\w\s/]+?)\s*(<=?|>=?|==?|!=|≤|≥|<|>)\s*"
    r"([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*(\w*)"
)
_TIME_RE = re.compile(
    r"(?:from|between|during|over|at|after)\s+t\s*=?\s*"
    r"([+-]?[\d.]+)\s*(?:s|sec|seconds?)?"
    r"(?:\s*(?:to|and|\.\.\.?|-)\s*([+-]?[\d.]+)\s*(?:s|sec|seconds?)?)?",
    re.IGNORECASE,
)
_WITHIN_RE = re.compile(
    r"within\s*\[?\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)\s*\]?",
    re.IGNORECASE,
)


def _component_is_mentioned(name: str, component_type: str, requirement: str) -> bool:
    lowered = requirement.lower()
    if name.lower() in lowered:
        return True
    if component_type and component_type.lower() in lowered:
        return True
    name_tokens = set(re.findall(r"[a-z][a-z0-9]*", name.lower()))
    if len(name_tokens) >= 2 and name_tokens <= set(re.findall(r"[a-z][a-z0-9]*", lowered)):
        return True
    return False


def _extract_acceptance_criteria(requirement: str) -> list[AcceptanceCriterion]:
    criteria: list[AcceptanceCriterion] = []
    for match in _CRITERION_RE.finditer(requirement):
        metric, operator, value_str, unit = match.groups()
        try:
            value: Any = float(value_str)
        except ValueError:
            value = value_str
        criteria.append(
            AcceptanceCriterion(
                metric=metric.strip(),
                operator=operator.strip(),
                value=value,
                unit=unit.strip(),
            )
        )
    for match in _WITHIN_RE.finditer(requirement):
        lo, hi = match.groups()
        criteria.append(
            AcceptanceCriterion(
                metric="range_constraint",
                operator="within",
                value=[float(lo), float(hi)],
            )
        )
    return criteria


def _extract_operating_regime(requirement: str) -> OperatingRegime | None:
    match = _TIME_RE.search(requirement)
    if match:
        start = float(match.group(1))
        end = float(match.group(2)) if match.group(2) else None
        return OperatingRegime(start_time=start, end_time=end)
    return None


def _global_objective(requirement: str) -> str:
    text = requirement.strip()
    return text[:197] + "..." if len(text) > 200 else text


def _generation_family(source: str) -> str:
    source_lower = (source or "").lower()
    if "llm" in source_lower:
        return "llm"
    if "rule" in source_lower:
        return "rules"
    if "heuristic" in source_lower:
        return "heuristic"
    return "unknown"


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a verification engineer. Given a verification requirement and a list of \
MBSE system components, decompose the requirement into a set of simulation sub-tasks.

Return a JSON array of task objects. Each task object MUST have:
  "task_id": string (e.g. "task_0"),
  "objective": string (what to verify),
  "required_signals": [list of signal/port names],
  "grounded_components": [list of component names from the MBSE model],
  "grounded_component_types": [list of component types],
  "grounded_ports": [list of port names],
  "acceptance_criteria": [{"metric": str, "operator": str, "value": number, "unit": str}],
  "operating_regime": {"start_time": number or null, "end_time": number or null, \
"description": str} or null

Return ONLY the JSON array, no markdown fencing or extra text.\
"""


def _build_user_prompt(requirement: str, mbse_context: MBSEContext) -> str:
    components_desc = "\n".join(
        f"- {c.name} (type={c.component_type}, "
        f"ports=[{', '.join(p.name for p in c.ports)}])"
        for c in mbse_context.components
    )
    return (
        f"Requirement:\n{requirement}\n\n"
        f"MBSE System: {mbse_context.system_name}\n"
        f"Components:\n{components_desc}\n\n"
        "Decompose this into verification sub-tasks."
    )


def _chat_completions_url(base_url: str) -> str:
    normalized = (base_url or "https://api.openai.com").strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return normalized + "/chat/completions"
    return normalized + "/v1/chat/completions"


def _extract_text(payload: dict) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str):
            return content
    return ""


def _call_llm(requirement: str, mbse_context: MBSEContext) -> list[dict[str, Any]]:
    cfg = _llm_config()
    api_key = cfg["api_key"]
    if not api_key:
        return []
    body = json.dumps({
        "model": cfg["model"],
        "temperature": 0.3,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(requirement, mbse_context)},
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        url=_chat_completions_url(cfg.get("base_url") or ""),
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(cfg["timeout"])) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = _extract_text(payload).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("LLM call failed, falling back: %s", exc)
        return []


def _parse_llm_tasks(
    raw_tasks: list[dict[str, Any]],
    requirement: str,
    mbse_context: MBSEContext,
) -> list[VerificationTask]:
    valid_components = {c.name for c in mbse_context.components}
    component_type_map = {c.name: c.component_type for c in mbse_context.components}
    tasks: list[VerificationTask] = []
    for idx, raw in enumerate(raw_tasks):
        if not isinstance(raw, dict):
            continue
        grounded = [n for n in raw.get("grounded_components", []) if n in valid_components]
        ac_raw = raw.get("acceptance_criteria") or []
        criteria = [
            AcceptanceCriterion(
                metric=str(c.get("metric", "")),
                operator=str(c.get("operator", "")),
                value=c.get("value", 0),
                unit=str(c.get("unit", "")),
            )
            for c in ac_raw
            if isinstance(c, dict)
        ]
        regime_raw = raw.get("operating_regime")
        regime = None
        if isinstance(regime_raw, dict):
            regime = OperatingRegime(
                start_time=regime_raw.get("start_time"),
                end_time=regime_raw.get("end_time"),
                description=str(regime_raw.get("description", "")),
            )
        tasks.append(
            VerificationTask(
                task_id=raw.get("task_id", f"task_llm_{idx}"),
                objective=str(raw.get("objective", _global_objective(requirement))),
                required_signals=list(raw.get("required_signals", [])),
                acceptance_criteria=criteria,
                operating_regime=regime,
                grounded_components=grounded,
                grounded_component_types=[component_type_map.get(n, "") for n in grounded],
                grounded_ports=list(raw.get("grounded_ports", [])),
                diagnostics={
                    "generation_source": "llm_raw",
                    "generation_family": "llm",
                },
            )
        )
    return tasks


# ---------------------------------------------------------------------------
# Local grounding & scoring (replaces pipeline.stage1_decomposition.grounding
# and pipeline.stage1_decomposition.calibration)
# ---------------------------------------------------------------------------


def _ground_and_score(
    raw_taskset: TaskSet,
    requirement: str,
    mbse_context: MBSEContext,
) -> TaskSet:
    valid_components = {c.name for c in mbse_context.components}
    component_type_map = {c.name: c.component_type for c in mbse_context.components}
    port_set = {p.name for c in mbse_context.components for p in c.ports}

    grounded_tasks: list[VerificationTask] = []
    total_component_hits = 0
    total_port_hits = 0
    total_components = 0
    total_ports = 0

    for task in raw_taskset.tasks:
        gc = [n for n in task.grounded_components if n in valid_components]
        gct = [component_type_map.get(n, "") for n in gc]
        gp = [p for p in task.grounded_ports if p in port_set]
        total_component_hits += len(gc)
        total_port_hits += len(gp)
        total_components += max(len(task.grounded_components), 1)
        total_ports += max(len(task.grounded_ports), 1)
        grounded_tasks.append(
            replace(
                task,
                grounded_components=gc,
                grounded_component_types=gct,
                grounded_ports=gp,
            )
        )

    comp_ratio = total_component_hits / total_components if total_components else 0.0
    port_ratio = total_port_hits / total_ports if total_ports else 0.0
    has_criteria = any(t.acceptance_criteria for t in grounded_tasks)
    criteria_bonus = 0.15 if has_criteria else 0.0
    score = round(0.5 * comp_ratio + 0.35 * port_ratio + criteria_bonus, 4)
    grounding_valid = comp_ratio > 0.0

    source = raw_taskset.generation_source or "llm_raw"
    status = "grounded" if grounding_valid else "partially_grounded"

    return replace(
        raw_taskset,
        tasks=grounded_tasks,
        task_set_id="taskset_0",
        generation_source=source,
        grounding_status=status,
        score=score,
        score_breakdown={
            "component_ratio": comp_ratio,
            "port_ratio": port_ratio,
            "criteria_bonus": criteria_bonus,
            "final_score": score,
        },
        meta={
            **dict(raw_taskset.meta),
            "generation_family": _generation_family(source),
            "grounding_valid": grounding_valid,
        },
    )


# ---------------------------------------------------------------------------
# Config / workspace helpers
# ---------------------------------------------------------------------------


def _config_dict(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize the optional evaluator config mapping."""
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise TypeError(f"config must be a mapping or None, got {type(config).__name__}")
    return dict(config)


def _validate_workspace_context(stage_config: Mapping[str, Any]) -> tuple[str, Path]:
    """Validate that the injected workspace root matches an allowed method workspace."""
    method_name = str(stage_config.get("method_name") or "").strip()
    if method_name not in _ALLOWED_METHOD_NAMES:
        raise ValueError(
            f"top1_llm_stage1 only supports {', '.join(sorted(_ALLOWED_METHOD_NAMES))}; "
            f"got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("top1_llm_stage1 requires config['workspace_root']")

    try:
        candidate = Path(workspace_value)
    except TypeError as exc:
        raise TypeError(
            f"config['workspace_root'] must be path-like, got {type(workspace_value).__name__}"
        ) from exc

    expected = method_workspace(method_name).resolve()
    try:
        resolved = validate_path_in_workspace(method_name, candidate)
    except WorkspaceError as exc:
        raise WorkspaceError(
            f"workspace_root for {method_name!r} must stay within {expected}, got {candidate}"
        ) from exc
    if resolved != expected:
        raise WorkspaceError(
            f"workspace_root for {method_name!r} must resolve to {expected}, got {resolved}"
        )
    return method_name, expected


def _strip_calibration_extras(taskset: TaskSet) -> TaskSet:
    """Drop conformal-set metadata while keeping the TaskSet schema stable."""
    meta = {
        key: value
        for key, value in dict(taskset.meta).items()
        if key not in _CALIBRATION_META_KEYS
    }
    return replace(
        taskset,
        p_value=0.0,
        conformal_info={},
        meta=meta,
    )


# ---------------------------------------------------------------------------
# Fallback (when LLM call fails or returns nothing)
# ---------------------------------------------------------------------------


def _fallback_component(requirement: str, *, mbse_context: MBSEContext) -> MBSEComponent | None:
    mentioned = [
        c
        for c in mbse_context.components
        if _component_is_mentioned(c.name, c.component_type, requirement)
    ]
    if mentioned:
        return mentioned[0]
    return mbse_context.components[0] if mbse_context.components else None


def _fallback_required_signals(requirement: str, component: MBSEComponent | None) -> list[str]:
    if component is None:
        return []
    lowered = (requirement or "").lower()
    mentioned = [p.name for p in component.ports if p.name and p.name.lower() in lowered]
    if mentioned:
        return mentioned
    if component.ports:
        return [component.ports[0].name]
    return []


def _build_fallback_raw_taskset(requirement: str, *, mbse_context: MBSEContext) -> TaskSet:
    component = _fallback_component(requirement, mbse_context=mbse_context)
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)
    required_signals = _fallback_required_signals(requirement, component)
    tasks = [
        VerificationTask(
            task_id="task_llm_fallback_0",
            objective=_global_objective(requirement),
            required_signals=list(required_signals),
            acceptance_criteria=list(criteria),
            operating_regime=regime,
            grounded_components=[component.name] if component is not None else [],
            grounded_component_types=[component.component_type] if component is not None else [],
            grounded_ports=list(required_signals),
            diagnostics={
                "generation_source": "llm_fallback_raw",
                "generation_family": "llm",
                "llm_fallback": True,
            },
        )
    ]
    return TaskSet(
        tasks=tasks,
        rationale="top1_llm fallback raw task set",
        task_set_id="",
        generation_source="llm_fallback_raw",
        grounding_status="raw",
        score=0.0,
        p_value=0.0,
        conformal_info={},
        score_breakdown={},
        meta={
            "generation_source": "llm_fallback_raw",
            "generation_family": "llm",
            "llm_fallback": True,
            "fallback_component": component.name if component is not None else "",
        },
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def top1_llm_stage1(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> list[TaskSet]:
    """Produce exactly one evaluator-compatible Stage-1 candidate."""
    stage_config = _config_dict(config)
    _validate_workspace_context(stage_config)

    req = (requirement or "").strip()

    raw_tasks = _call_llm(req, mbse_context)
    parsed = _parse_llm_tasks(raw_tasks, req, mbse_context) if raw_tasks else []

    if parsed:
        raw_taskset = TaskSet(
            tasks=parsed,
            rationale="top1_llm single candidate from LLM",
            task_set_id="",
            generation_source="llm_raw",
            grounding_status="raw",
            meta={"generation_source": "llm_raw", "generation_family": "llm"},
        )
    else:
        raw_taskset = _build_fallback_raw_taskset(req, mbse_context=mbse_context)

    candidate = _ground_and_score(raw_taskset, req, mbse_context)
    return [_strip_calibration_extras(candidate)]


__all__ = ["top1_llm_stage1"]
