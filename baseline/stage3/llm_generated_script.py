"""Stage-3 orchestration payload generator with deterministic fallback.

Ablation: LLM directly generates the payload using the openai library.
All logic is self-contained — only data-structure imports from pipeline.types.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

from pipeline.types import (
    CompositionResult,
    MatchingResult,
    MBSEContext,
    OrchestrationGraph,
    PortBinding,
    SimulationConfig,
)

from ..common.paths import method_workspace
from ..common.workspace import WorkspaceError, validate_path_in_workspace


_ALLOWED_METHOD_NAMES = frozenset({"ablation_stage3_llm_generated_script"})
_ALLOWED_SCHEDULE_KINDS = frozenset({"single_fmu", "co_simulation", "fixed_step"})

_SYSTEM_PROMPT = """\
You are a co-simulation orchestration payload generator.
Your task: produce a single valid JSON object defining how FMUs should be \
orchestrated together for co-simulation using only the provided FMU list, \
known ports, and scenario window.

Return EXACTLY ONE valid JSON object. No markdown, no code fences, no prose.

Required top-level keys:
- "selected_asset_ids": ordered list of FMU UIDs
- "connections": list of objects each with "source" and "target" \
(format: "<fmu_uid>.<signal_name>")
- "schedule": object with "kind", "start_time", "stop_time", "step_size", \
"execution_order"; for multi-FMU payloads also "per_node_period" mapping every \
selected asset to its step period
- "execution_order": ordered list of FMU UIDs defining execution sequence

Optional keys (MUST be empty arrays for this variant):
- "adapters": []
- "loop_resolution": []

Optional metadata:
- "extensions": {} (freeform dict)
- "notes": [] (string list)

"schedule.kind" must be one of: single_fmu, co_simulation, fixed_step.

Constraints:
- "selected_asset_ids" must match the provided asset list exactly and in the same order.
- Do NOT invent assets or ports outside the provided catalog.
- Do NOT use adapters or loop wrappers.
- Prefer sparse orchestration. If uncertain, return no connections and use a coarse fixed-step schedule.\
"""


# ---------------------------------------------------------------------------
# Config / workspace helpers
# ---------------------------------------------------------------------------

def _config_dict(config: Mapping[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise TypeError(f"config must be a mapping or None, got {type(config).__name__}")
    return dict(config)


def _validate_workspace_context(stage_config: Mapping[str, Any]) -> tuple[str, Path]:
    method_name = str(stage_config.get("method_name") or "").strip()
    if method_name not in _ALLOWED_METHOD_NAMES:
        raise ValueError(
            "llm_generated_script_stage3 only supports "
            f"{', '.join(sorted(_ALLOWED_METHOD_NAMES))}; got {method_name!r}"
        )

    workspace_value = stage_config.get("workspace_root")
    if workspace_value in (None, ""):
        raise ValueError("llm_generated_script_stage3 requires config['workspace_root']")

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


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def _json_clone(value: Any, *, fallback: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError):
        return fallback


def _positive_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0.0:
        return None
    return numeric


def _unique_strings(items: Any) -> list[str]:
    """Ordered dedup of non-empty stripped strings."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        s = str(item or "").strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _ordered_unique_ids(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _string_list(value: Any, *, max_items: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    return _unique_strings(str(item or "").strip() for item in value)[:max_items]


# ---------------------------------------------------------------------------
# FMU introspection
# ---------------------------------------------------------------------------

def _port_catalog(fmu: Any) -> dict[str, list[str]]:
    inputs = _unique_strings(
        list(getattr(fmu, "inputs", []) or [])
        + [
            getattr(port, "name", "")
            for port in getattr(fmu, "ports", [])
            if str(getattr(port, "causality", "")).strip().lower() == "input"
        ]
    )
    outputs = _unique_strings(
        list(getattr(fmu, "outputs", []) or [])
        + [
            getattr(port, "name", "")
            for port in getattr(fmu, "ports", [])
            if str(getattr(port, "causality", "")).strip().lower() == "output"
        ]
    )
    return {"inputs": inputs, "outputs": outputs}


def _default_step_size(fmu: Any) -> float:
    default = (
        getattr(fmu, "meta", {}).get("default_experiment")
        if isinstance(getattr(fmu, "meta", {}), dict)
        else {}
    )
    if isinstance(default, dict):
        numeric = _positive_float(default.get("stepSize"))
        if numeric is not None:
            return numeric
    capabilities = getattr(fmu, "capabilities", None)
    if capabilities is not None:
        numeric = _positive_float(getattr(capabilities, "fixed_internal_step_size", None))
        if numeric is not None:
            return numeric
    return 0.01


# ---------------------------------------------------------------------------
# Scenario window helpers
# ---------------------------------------------------------------------------

def _scenario_window(stage_config: Mapping[str, Any]) -> dict[str, Any]:
    raw = stage_config.get("scenario_window")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _scenario_start(stage_config: Mapping[str, Any]) -> float:
    window = _scenario_window(stage_config)
    for key in ("start_time", "start", "start_time_s"):
        numeric = _positive_float(window.get(key))
        if numeric is not None:
            return numeric
    raw = window.get("start_time")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass
    return 0.0


def _infer_stop_time(
    matching_result: MatchingResult,
    *,
    start_time: float,
    stage_config: Mapping[str, Any],
) -> float:
    window = _scenario_window(stage_config)
    for key in ("stop_time", "stop", "end_time", "stop_time_s", "end_time_s"):
        numeric = _positive_float(window.get(key))
        if numeric is not None and numeric > start_time:
            return numeric
    duration = _positive_float(window.get("duration"))
    if duration is not None:
        return start_time + duration

    for task in matching_result.task_set.tasks:
        regime = task.operating_regime
        if regime is not None and regime.end_time is not None:
            stop_time = float(regime.end_time)
            if stop_time > start_time:
                return stop_time

    durations: list[float] = []
    for fmu in matching_result.selected_fmus:
        default = fmu.meta.get("default_experiment") if isinstance(fmu.meta, dict) else {}
        if not isinstance(default, dict):
            continue
        stop = default.get("stopTime")
        start = default.get("startTime", 0.0)
        try:
            stop_numeric = float(stop)
            start_numeric = float(start or 0.0)
        except (TypeError, ValueError):
            continue
        if stop_numeric > start_numeric:
            durations.append(stop_numeric)
    if durations:
        return max(max(durations), start_time + 1.0)
    return start_time + 1.0


# ---------------------------------------------------------------------------
# Execution order — local topological sort
# ---------------------------------------------------------------------------

def _derive_execution_order(matching_result: MatchingResult) -> list[str]:
    """Topological sort of selected FMUs based on graph bindings."""
    nodes = [fmu.uid for fmu in matching_result.selected_fmus]
    node_set = set(nodes)
    outgoing: dict[str, set[str]] = {uid: set() for uid in nodes}
    incoming: dict[str, set[str]] = {uid: set() for uid in nodes}
    for binding in matching_result.graph.bindings:
        s, t = binding.source_fmu, binding.target_fmu
        if s in node_set and t in node_set and s != t:
            outgoing[s].add(t)
            incoming[t].add(s)

    indegree = {uid: len(incoming[uid]) for uid in nodes}
    ready = deque(sorted(uid for uid in nodes if indegree[uid] == 0))
    ordered: list[str] = []
    while ready:
        node = ready.popleft()
        ordered.append(node)
        for neighbor in sorted(outgoing[node]):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)

    ordered_set = set(ordered)
    remaining = [uid for uid in nodes if uid not in ordered_set]
    return ordered + sorted(remaining)


def _deterministic_execution_order(matching_result: MatchingResult) -> list[str]:
    ordered = _ordered_unique_ids(_derive_execution_order(matching_result))
    selected_assets = _ordered_unique_ids([fmu.uid for fmu in matching_result.selected_fmus])
    return ordered + [asset_id for asset_id in selected_assets if asset_id not in ordered]


def _selected_asset_ids(matching_result: MatchingResult) -> list[str]:
    return [str(fmu.uid).strip() for fmu in matching_result.selected_fmus if str(fmu.uid).strip()]


def _ordered_selected_fmus(matching_result: MatchingResult, *, selected_asset_ids: Sequence[str]) -> list[Any]:
    fmu_by_uid = {fmu.uid: fmu for fmu in matching_result.selected_fmus}
    return [fmu_by_uid[asset_id] for asset_id in selected_asset_ids if asset_id in fmu_by_uid]


# ---------------------------------------------------------------------------
# Binding / connection helpers
# ---------------------------------------------------------------------------

def _binding_sort_key(binding: PortBinding, *, node_index: Mapping[str, int]) -> tuple[Any, ...]:
    return (
        node_index.get(binding.source_fmu, 10**6),
        node_index.get(binding.target_fmu, 10**6),
        binding.source_fmu,
        binding.target_fmu,
        binding.source_signal,
        binding.target_signal,
        binding.chain_id,
        binding.segment_id,
    )


def _base_connection_records(
    matching_result: MatchingResult,
    *,
    selected_asset_ids: Sequence[str],
) -> list[dict[str, Any]]:
    node_index = {uid: index for index, uid in enumerate(selected_asset_ids)}
    selected_nodes = set(selected_asset_ids)
    bindings = [
        binding
        for binding in matching_result.graph.bindings
        if binding.source_fmu in selected_nodes and binding.target_fmu in selected_nodes
    ]
    records: list[dict[str, Any]] = []
    for binding in sorted(bindings, key=lambda item: _binding_sort_key(item, node_index=node_index)):
        records.append(
            {
                "source": f"{binding.source_fmu}.{binding.source_signal}",
                "target": f"{binding.target_fmu}.{binding.target_signal}",
                "kind": "direct",
                "chain_id": binding.chain_id,
                "segment_id": binding.segment_id,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Per-node period / deterministic schedule
# ---------------------------------------------------------------------------

def _per_node_period(
    matching_result: MatchingResult,
    *,
    selected_asset_ids: Sequence[str],
    step_size: float,
) -> dict[str, float]:
    fmu_by_uid = {fmu.uid: fmu for fmu in matching_result.selected_fmus}
    out: dict[str, float] = {}
    for asset_id in selected_asset_ids:
        preferred = _default_step_size(fmu_by_uid[asset_id]) if asset_id in fmu_by_uid else step_size
        multiples = max(1, round(preferred / max(step_size, 1e-9)))
        out[asset_id] = float(multiples) * float(step_size)
    return out


def _deterministic_schedule(
    matching_result: MatchingResult,
    *,
    selected_asset_ids: Sequence[str],
    execution_order: Sequence[str],
    start_time: float,
    stop_time: float,
    step_size: float,
) -> dict[str, Any]:
    step = max(float(step_size), 1e-9)
    duration = max(float(stop_time) - float(start_time), step)
    per_node = _per_node_period(
        matching_result,
        selected_asset_ids=selected_asset_ids,
        step_size=step,
    )
    warnings: list[str] = []
    for asset_id, period in per_node.items():
        fmu = next((f for f in matching_result.selected_fmus if f.uid == asset_id), None)
        if fmu and abs(period - _default_step_size(fmu)) > 1e-12:
            warnings.append(f"quantized_period[{asset_id}]={period}")
    kind = "single_fmu" if len(selected_asset_ids) == 1 and not matching_result.graph.bindings else "co_simulation"
    schedule: dict[str, Any] = {
        "kind": kind,
        "start_time": float(start_time),
        "stop_time": float(stop_time),
        "duration": float(duration),
        "step_size": float(step),
        "execution_order": list(execution_order),
        "node_order": list(execution_order),
        "warnings": warnings,
    }
    if len(selected_asset_ids) > 1:
        schedule["per_node_period"] = dict(per_node)
    return schedule


def _task_goal(matching_result: MatchingResult, mbse_context: MBSEContext) -> str:
    system_name = str(mbse_context.system_name or "system").strip() or "system"
    return (
        "Generate the final UNIFIED_SOLUTION_V1 orchestration payload fields for "
        f"{len(matching_result.selected_fmus)} FMUs in {system_name} without using adapters or loop wrappers."
    )


def _coarse_step_size(
    matching_result: MatchingResult,
    *,
    stage_config: Mapping[str, Any],
) -> float:
    scenario_step = _positive_float(_scenario_window(stage_config).get("step_size"))
    default_steps = [_default_step_size(fmu) for fmu in matching_result.selected_fmus]
    if scenario_step is not None:
        default_steps.append(float(scenario_step))
    return max(default_steps) if default_steps else 0.01


def _weak_fallback_schedule(
    matching_result: MatchingResult,
    *,
    selected_asset_ids: Sequence[str],
    execution_order: Sequence[str],
    start_time: float,
    stop_time: float,
    step_size: float,
) -> dict[str, Any]:
    step = max(float(step_size), 1e-9)
    duration = max(float(stop_time) - float(start_time), step)
    schedule: dict[str, Any] = {
        "kind": "single_fmu" if len(selected_asset_ids) == 1 else "fixed_step",
        "start_time": float(start_time),
        "stop_time": float(stop_time),
        "duration": float(duration),
        "step_size": float(step),
        "execution_order": list(execution_order),
        "node_order": list(execution_order),
        "warnings": ["weak_stage3_fallback"],
    }
    if len(selected_asset_ids) > 1:
        schedule["per_node_period"] = {
            asset_id: float(step)
            for asset_id in selected_asset_ids
        }
    return schedule


def _weak_fallback_final_solution_payload(
    matching_result: MatchingResult,
    *,
    stage_config: Mapping[str, Any],
    task_goal: str,
) -> dict[str, Any]:
    selected_asset_ids = _selected_asset_ids(matching_result)
    execution_order = list(selected_asset_ids)
    start_time = _scenario_start(stage_config)
    stop_time = _infer_stop_time(matching_result, start_time=start_time, stage_config=stage_config)
    step_size = _coarse_step_size(
        matching_result,
        stage_config=stage_config,
    )
    schedule = _weak_fallback_schedule(
        matching_result,
        selected_asset_ids=selected_asset_ids,
        execution_order=execution_order,
        start_time=start_time,
        stop_time=stop_time,
        step_size=step_size,
    )
    return {
        "selected_asset_ids": list(selected_asset_ids),
        "connections": [],
        "schedule": schedule,
        "execution_order": list(execution_order),
        "adapters": [],
        "loop_resolution": [],
        "extensions": {},
        "notes": _unique_strings(
            [
                f"task_goal={task_goal}",
                f"selected_fmu_count={len(selected_asset_ids)}",
                "connection_count=0",
                "fallback_mode=weak_fixed_step",
                "stage3_variant=llm_generated_script",
            ]
        ),
    }


# ---------------------------------------------------------------------------
# LLM call (openai library, env-var config)
# ---------------------------------------------------------------------------

def _chat_json_openai(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 1600,
) -> dict[str, Any] | None:
    """Call an OpenAI-compatible API and parse the JSON response."""
    api_key = os.environ.get("PIPELINE_LLM_API_KEY", "")
    if not api_key:
        return None

    base_url = os.environ.get("PIPELINE_LLM_BASE_URL", "") or None
    model = os.environ.get("PIPELINE_LLM_MODEL", "gpt-4o")
    timeout = float(os.environ.get("PIPELINE_LLM_TIMEOUT_SECONDS", "60"))

    normalized_base = (base_url or "https://api.openai.com").strip().rstrip("/")
    if normalized_base.endswith("/chat/completions"):
        url = normalized_base
    elif normalized_base.endswith("/v1"):
        url = normalized_base + "/chat/completions"
    else:
        url = normalized_base + "/v1/chat/completions"

    body = json.dumps({
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=int(timeout)) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            content = (choices[0].get("message", {}).get("content") or "").strip()
        else:
            return None
        if content.startswith("```"):
            lines = content.split("\n")
            end = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            content = "\n".join(lines[1:end])
        return json.loads(content)
    except Exception:
        return None


chat_json = _chat_json_openai


# ---------------------------------------------------------------------------
# Sanitization helpers
# ---------------------------------------------------------------------------

def _port_constraints(matching_result: MatchingResult) -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = {}
    for fmu in matching_result.selected_fmus:
        catalog = _port_catalog(fmu)
        inputs = set(catalog.get("inputs") or [])
        outputs = set(catalog.get("outputs") or [])
        known = inputs | outputs
        out[fmu.uid] = {
            "inputs": inputs or set(known),
            "outputs": outputs or set(known),
            "known": known,
        }
    return out


def _sanitize_execution_order(
    value: Any,
    *,
    selected_asset_ids: Sequence[str],
) -> list[str]:
    ordered = _ordered_unique_ids([str(item or "").strip() for item in value] if isinstance(value, list) else [])
    if not ordered or set(ordered) != set(selected_asset_ids):
        return []
    return ordered


def _sanitize_connections(
    value: Any,
    *,
    selected_asset_ids: Sequence[str],
    port_constraints: Mapping[str, Mapping[str, set[str]]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    selected_assets = set(selected_asset_ids)
    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            return []
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if not source or not target:
            return []
        if "." not in source or "." not in target:
            return []
        source_asset, source_signal = source.split(".", 1)
        target_asset, target_signal = target.split(".", 1)
        if (
            source_asset not in selected_assets
            or target_asset not in selected_assets
            or not source_signal.strip()
            or not target_signal.strip()
            or source_asset == target_asset
        ):
            return []
        source_rules = port_constraints.get(source_asset) or {}
        target_rules = port_constraints.get(target_asset) or {}
        if source_signal not in set(source_rules.get("outputs") or set()):
            return []
        if target_signal not in set(target_rules.get("inputs") or set()):
            return []
        key = (source, target)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        normalized.append({"source": source, "target": target, "kind": "direct"})
    return normalized


def _sanitize_per_node_period(
    value: Any,
    *,
    selected_asset_ids: Sequence[str],
    step_size: float,
) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    selected_assets = set(selected_asset_ids)
    period_map: dict[str, float] = {}
    for asset_id in selected_asset_ids:
        raw = value.get(asset_id)
        numeric = _positive_float(raw)
        if numeric is None:
            return {}
        if asset_id not in selected_assets:
            return {}
        period_map[asset_id] = float(numeric)
    if set(period_map) != selected_assets:
        return {}
    if any(period < step_size for period in period_map.values()):
        return {}
    return period_map


def _sanitize_schedule(
    value: Any,
    *,
    selected_asset_ids: Sequence[str],
    execution_order: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    kind = str(value.get("kind") or "").strip().lower()
    if kind not in _ALLOWED_SCHEDULE_KINDS:
        return {}
    if len(selected_asset_ids) > 1 and kind == "single_fmu":
        return {}
    start_time = value.get("start_time", 0.0)
    stop_time = value.get("stop_time")
    step_size = value.get("step_size", value.get("base_tick"))
    try:
        start_numeric = float(start_time)
        stop_numeric = float(stop_time)
        step_numeric = float(step_size)
    except (TypeError, ValueError):
        return {}
    if stop_numeric <= start_numeric or step_numeric <= 0.0:
        return {}
    schedule: dict[str, Any] = {
        "kind": kind,
        "start_time": start_numeric,
        "stop_time": stop_numeric,
        "duration": stop_numeric - start_numeric,
        "step_size": step_numeric,
        "execution_order": list(execution_order),
        "node_order": list(
            _sanitize_execution_order(value.get("node_order"), selected_asset_ids=selected_asset_ids)
            or execution_order
        ),
        "warnings": _string_list(value.get("warnings"), max_items=10),
    }
    if len(selected_asset_ids) > 1:
        period_map = _sanitize_per_node_period(
            value.get("per_node_period"),
            selected_asset_ids=selected_asset_ids,
            step_size=step_numeric,
        )
        if not period_map:
            return {}
        schedule["per_node_period"] = period_map
    return schedule


def _sanitize_extensions(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    cloned = _json_clone(dict(value), fallback={})
    return cloned if isinstance(cloned, dict) else {}


def _sanitize_final_solution_payload(
    response: object,
    *,
    matching_result: MatchingResult,
) -> dict[str, Any]:
    payload = response
    if isinstance(response, dict) and isinstance(response.get("final_solution_payload"), dict):
        payload = response.get("final_solution_payload")
    if not isinstance(payload, dict):
        return {}
    for required_key in ("selected_asset_ids", "connections", "schedule", "execution_order"):
        if required_key not in payload:
            return {}

    selected_asset_ids = _ordered_unique_ids(
        [str(item or "").strip() for item in list(payload.get("selected_asset_ids") or [])]
    )
    expected_asset_ids = _selected_asset_ids(matching_result)
    if selected_asset_ids != expected_asset_ids:
        return {}

    execution_order = _sanitize_execution_order(payload.get("execution_order"), selected_asset_ids=selected_asset_ids)
    if not execution_order:
        return {}

    if not isinstance(payload.get("connections"), list):
        return {}
    connections = _sanitize_connections(
        payload.get("connections"),
        selected_asset_ids=selected_asset_ids,
        port_constraints=_port_constraints(matching_result),
    )
    if len(selected_asset_ids) == 1 and payload.get("connections") in (None, []):
        connections = []
    elif payload.get("connections") is not None and not connections and list(payload.get("connections") or []):
        return {}

    schedule = _sanitize_schedule(
        payload.get("schedule"),
        selected_asset_ids=selected_asset_ids,
        execution_order=execution_order,
    )
    if not schedule:
        return {}

    raw_adapters = payload.get("adapters", [])
    raw_loops = payload.get("loop_resolution", [])
    if raw_adapters not in (None, []) or raw_loops not in (None, []):
        return {}

    return {
        "selected_asset_ids": list(selected_asset_ids),
        "connections": list(connections),
        "schedule": schedule,
        "execution_order": list(execution_order),
        "adapters": [],
        "loop_resolution": [],
        "extensions": _sanitize_extensions(payload.get("extensions")),
        "notes": _string_list(payload.get("notes"), max_items=12),
    }


# ---------------------------------------------------------------------------
# LLM payload generation
# ---------------------------------------------------------------------------

def _llm_final_solution_payload(
    matching_result: MatchingResult,
    *,
    mbse_context: MBSEContext,
    task_goal: str,
    stage_config: Mapping[str, Any],
) -> dict[str, Any]:
    selected_asset_ids = _selected_asset_ids(matching_result)
    user_prompt = json.dumps(
        {
            "task_goal": task_goal,
            "mbse_system": mbse_context.system_name,
            "task_set_id": matching_result.task_set.task_set_id,
            "selected_asset_ids": list(selected_asset_ids),
            "selected_assets": [
                {
                    "asset_id": fmu.uid,
                    "name": fmu.name,
                    "ports": _port_catalog(fmu),
                    "default_step_size": _default_step_size(fmu),
                }
                for fmu in matching_result.selected_fmus
            ],
            "scenario_window": _scenario_window(stage_config),
            "required_output_shape": {
                "selected_asset_ids": list(selected_asset_ids),
                "adapters": [],
                "loop_resolution": [],
            },
        },
        ensure_ascii=False,
    )
    response = chat_json(_SYSTEM_PROMPT, user_prompt, temperature=0.1, max_tokens=1600)
    if response is None:
        return {}
    return _sanitize_final_solution_payload(response, matching_result=matching_result)


# ---------------------------------------------------------------------------
# SimulationConfig construction & local validation
# ---------------------------------------------------------------------------

def _validate_simulation_config(config: SimulationConfig) -> list[str]:
    issues: list[str] = []
    if config.step_size <= 0:
        issues.append("step_size must be positive")
    if config.duration <= 0:
        issues.append("duration must be positive")
    if not config.fmus:
        issues.append("fmus list is empty")
    if config.step_size > config.duration:
        issues.append("step_size exceeds duration")
    fmu_uids = [fmu.uid for fmu in config.fmus]
    if len(fmu_uids) != len(set(fmu_uids)):
        issues.append("duplicate fmu uids")
    seen_conns: set[str] = set()
    for conn in config.connections:
        key = f"{conn.get('source', '')}->{conn.get('target', '')}"
        if key in seen_conns:
            issues.append(f"duplicate connection: {key}")
        seen_conns.add(key)
    return issues


def _simulation_config_from_payload(
    matching_result: MatchingResult,
    *,
    method_name: str,
    workspace_root: Path,
    final_solution_payload: Mapping[str, Any],
    generation_source: str,
    fallback_used: bool,
) -> tuple[SimulationConfig, list[str]]:
    selected_asset_ids = [
        str(item).strip()
        for item in list(final_solution_payload.get("selected_asset_ids") or [])
        if str(item).strip()
    ]
    ordered_fmus = _ordered_selected_fmus(matching_result, selected_asset_ids=selected_asset_ids)
    schedule = dict(final_solution_payload.get("schedule") or {})
    start_time = float(schedule.get("start_time", 0.0) or 0.0)
    stop_time = float(schedule.get("stop_time", schedule.get("duration", 0.0)) or 0.0)
    step_size = float(schedule.get("step_size", 0.01) or 0.01)
    config = SimulationConfig(
        step_size=max(step_size, 1e-9),
        duration=max(stop_time - start_time, step_size),
        fmus=ordered_fmus,
        connections=[
            dict(item) for item in list(final_solution_payload.get("connections") or []) if isinstance(item, dict)
        ],
        scheduler=dict(schedule),
        meta={
            "method_name": method_name,
            "workspace_root": str(workspace_root),
            "selected_task_set_id": matching_result.task_set.task_set_id,
            "selected_asset_ids": list(selected_asset_ids),
            "adapters": [],
            "loop_resolution": [],
            "script_generation_source": generation_source,
            "fallback_used": fallback_used,
            "final_solution_payload": _json_clone(dict(final_solution_payload), fallback={}),
            "script_notes": list(final_solution_payload.get("notes") or []),
        },
    )
    validation_issues = _validate_simulation_config(config)
    return config, validation_issues


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _filtered_bindings(
    matching_result: MatchingResult,
    *,
    normalized_connections: Sequence[Mapping[str, Any]],
) -> list[PortBinding]:
    allowed_pairs = {
        (
            str(item.get("source") or "").strip(),
            str(item.get("target") or "").strip(),
        )
        for item in normalized_connections
        if isinstance(item, Mapping)
    }
    return [
        binding
        for binding in matching_result.graph.bindings
        if (
            f"{binding.source_fmu}.{binding.source_signal}",
            f"{binding.target_fmu}.{binding.target_signal}",
        )
        in allowed_pairs
    ]


def _graph_for_payload(
    matching_result: MatchingResult,
    *,
    final_solution_payload: Mapping[str, Any],
    generation_source: str,
    fallback_used: bool,
) -> OrchestrationGraph:
    selected_asset_ids = [
        str(item).strip()
        for item in list(final_solution_payload.get("selected_asset_ids") or [])
        if str(item).strip()
    ]
    selected_assets = set(selected_asset_ids)
    filtered = _filtered_bindings(
        matching_result,
        normalized_connections=list(final_solution_payload.get("connections") or []),
    )
    return OrchestrationGraph(
        nodes=list(selected_asset_ids),
        port_nodes=list(matching_result.graph.port_nodes),
        bindings=filtered,
        component_to_fmu={
            component: asset_id
            for component, asset_id in matching_result.graph.component_to_fmu.items()
            if asset_id in selected_assets
        },
        required_signal_chains=list(matching_result.graph.required_signal_chains),
        binding_candidates=list(matching_result.graph.binding_candidates),
        closure_ok=bool(matching_result.graph.closure_ok),
        closure_failures=list(matching_result.graph.closure_failures),
        routing_failures=list(matching_result.graph.routing_failures),
        diagnostics={
            **dict(matching_result.graph.diagnostics),
            "stage3_variant": "llm_generated_script",
            "generation_source": generation_source,
            "fallback_used": fallback_used,
            "adapter_generation": False,
            "loop_wrapper_generation": False,
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def llm_generated_script_stage3(
    matching_result: MatchingResult,
    *,
    mbse_context: MBSEContext,
    config: Mapping[str, Any] | None,
) -> CompositionResult:
    stage_config = _config_dict(config)
    method_name, workspace_root = _validate_workspace_context(stage_config)
    if not matching_result.selected_fmus:
        raise ValueError("llm_generated_script_stage3 received empty selected_fmus")

    task_goal = _task_goal(matching_result, mbse_context)
    fallback_payload = _weak_fallback_final_solution_payload(
        matching_result,
        stage_config=stage_config,
        task_goal=task_goal,
    )
    llm_payload = _llm_final_solution_payload(
        matching_result,
        mbse_context=mbse_context,
        task_goal=task_goal,
        stage_config=stage_config,
    )
    final_solution_payload = llm_payload or fallback_payload
    fallback_used = not bool(llm_payload)
    generation_source = "deterministic_fallback" if fallback_used else "llm"

    simulation_config, validation_issues = _simulation_config_from_payload(
        matching_result,
        method_name=method_name,
        workspace_root=workspace_root,
        final_solution_payload=final_solution_payload,
        generation_source=generation_source,
        fallback_used=fallback_used,
    )
    graph_augmented = _graph_for_payload(
        matching_result,
        final_solution_payload=final_solution_payload,
        generation_source=generation_source,
        fallback_used=fallback_used,
    )
    schedule = {
        **dict(simulation_config.scheduler),
        "stage3_variant": "llm_generated_script",
        "generation_source": generation_source,
        "fallback_used": fallback_used,
    }
    return CompositionResult(
        graph_augmented=graph_augmented,
        adapters=[],
        schedule=schedule,
        loop_resolution=[],
        simulation_config=simulation_config,
        diagnostics={
            "stage3_variant": "llm_generated_script",
            "generation_source": generation_source,
            "fallback_used": fallback_used,
            "validation_issues": validation_issues,
        },
    )


__all__ = ["llm_generated_script_stage3"]
