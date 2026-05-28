"""Stage 1 full implementation: requirement + MBSE model -> calibrated task sets."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

from pipeline.llm_guidance import build_strict_json_system_prompt, goal_is_aligned, normalize_text, tokenize, unique_strings
from pipeline.llm_client import chat_json
from pipeline.types import (
    AcceptanceCriterion,
    ChainSegment,
    MBSEContext,
    OperatingRegime,
    RequiredSignalChain,
    TaskConstraint,
    TaskSet,
    TaskSignalSpec,
    VerificationTask,
)

from .calibration import apply_conformal_filter, compute_verifiability_score, load_calibration_model
from .grounding import ground_taskset_to_mbse, repair_invalid_grounding, validate_grounded_taskset


def _unique_preserve(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _compact_norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(text))


def _component_is_mentioned(component_name: str, component_type: str, requirement: str) -> bool:
    requirement_tokens = set(tokenize(requirement))
    requirement_compact = _compact_norm(requirement)
    for candidate in (component_name, component_type):
        candidate_tokens = set(tokenize(candidate))
        if candidate_tokens & requirement_tokens:
            return True
        compact = _compact_norm(candidate)
        if compact and compact in requirement_compact:
            return True
    return False


def _extract_acceptance_criteria(requirement: str) -> List[AcceptanceCriterion]:
    criteria: List[AcceptanceCriterion] = []
    range_re = re.compile(r"([A-Za-z0-9_()]+)\s+(?:in|within)\s+\[([\d.\-]+),\s*([\d.\-]+)\]\s*([A-Za-z/%0-9.]*)", re.I)
    cmp_re = re.compile(r"([A-Za-z0-9_()]+)\s*(<=|>=|<|>)\s*([\d.\-]+)\s*([A-Za-z/%0-9.]*)", re.I)
    below_re = re.compile(r"([A-Za-z0-9_()]+)\s+(?:below|under|less than)\s+([\d.\-]+)\s*([A-Za-z/%0-9.]*)", re.I)
    above_re = re.compile(r"([A-Za-z0-9_()]+)\s+(?:above|over|greater than)\s+([\d.\-]+)\s*([A-Za-z/%0-9.]*)", re.I)

    def _parse_float(text: str) -> float:
        cleaned = str(text or "").strip().rstrip(".,;:")
        return float(cleaned)

    for match in range_re.finditer(requirement):
        criteria.append(
            AcceptanceCriterion(
                metric=str(match.group(1)),
                operator="within",
                value=[_parse_float(match.group(2)), _parse_float(match.group(3))],
                unit=str(match.group(4) or ""),
            )
        )
    for regex in (cmp_re, below_re, above_re):
        for match in regex.finditer(requirement):
            op = match.group(2) if regex is cmp_re else ("<" if regex is below_re else ">")
            criteria.append(
                AcceptanceCriterion(
                    metric=str(match.group(1)),
                    operator=str(op),
                    value=_parse_float(match.group(3) if regex is cmp_re else match.group(2)),
                    unit=str(match.group(4) if regex is cmp_re else match.group(3) or ""),
                )
            )
    return criteria


def _extract_operating_regime(requirement: str) -> OperatingRegime | None:
    time_match = re.search(r"time window\s+([\d.]+)s\s+to\s+([\d.]+)s", requirement, re.I)
    inputs: Dict[str, str] = {}
    initial_conditions: Dict[str, str] = {}

    inputs_match = re.search(r"inputs:\s*(.*?)(?:;\s*initial conditions:|;\s*acceptance criteria:|\.|$)", requirement, re.I)
    if inputs_match:
        for name in re.split(r",\s*", inputs_match.group(1)):
            text = name.strip().strip(" ;:.,")
            if text:
                inputs[text] = "provided"

    init_match = re.search(r"initial conditions:\s*(.*?)(?:;\s*acceptance criteria:|\.|$)", requirement, re.I)
    if init_match:
        for name in re.split(r",\s*", init_match.group(1)):
            text = name.strip().strip(" ;:.,")
            if text:
                initial_conditions[text] = "provided"

    if not time_match and not inputs and not initial_conditions:
        return None

    return OperatingRegime(
        start_time=float(time_match.group(1)) if time_match else None,
        end_time=float(time_match.group(2)) if time_match else None,
        inputs=inputs,
        initial_conditions=initial_conditions,
        description="Extracted from requirement text",
    )


_SIGNAL_FUNCTION_NAMES = frozenset(
    {
        "abs",
        "after",
        "all",
        "at",
        "benchmark",
        "default",
        "example",
        "fmu",
        "input",
        "inputs",
        "less",
        "match",
        "max",
        "metric",
        "min",
        "model",
        "monitored",
        "observe",
        "output",
        "outputs",
        "over",
        "requirement",
        "run",
        "suite",
        "than",
        "the",
        "trajectory",
        "under",
        "verify",
        "within",
    }
)
_EXPLICIT_SIGNAL_CLAUSE_RE = re.compile(
    r"(?:observe|monitor|monitored)\s+outputs?\s*:\s*([^.;]+)|signals?\s+of\s+interest\s*:\s*([^.;]+)",
    re.I,
)
_MONITORED_GENERIC_SIGNAL_RE = re.compile(r"\bmonitored\s+(inputs?|outputs?)\b", re.I)
_INDEXED_SIGNAL_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\[\d+\]")
_SIGNAL_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def _metric_signal_candidates(metric: str) -> List[str]:
    candidates: List[str] = []
    candidates.extend(match.group(0) for match in _INDEXED_SIGNAL_RE.finditer(metric or ""))
    for match in _SIGNAL_IDENTIFIER_RE.finditer(metric or ""):
        candidate = str(match.group(0) or "").strip()
        lowered = candidate.lower()
        if not candidate or lowered in _SIGNAL_FUNCTION_NAMES:
            continue
        if "_" not in candidate and candidate.isalpha() and candidate[:1].isupper():
            continue
        candidates.append(candidate)
    return _unique_preserve(candidates)


def _explicit_requirement_signals(requirement: str, mbse_context: MBSEContext) -> List[str]:
    del mbse_context
    candidates: List[str] = []
    explicit_generics: List[str] = []
    candidates.extend(match.group(0) for match in _INDEXED_SIGNAL_RE.finditer(requirement or ""))
    for criterion in _extract_acceptance_criteria(requirement):
        candidates.extend(_metric_signal_candidates(criterion.metric))
    for clause_match in _EXPLICIT_SIGNAL_CLAUSE_RE.finditer(requirement or ""):
        clause = next((group for group in clause_match.groups() if group), "")
        for part in re.split(r",\s*", clause):
            text = str(part or "").strip()
            if not text:
                continue
            candidates.extend(_metric_signal_candidates(text))
            indexed = _INDEXED_SIGNAL_RE.search(text)
            if indexed:
                candidates.append(indexed.group(0))
    explicit_generics.extend(match.group(1).lower() for match in _MONITORED_GENERIC_SIGNAL_RE.finditer(requirement or ""))
    return _unique_preserve(
        candidate
        for candidate in [*candidates, *explicit_generics]
        if candidate and (candidate.lower() not in {"input", "inputs", "output", "outputs"} or candidate in explicit_generics)
    )


def _mentioned_signals(requirement: str, mbse_context: MBSEContext) -> List[str]:
    req_tokens = set(tokenize(requirement))
    signals: List[str] = []
    for component in mbse_context.components:
        for port in component.ports:
            tokens = set(tokenize(port.name)) | set(tokenize(port.qualified_name))
            if tokens & req_tokens:
                signals.append(port.name)
    return _unique_preserve(signals)


def _signal_role(direction: str) -> str:
    direction_norm = (direction or "").strip().lower()
    if direction_norm in {"out", "output", "provided", "send"}:
        return "observed"
    if direction_norm in {"in", "input", "required", "receive"}:
        return "driven"
    return "monitored"


def _matching_mbse_ports(signal_name: str, grounded_components: Sequence[str], mbse_context: MBSEContext) -> List[Tuple[str, object]]:
    signal_norm = normalize_text(signal_name)
    component_filter = set(grounded_components)
    matches: List[Tuple[str, object]] = []
    for component in mbse_context.components:
        if component_filter and component.name not in component_filter:
            continue
        for port in component.ports:
            aliases = {normalize_text(port.name), normalize_text(port.qualified_name or "")}
            if signal_norm in aliases or signal_norm == normalize_text(f"{component.name}.{port.name}"):
                matches.append((component.name, port))
    if matches or component_filter:
        return matches
    for component in mbse_context.components:
        for port in component.ports:
            aliases = {normalize_text(port.name), normalize_text(port.qualified_name or "")}
            if signal_norm in aliases:
                matches.append((component.name, port))
    return matches


def derive_task_signal_specs(task: VerificationTask, mbse_context: MBSEContext) -> List[TaskSignalSpec]:
    signals = _unique_preserve(list(task.required_signals) + list(task.grounded_ports))
    specs: List[TaskSignalSpec] = []
    seen: Set[Tuple[str, str, str]] = set()
    for signal_name in signals:
        matches = _matching_mbse_ports(signal_name, task.grounded_components, mbse_context)
        if not matches:
            key = (signal_name, "", "")
            if key in seen:
                continue
            seen.add(key)
            specs.append(
                TaskSignalSpec(
                    signal_name=signal_name,
                    source_text=signal_name,
                    role="monitored",
                    grounded_component_ref="",
                    grounded_port_ref="",
                )
            )
            continue
        for component_name, port in matches:
            key = (signal_name, component_name, port.name)
            if key in seen:
                continue
            seen.add(key)
            specs.append(
                TaskSignalSpec(
                    signal_name=signal_name,
                    direction=port.direction,
                    component_hint=component_name,
                    port_hint=port.qualified_name or port.name,
                    type_hint=port.type_hint,
                    role=_signal_role(port.direction),
                    source_text=signal_name,
                    grounded_component_ref=component_name,
                    grounded_port_ref=port.qualified_name or port.name,
                )
            )
    return specs


def derive_task_constraints(
    task: VerificationTask,
    requirement: str,
    mbse_context: MBSEContext,
    *,
    signal_specs: Sequence[TaskSignalSpec] | None = None,
) -> List[TaskConstraint]:
    constraints: List[TaskConstraint] = []
    resolved_signal_specs = list(signal_specs or task.signal_specs)
    signal_aliases: Dict[str, str] = {}
    for spec in resolved_signal_specs:
        canonical = spec.signal_name or spec.grounded_port_ref or spec.port_hint
        for alias in (spec.signal_name, spec.port_hint, spec.grounded_port_ref):
            key = normalize_text(alias)
            if key and canonical:
                signal_aliases.setdefault(key, spec.signal_name or canonical)
    fallback_signal = task.required_signals[0] if task.required_signals else ""
    for criterion in task.acceptance_criteria:
        grounded_signal = signal_aliases.get(normalize_text(criterion.metric), "")
        if not grounded_signal and criterion.metric in set(task.required_signals) | set(task.grounded_ports):
            grounded_signal = criterion.metric
        if not grounded_signal:
            grounded_signal = fallback_signal
        matching_specs = [
            spec
            for spec in resolved_signal_specs
            if spec.signal_name == grounded_signal
            or normalize_text(spec.port_hint) == normalize_text(criterion.metric)
            or normalize_text(spec.grounded_port_ref) == normalize_text(criterion.metric)
        ]
        component_ref = matching_specs[0].grounded_component_ref if matching_specs else ""
        port_ref = matching_specs[0].grounded_port_ref if matching_specs else ""
        if grounded_signal and not component_ref:
            matches = _matching_mbse_ports(grounded_signal, task.grounded_components, mbse_context)
            if not matches:
                matches = _matching_mbse_ports(criterion.metric, task.grounded_components, mbse_context)
            if matches:
                component_ref = matches[0][0]
                port_ref = matches[0][1].qualified_name or matches[0][1].name
        if not component_ref and task.grounded_components:
            component_ref = task.grounded_components[0]
        if not port_ref:
            port_ref = grounded_signal
        constraints.append(
            TaskConstraint(
                metric=criterion.metric,
                operator=criterion.operator,
                value=criterion.value,
                unit=criterion.unit,
                grounded_signal=grounded_signal,
                scope=task.grounded_components[0] if task.grounded_components else "task",
                source_text=requirement,
                grounded_component_ref=component_ref,
                grounded_port_ref=port_ref,
            )
        )
    return constraints


def derive_required_signal_chains(taskset: TaskSet, mbse_context: MBSEContext) -> List[RequiredSignalChain]:
    if not mbse_context.connections:
        return []
    task_ids_by_component: Dict[str, List[str]] = {}
    task_ids_by_signal: Dict[str, List[str]] = {}
    for task in taskset.tasks:
        for component_name in task.grounded_components:
            task_ids_by_component.setdefault(component_name, []).append(task.task_id)
        for signal_name in task.required_signals:
            task_ids_by_signal.setdefault(signal_name, []).append(task.task_id)
    relevant_components = set(task_ids_by_component)
    relevant_signals = set(task_ids_by_signal)
    chains: List[RequiredSignalChain] = []
    for index, connection in enumerate(mbse_context.connections):
        if relevant_components and (
            connection.source_component not in relevant_components or connection.target_component not in relevant_components
        ):
            if not relevant_signals or {connection.source_signal, connection.target_signal}.isdisjoint(relevant_signals):
                continue
        origin_task_ids = _unique_preserve(
            task_ids_by_component.get(connection.source_component, [])
            + task_ids_by_component.get(connection.target_component, [])
            + task_ids_by_signal.get(connection.source_signal, [])
            + task_ids_by_signal.get(connection.target_signal, [])
        )
        chain_id = f"chain_{index}"
        semantic_intent = f"{connection.source_component}.{connection.source_signal} -> {connection.target_component}.{connection.target_signal}"
        chains.append(
            RequiredSignalChain(
                chain_id=chain_id,
                source_component=connection.source_component,
                target_component=connection.target_component,
                signals=[connection.source_signal, connection.target_signal],
                origin_task_ids=origin_task_ids,
                segments=[
                    ChainSegment(
                        segment_id=f"{chain_id}_seg_0",
                        source_component=connection.source_component,
                        source_signal=connection.source_signal,
                        target_component=connection.target_component,
                        target_signal=connection.target_signal,
                        semantic_intent=semantic_intent,
                        adjacency_evidence={
                            "source_component": connection.source_component,
                            "target_component": connection.target_component,
                        },
                    )
                ],
                semantic_intent=semantic_intent,
                details={
                    "source_signal": connection.source_signal,
                    "target_signal": connection.target_signal,
                },
            )
        )
    return chains


def _enrich_grounded_taskset(taskset: TaskSet, requirement: str, mbse_context: MBSEContext) -> TaskSet:
    tasks: List[VerificationTask] = []
    for task in taskset.tasks:
        signal_specs = derive_task_signal_specs(task, mbse_context)
        constraint_set = derive_task_constraints(task, requirement, mbse_context, signal_specs=signal_specs)
        tasks.append(
            replace(
                task,
                signal_specs=signal_specs,
                constraint_set=constraint_set,
                task_trace={
                    "components": list(task.grounded_components),
                    "ports": list(task.grounded_ports),
                    "signals": list(task.required_signals),
                    "connections": [],
                    "notes": ["stage1_enriched"],
                },
            )
        )
    enriched = replace(taskset, tasks=tasks)
    required_signal_chains = derive_required_signal_chains(enriched, mbse_context)
    return replace(
        enriched,
        required_signal_chains=required_signal_chains,
        meta={
            **dict(enriched.meta),
            "required_chain_count": len(required_signal_chains),
        },
    )


def _global_objective(requirement: str) -> str:
    text = (requirement or "").strip()
    if not text:
        return "verify system behavior"
    return text[:160]


def _mbse_summary(mbse_context: MBSEContext) -> Dict[str, Any]:
    return {
        "system_name": mbse_context.system_name,
        "components": [
            {
                "name": component.name,
                "component_type": component.component_type,
                "ports": [{"name": port.name, "direction": port.direction} for port in component.ports[:8]],
            }
            for component in mbse_context.components[:24]
        ],
        "connections": [
            {
                "source_component": connection.source_component,
                "source_signal": connection.source_signal,
                "target_component": connection.target_component,
                "target_signal": connection.target_signal,
            }
            for connection in mbse_context.connections[:24]
        ],
    }


def _build_alias_map(*groups: Sequence[str]) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for group in groups:
        items = [str(item) for item in group if str(item).strip()]
        if not items:
            continue
        canonical = items[0]
        for item in items:
            aliases.setdefault(normalize_text(item), canonical)
    return aliases


def _sanitize_name_list(values: Any, aliases: Dict[str, str]) -> List[str]:
    if not isinstance(values, list):
        return []
    output: List[str] = []
    seen: Set[str] = set()
    for value in values:
        key = normalize_text(str(value or ""))
        canonical = aliases.get(key)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        output.append(canonical)
    return output


def _sanitize_objective(value: Any, requirement: str) -> str:
    text = str(value or "").strip()
    if not text:
        return _global_objective(requirement)
    if not _goal_matches_requirement(text, requirement):
        return _global_objective(requirement)
    return text[:200]


def _goal_matches_requirement(summary: str, requirement: str) -> bool:
    requirement_tokens = tokenize(requirement)
    min_common_tokens = 2 if len(requirement_tokens) >= 4 else 1
    min_overlap = 0.2 if len(requirement_tokens) >= 4 else 0.15
    return goal_is_aligned(summary, requirement, min_common_tokens=min_common_tokens, min_overlap=min_overlap)


def _criterion_from_text(text: str) -> AcceptanceCriterion | None:
    cleaned = str(text or "").strip()
    if not cleaned:
        return None
    range_match = re.search(r"([A-Za-z0-9_()]+)\s+(?:in|within)\s+\[([\d.\-]+),\s*([\d.\-]+)\]\s*([A-Za-z/%0-9.]*)", cleaned, re.I)
    if range_match:
        return AcceptanceCriterion(
            metric=str(range_match.group(1)),
            operator="within",
            value=[float(range_match.group(2)), float(range_match.group(3))],
            unit=str(range_match.group(4) or ""),
            notes=cleaned,
        )
    compare_match = re.search(r"([A-Za-z0-9_()]+)\s*(<=|>=|<|>)\s*([\d.\-]+)\s*([A-Za-z/%0-9.]*)", cleaned, re.I)
    if compare_match:
        return AcceptanceCriterion(
            metric=str(compare_match.group(1)),
            operator=str(compare_match.group(2)),
            value=float(compare_match.group(3)),
            unit=str(compare_match.group(4) or ""),
            notes=cleaned,
        )
    below_match = re.search(r"([A-Za-z0-9_()]+)\s+(?:below|under|less than)\s+([\d.\-]+)\s*([A-Za-z/%0-9.]*)", cleaned, re.I)
    if below_match:
        return AcceptanceCriterion(
            metric=str(below_match.group(1)),
            operator="<",
            value=float(below_match.group(2)),
            unit=str(below_match.group(3) or ""),
            notes=cleaned,
        )
    above_match = re.search(r"([A-Za-z0-9_()]+)\s+(?:above|over|greater than)\s+([\d.\-]+)\s*([A-Za-z/%0-9.]*)", cleaned, re.I)
    if above_match:
        return AcceptanceCriterion(
            metric=str(above_match.group(1)),
            operator=">",
            value=float(above_match.group(2)),
            unit=str(above_match.group(3) or ""),
            notes=cleaned,
        )
    signal_match = re.search(r"\b(?:for|of|signal)\s+([A-Za-z_][A-Za-z0-9_]*)\b", cleaned, re.I)
    metric = str(signal_match.group(1) if signal_match else cleaned[:160]).strip()
    return AcceptanceCriterion(metric=metric, operator="descriptive", value=cleaned, notes=cleaned)


def _criterion_from_raw(raw: Any) -> AcceptanceCriterion | None:
    if isinstance(raw, str):
        return _criterion_from_text(raw)
    if not isinstance(raw, dict):
        return None
    metric = str(raw.get("metric") or "").strip()
    operator = str(raw.get("operator") or "").strip()
    if not metric or not operator:
        summary_text = str(raw.get("text") or raw.get("summary") or raw.get("description") or "").strip()
        return _criterion_from_text(summary_text)
    value = raw.get("value")
    if isinstance(value, list):
        cleaned = []
        for item in value:
            try:
                cleaned.append(float(item))
            except (TypeError, ValueError):
                continue
        value = cleaned or value
    elif isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            value = value.strip()
    return AcceptanceCriterion(
        metric=metric,
        operator=operator,
        value=value,
        unit=str(raw.get("unit") or ""),
        notes=str(raw.get("notes") or raw.get("text") or ""),
    )


def _regime_from_raw(raw: Any) -> OperatingRegime | None:
    if isinstance(raw, str):
        description = raw.strip()
        return OperatingRegime(description=description) if description else None
    if not isinstance(raw, dict):
        return None
    start = _safe_float(raw.get("start_time"))
    end = _safe_float(raw.get("end_time"))
    inputs = raw.get("inputs") if isinstance(raw.get("inputs"), dict) else {}
    initial_conditions = raw.get("initial_conditions") if isinstance(raw.get("initial_conditions"), dict) else {}
    assumptions = raw.get("assumptions") if isinstance(raw.get("assumptions"), list) else []
    description = str(raw.get("description") or "LLM-extracted operating regime")
    if start is None and end is None and not inputs and not initial_conditions and not assumptions and not description:
        return None
    return OperatingRegime(
        start_time=start,
        end_time=end,
        inputs={str(key): value for key, value in inputs.items()},
        initial_conditions={str(key): value for key, value in initial_conditions.items()},
        assumptions=[str(item) for item in assumptions],
        description=description,
    )


def _generate_raw_tasksets_via_llm(requirement: str, mbse_context: MBSEContext, max_candidates: int) -> List[TaskSet]:
    task_goal = "Decompose the requirement into MBSE-grounded verification task sets that preserve the current requirement objective."
    system_prompt = build_strict_json_system_prompt(
        role="an MBSE verification task decomposition assistant",
        task_goal=task_goal,
        output_contract=[
            'Top-level keys: "task_goal_summary" and "task_sets".',
            '"task_goal_summary" must restate the current requirement objective in one short sentence.',
            '"task_sets" must be a list with at most the requested number of candidates.',
            'Each task set must contain "rationale", optional "task_goal_summary", and "tasks".',
            'Each task must contain "task_id", "objective", "required_signals", "acceptance_criteria", "operating_regime", "grounded_components", "grounded_component_types", and "grounded_ports".',
        ],
        validity_rules=[
            "Do not invent components, component types, ports, or signals outside the provided MBSE context.",
            "Every task objective must support the given requirement, not a different engineering goal.",
            "If a field cannot be grounded to the MBSE context, return an empty list or empty object for that field.",
            "Acceptance criteria may only contain metrics that are explicit in the requirement or directly tied to grounded signals.",
        ],
    )
    allowed_entities = {
        "components": [component.name for component in mbse_context.components],
        "component_types": unique_strings(component.component_type for component in mbse_context.components),
        "signals": unique_strings(port.name for component in mbse_context.components for port in component.ports),
        "ports": unique_strings(port.qualified_name or port.name for component in mbse_context.components for port in component.ports),
    }
    user_prompt = json.dumps(
        {
            "current_task_goal": task_goal,
            "requirement": requirement,
            "mbse_context": _mbse_summary(mbse_context),
            "allowed_entities": allowed_entities,
            "max_task_sets": max(1, min(int(max_candidates), 4)),
        },
        ensure_ascii=False,
    )
    raw = chat_json(system_prompt, user_prompt, temperature=0.35, max_tokens=1600)
    if not isinstance(raw, dict):
        return []
    goal_summary = str(raw.get("task_goal_summary") or "").strip()
    if not _goal_matches_requirement(goal_summary, requirement):
        return []
    task_sets_raw = raw.get("task_sets")
    if not isinstance(task_sets_raw, list):
        return []

    component_aliases = _build_alias_map(*([component.name] for component in mbse_context.components))
    component_type_aliases = _build_alias_map(*([component.component_type] for component in mbse_context.components))
    signal_aliases = _build_alias_map(
        *([port.name, port.qualified_name] for component in mbse_context.components for port in component.ports)
    )
    port_aliases = _build_alias_map(
        *([port.name, port.qualified_name] for component in mbse_context.components for port in component.ports)
    )
    output: List[TaskSet] = []
    for set_index, raw_set in enumerate(task_sets_raw[: max(int(max_candidates), 1)]):
        if not isinstance(raw_set, dict):
            continue
        set_goal_summary = str(raw_set.get("task_goal_summary") or goal_summary).strip()
        if not _goal_matches_requirement(set_goal_summary, requirement):
            continue
        raw_tasks = raw_set.get("tasks")
        if not isinstance(raw_tasks, list):
            continue
        tasks: List[VerificationTask] = []
        for task_index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, dict):
                continue
            criteria = [
                criterion
                for criterion in (_criterion_from_raw(item) for item in raw_task.get("acceptance_criteria", []))
                if criterion is not None
            ]
            required_signals = _sanitize_name_list(raw_task.get("required_signals", []), signal_aliases)
            grounded_components = _sanitize_name_list(raw_task.get("grounded_components", []), component_aliases)
            grounded_component_types = _sanitize_name_list(raw_task.get("grounded_component_types", []), component_type_aliases)
            grounded_ports = _sanitize_name_list(raw_task.get("grounded_ports", []), port_aliases)
            operating_regime = _regime_from_raw(raw_task.get("operating_regime", {}))
            if not (required_signals or grounded_components or grounded_component_types or grounded_ports or criteria or operating_regime):
                continue
            tasks.append(
                VerificationTask(
                    task_id=str(raw_task.get("task_id") or f"task_llm_{set_index}_{task_index}"),
                    objective=_sanitize_objective(raw_task.get("objective"), requirement),
                    required_signals=required_signals,
                    acceptance_criteria=criteria,
                    operating_regime=operating_regime,
                    grounded_components=grounded_components,
                    grounded_component_types=grounded_component_types,
                    grounded_ports=grounded_ports,
                    diagnostics={
                        "generation_source": "llm_raw",
                        "generation_family": "llm",
                        "task_goal_summary": set_goal_summary,
                        "llm_sanitized": True,
                    },
                )
            )
        if tasks:
            output.append(
                TaskSet(
                    tasks=tasks,
                    rationale=str(raw_set.get("rationale") or "llm-generated raw task set")[:240],
                    generation_source="llm_raw",
                    grounding_status="raw",
                    meta={
                        "generation_source": "llm_raw",
                        "generation_family": "llm",
                        "task_goal_summary": set_goal_summary,
                        "llm_sanitized": True,
                    },
                )
            )
    return output


def _generate_raw_tasksets_via_rules(requirement: str, mbse_context: MBSEContext) -> List[TaskSet]:
    criteria = _extract_acceptance_criteria(requirement)
    regime = _extract_operating_regime(requirement)
    explicit_signals = _explicit_requirement_signals(requirement, mbse_context)
    mentioned_signals = _mentioned_signals(requirement, mbse_context)
    all_signals = _unique_preserve(port.name for component in mbse_context.components for port in component.ports)
    active_signals = explicit_signals or mentioned_signals or all_signals
    output: List[TaskSet] = []

    taskset_tasks: List[VerificationTask] = []
    relevant_components = [
        component
        for component in mbse_context.components
        if _component_is_mentioned(component.name, component.component_type, requirement)
    ]
    component_pool = relevant_components or list(mbse_context.components)
    for index, component in enumerate(component_pool):
        component_port_names = [port.name for port in component.ports]
        component_signals = (
            list(explicit_signals)
            or [port.name for port in component.ports if not active_signals or port.name in active_signals]
            or component_port_names
        )
        taskset_tasks.append(
            VerificationTask(
                task_id=f"task_component_{index}",
                objective=f"Verify {component.component_type} behavior for requirement: {_global_objective(requirement)}",
                required_signals=component_signals,
                acceptance_criteria=list(criteria),
                operating_regime=regime,
                grounded_components=[component.name],
                grounded_component_types=[component.component_type],
                grounded_ports=component_signals,
                diagnostics={"generation_source": "rules_component", "generation_family": "rules"},
            )
        )
    if taskset_tasks:
        output.append(
            TaskSet(
                tasks=taskset_tasks,
                rationale="rule-generated component-aligned raw task set",
                generation_source="rules_component",
                grounding_status="raw",
                meta={"generation_source": "rules_component", "generation_family": "rules"},
            )
        )

    if mbse_context.connections:
        connection_tasks: List[VerificationTask] = []
        for index, connection in enumerate(mbse_context.connections):
            connection_tasks.append(
                VerificationTask(
                    task_id=f"task_connection_{index}",
                    objective=f"Verify transfer from {connection.source_component} to {connection.target_component}",
                    required_signals=_unique_preserve([connection.source_signal, connection.target_signal]),
                    acceptance_criteria=list(criteria),
                    operating_regime=regime,
                    grounded_components=_unique_preserve([connection.source_component, connection.target_component]),
                    grounded_ports=_unique_preserve([connection.source_signal, connection.target_signal]),
                    diagnostics={"generation_source": "rules_connection", "generation_family": "rules"},
                )
            )
        output.append(
            TaskSet(
                tasks=connection_tasks,
                rationale="rule-generated connection-aligned raw task set",
                generation_source="rules_connection",
                grounding_status="raw",
                meta={"generation_source": "rules_connection", "generation_family": "rules"},
            )
        )

    output.append(
        TaskSet(
            tasks=[
                VerificationTask(
                    task_id="task_monolithic",
                    objective=_global_objective(requirement),
                    required_signals=active_signals[: max(len(active_signals), 1)],
                    acceptance_criteria=list(criteria),
                    operating_regime=regime,
                    grounded_components=[component.name for component in mbse_context.components],
                    grounded_component_types=[component.component_type for component in mbse_context.components],
                    grounded_ports=active_signals,
                    diagnostics={"generation_source": "rules_monolithic", "generation_family": "rules"},
                )
            ],
            rationale="rule-generated holistic raw task set",
            generation_source="rules_monolithic",
            grounding_status="raw",
            meta={"generation_source": "rules_monolithic", "generation_family": "rules"},
        )
    )
    return output


def _task_signature(taskset: TaskSet) -> Tuple[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]:
    task_ids = tuple(sorted(task.task_id for task in taskset.tasks))
    task_shapes = tuple(
        sorted(
            (
                tuple(sorted(task.grounded_components)),
                tuple(sorted(task.required_signals)),
                task.objective,
            )
            for task in taskset.tasks
        )
    )
    return task_ids, task_shapes


def _generation_family(generation_source: str) -> str:
    return "llm" if str(generation_source or "").startswith("llm") else "rules"


def _calibration_artifact_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "stage1_calibration.json"


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def decompose(
    requirement: str,
    *,
    mbse_context: MBSEContext,
    confidence: float = 0.9,
    max_candidates: int = 6,
) -> List[TaskSet]:
    text = (requirement or "").strip()
    raw_candidates = _generate_raw_tasksets_via_rules(text, mbse_context)
    raw_candidates.extend(_generate_raw_tasksets_via_llm(text, mbse_context, max_candidates=max_candidates))

    grounded_candidates: List[TaskSet] = []
    seen: Set[Tuple[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]] = set()
    for index, raw_taskset in enumerate(raw_candidates):
        grounded = ground_taskset_to_mbse(raw_taskset, mbse_context)
        report = validate_grounded_taskset(grounded, mbse_context)
        if not report.valid:
            grounded = repair_invalid_grounding(grounded, mbse_context, max_repairs=2)
            report = validate_grounded_taskset(grounded, mbse_context)
        grounded = _enrich_grounded_taskset(grounded, text, mbse_context)
        report = validate_grounded_taskset(grounded, mbse_context)
        breakdown = compute_verifiability_score(grounded, text, mbse_context)
        grounding_status = grounded.grounding_status or ("grounded" if report.valid else "partially_grounded")
        if report.valid and grounding_status not in {"repaired", "fallback", "partially_grounded"}:
            grounding_status = "grounded"
        if not report.valid and grounding_status not in {"fallback", "partially_grounded"}:
            grounding_status = "partially_grounded"
        candidate = replace(
            grounded,
            task_set_id=f"taskset_{index}",
            generation_source=raw_taskset.generation_source or str(raw_taskset.meta.get("generation_source") or "rules"),
            grounding_status=grounding_status,
            score=float(breakdown["final_score"]),
            score_breakdown=breakdown,
            meta={
                **dict(raw_taskset.meta),
                **dict(grounded.meta),
                "generation_family": _generation_family(
                    raw_taskset.generation_source or str(raw_taskset.meta.get("generation_source") or "rules")
                ),
                "grounding_valid": report.valid,
                "grounding_errors": list(report.errors),
                "grounding_notes": list(report.notes),
            },
        )
        signature = _task_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        grounded_candidates.append(candidate)

    if not grounded_candidates:
        fallback = TaskSet(
            tasks=[
                VerificationTask(
                    task_id="task_fallback",
                    objective=_global_objective(text),
                    diagnostics={"generation_source": "fallback"},
                )
            ],
            rationale="fallback empty task set",
            task_set_id="taskset_fallback",
            generation_source="fallback",
            grounding_status="fallback",
            score=0.0,
            score_breakdown={"final_score": 0.0},
            meta={
                "generation_source": "fallback",
                "generation_family": "fallback",
                "grounding_resolution": "fallback",
                "engineering_fallback": True,
                "candidate_status": "engineering_fallback",
                "selection_semantics": "pipeline_continuity_fallback",
            },
        )
        grounded_candidates = [fallback]

    calibration_model = load_calibration_model(_calibration_artifact_path())
    selected = apply_conformal_filter(
        grounded_candidates,
        calibration_model=calibration_model,
        confidence=float(confidence),
        keep_at_least=1,
    )
    selected = [
        replace(
            taskset,
            conformal_info=dict(taskset.conformal_info)
            or {
                "threshold": None,
                "p_value_threshold": max(0.0, min(1.0, 1.0 - float(confidence))),
                "p_value": float(taskset.p_value),
                "accepted": True,
                "accepted_by": "p_value",
                "nonconformity": max(0.0, min(1.0, 1.0 - float(taskset.score))),
                "fallback_retained": False,
                "engineering_fallback": bool(taskset.meta.get("engineering_fallback")),
                "calibrated_member": not bool(taskset.meta.get("engineering_fallback")),
                "candidate_status": "engineering_fallback" if taskset.meta.get("engineering_fallback") else "calibrated_accept",
                "selection_semantics": "pipeline_continuity_fallback"
                if taskset.meta.get("engineering_fallback")
                else "calibrated_set",
                "confidence": float(confidence),
            },
            meta={
                **dict(taskset.meta),
                "p_value_threshold": dict(taskset.conformal_info).get("p_value_threshold")
                if dict(taskset.conformal_info)
                else max(0.0, min(1.0, 1.0 - float(confidence))),
                "p_value": dict(taskset.conformal_info).get("p_value") if dict(taskset.conformal_info) else float(taskset.p_value),
                "accepted": bool(
                    dict(taskset.conformal_info).get("accepted") if dict(taskset.conformal_info) else not taskset.meta.get("engineering_fallback")
                ),
                "accepted_by": dict(taskset.conformal_info).get("accepted_by")
                if dict(taskset.conformal_info)
                else ("engineering_fallback" if taskset.meta.get("engineering_fallback") else "p_value"),
                "nonconformity": dict(taskset.conformal_info).get("nonconformity")
                if dict(taskset.conformal_info)
                else max(0.0, min(1.0, 1.0 - float(taskset.score))),
                "fallback_retained": bool(
                    dict(taskset.conformal_info).get("fallback_retained") if dict(taskset.conformal_info) else False
                ),
                "candidate_status": dict(taskset.conformal_info).get("candidate_status")
                if dict(taskset.conformal_info)
                else ("engineering_fallback" if taskset.meta.get("engineering_fallback") else "calibrated_accept"),
                "selection_semantics": dict(taskset.conformal_info).get("selection_semantics")
                if dict(taskset.conformal_info)
                else ("pipeline_continuity_fallback" if taskset.meta.get("engineering_fallback") else "calibrated_set"),
                "engineering_fallback": bool(
                    dict(taskset.conformal_info).get("engineering_fallback")
                    if dict(taskset.conformal_info)
                    else taskset.meta.get("engineering_fallback")
                ),
                "calibrated_member": bool(
                    dict(taskset.conformal_info).get("calibrated_member")
                    if dict(taskset.conformal_info)
                    else not taskset.meta.get("engineering_fallback")
                ),
            },
        )
        for taskset in selected
    ]
    return selected[: max(int(max_candidates), 1)]
