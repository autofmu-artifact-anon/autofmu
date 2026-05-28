"""Grounding helpers for Stage 1 task decomposition."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Sequence, Set, Tuple

from pipeline.types import MBSEContext, TaskSet, VerificationTask


@dataclass(frozen=True)
class GroundingReport:
    valid: bool
    errors: List[str]
    notes: List[str]


_GENERIC_PORT_NAMES = frozenset({"input", "inputs", "output", "outputs"})


def ground_taskset_to_mbse(raw_taskset: TaskSet, mbse_context: MBSEContext) -> TaskSet:
    component_index = {component.name: component for component in mbse_context.components}
    component_norm = {_normalize(component.name): component.name for component in mbse_context.components}
    signal_norm, signal_to_components, _, component_port_names = _build_signal_indexes(mbse_context)

    tasks: List[VerificationTask] = []
    for index, task in enumerate(raw_taskset.tasks):
        notes: List[str] = []
        requested_signals = _unique(task.required_signals or task.grounded_ports)
        grounded_signals = _match_signals(requested_signals, signal_norm)
        components = _match_components(task.grounded_components, component_index, component_norm)
        had_explicit_components = bool(components)
        if grounded_signals:
            owners = _signal_owner_components(grounded_signals, signal_to_components)
            if not components and owners:
                components = owners
                notes.append("components_inferred_from_signal_owners")
            elif components:
                supported_components = [
                    name
                    for name in components
                    if any(name in signal_to_components.get(signal_name, set()) for signal_name in grounded_signals)
                ]
                if supported_components:
                    if len(supported_components) != len(components):
                        notes.append("dropped_components_without_signal_support")
                    components = _unique(supported_components)
                elif owners:
                    notes.append("retained_explicit_components_despite_signal_alias_overlap")
            if components:
                supported_signals = [
                    signal_name
                    for signal_name in grounded_signals
                    if any(component_name in signal_to_components.get(signal_name, set()) for component_name in components)
                ]
                if supported_signals:
                    if len(supported_signals) != len(grounded_signals):
                        notes.append("dropped_signals_without_component_support")
                    grounded_signals = _unique(supported_signals)
                elif had_explicit_components:
                    notes.append("retained_explicit_components_without_supported_signals")
        if not components:
            inferred_components, component_notes = _suggest_components_for_task(task, mbse_context)
            if inferred_components:
                components = inferred_components
            notes.extend(component_notes)
        retained_requirement_signals = [
            signal_name
            for signal_name in requested_signals
            if signal_name not in grounded_signals
            and _allow_requirement_signal_without_exact_port(signal_name, components, component_port_names)
        ]
        if retained_requirement_signals:
            grounded_signals = _unique(list(grounded_signals) + list(retained_requirement_signals))
            notes.append("retained_requirement_signals_without_exact_mbse_port")
        if not grounded_signals and components:
            inferred_signals, signal_notes = _suggest_signals_for_task(task, mbse_context, components)
            grounded_signals = inferred_signals
            notes.extend(signal_notes)
        component_types = _unique(
            component_index[name].component_type
            for name in components
            if name in component_index
        )
        grounded_ports = _unique(
            signal
            for signal in grounded_signals
            if not components
            or any(signal in {port.name for port in component_index[name].ports} for name in components if name in component_index)
        )
        supporting_connections = [
            {
                "source_component": connection.source_component,
                "source_signal": connection.source_signal,
                "target_component": connection.target_component,
                "target_signal": connection.target_signal,
            }
            for connection in mbse_context.connections
            if connection.source_component in components
            or connection.target_component in components
            or connection.source_signal in grounded_signals
            or connection.target_signal in grounded_signals
        ]
        tasks.append(
            replace(
                task,
                task_id=task.task_id or f"task_grounded_{index}",
                grounded_components=components,
                grounded_component_types=component_types,
                required_signals=grounded_signals,
                grounded_ports=list(grounded_ports or grounded_signals),
                task_trace={
                    "components": list(components),
                    "ports": list(grounded_ports or grounded_signals),
                    "signals": list(grounded_signals),
                    "connections": supporting_connections,
                    "notes": ["grounded_to_mbse", *notes],
                },
                diagnostics={
                    **dict(task.diagnostics),
                    "grounded": bool(components or grounded_signals),
                    "grounded_component_count": len(components),
                    "grounded_signal_count": len(grounded_signals),
                    "retained_requirement_signals_without_exact_mbse_port": bool(retained_requirement_signals),
                    "retained_requirement_signals": list(retained_requirement_signals),
                    "grounding_notes": list(notes),
                },
            )
        )
    return replace(raw_taskset, tasks=tasks)


def validate_grounded_taskset(taskset: TaskSet, mbse_context: MBSEContext) -> GroundingReport:
    component_names = {component.name for component in mbse_context.components}
    signal_norm, signal_owners, component_port_aliases, component_port_names = _build_signal_indexes(mbse_context)
    signal_names = set(signal_owners)
    connection_keys = {
        (
            connection.source_component,
            connection.source_signal,
            connection.target_component,
            connection.target_signal,
        )
        for connection in mbse_context.connections
    }
    errors: List[str] = []
    notes: List[str] = []
    if not taskset.tasks:
        errors.append("empty_task_set")
    for task in taskset.tasks:
        if not task.objective.strip():
            errors.append(f"{task.task_id}:empty_objective")
        bad_components = [name for name in task.grounded_components if name not in component_names]
        if bad_components:
            errors.append(f"{task.task_id}:unknown_components={bad_components}")
        bad_signals = [
            name
            for name in task.required_signals
            if _normalize(name) not in signal_norm
            and not _allow_requirement_signal_without_exact_port(name, task.grounded_components, component_port_names)
        ]
        if bad_signals:
            errors.append(f"{task.task_id}:unknown_signals={bad_signals}")
        if not task.grounded_components and not task.required_signals:
            errors.append(f"{task.task_id}:ungrounded_task")
        if task.grounded_components and task.required_signals:
            notes.append(f"{task.task_id}:component_signal_grounded")
            unsupported_signals = [
                signal_name
                for signal_name in task.required_signals
                if not _signal_supported_by_components(
                    signal_name,
                    task.grounded_components,
                    signal_owners,
                    component_port_names=component_port_names,
                )
            ]
            if unsupported_signals:
                errors.append(f"{task.task_id}:signals_not_owned_by_grounded_components={unsupported_signals}")
        for spec in task.signal_specs:
            if spec.grounded_component_ref and spec.grounded_component_ref not in component_names:
                errors.append(f"{task.task_id}:unknown_signal_component_ref={spec.grounded_component_ref}")
            if spec.grounded_port_ref and _normalize(spec.grounded_port_ref) not in signal_norm:
                errors.append(f"{task.task_id}:unknown_signal_port_ref={spec.grounded_port_ref}")
            if spec.grounded_component_ref and spec.grounded_port_ref:
                port_aliases = component_port_aliases.get(spec.grounded_component_ref, set())
                if _normalize(spec.grounded_port_ref) not in port_aliases:
                    errors.append(
                        f"{task.task_id}:signal_port_not_on_component={spec.grounded_component_ref}.{spec.grounded_port_ref}"
                    )
            if spec.signal_name and spec.grounded_component_ref and not _signal_supported_by_components(
                spec.signal_name,
                [spec.grounded_component_ref],
                signal_owners,
                component_port_names=component_port_names,
            ):
                errors.append(f"{task.task_id}:signal_spec_not_owned_by_component={spec.signal_name}")
            if spec.signal_name and not spec.grounded_component_ref and not spec.grounded_port_ref:
                notes.append(f"{task.task_id}:partial_signal_spec={spec.signal_name}")
        for constraint in task.constraint_set:
            if constraint.grounded_signal and _normalize(constraint.grounded_signal) not in signal_norm:
                errors.append(f"{task.task_id}:unknown_constraint_signal={constraint.grounded_signal}")
            if constraint.grounded_component_ref and constraint.grounded_component_ref not in component_names:
                errors.append(f"{task.task_id}:unknown_constraint_component_ref={constraint.grounded_component_ref}")
            if constraint.grounded_port_ref and _normalize(constraint.grounded_port_ref) not in signal_norm:
                errors.append(f"{task.task_id}:unknown_constraint_port_ref={constraint.grounded_port_ref}")
            if constraint.grounded_component_ref and constraint.grounded_port_ref:
                port_aliases = component_port_aliases.get(constraint.grounded_component_ref, set())
                if _normalize(constraint.grounded_port_ref) not in port_aliases:
                    errors.append(
                        f"{task.task_id}:constraint_port_not_on_component={constraint.grounded_component_ref}.{constraint.grounded_port_ref}"
                    )
            if constraint.grounded_signal and constraint.grounded_component_ref and not _signal_supported_by_components(
                constraint.grounded_signal,
                [constraint.grounded_component_ref],
                signal_owners,
                component_port_names=component_port_names,
            ):
                errors.append(f"{task.task_id}:constraint_signal_not_owned_by_component={constraint.grounded_signal}")
            if constraint.metric and not constraint.grounded_component_ref and not constraint.grounded_port_ref:
                notes.append(f"{task.task_id}:partial_constraint_ref={constraint.metric}")
    for chain in taskset.required_signal_chains:
        if not chain.segments:
            errors.append(f"{chain.chain_id}:empty_chain")
            continue
        for segment in chain.segments:
            if segment.source_component not in component_names:
                errors.append(f"{chain.chain_id}:{segment.segment_id}:unknown_source_component={segment.source_component}")
            if segment.target_component not in component_names:
                errors.append(f"{chain.chain_id}:{segment.segment_id}:unknown_target_component={segment.target_component}")
            if segment.source_signal and segment.source_signal not in signal_names:
                errors.append(f"{chain.chain_id}:{segment.segment_id}:unknown_source_signal={segment.source_signal}")
            if segment.target_signal and segment.target_signal not in signal_names:
                errors.append(f"{chain.chain_id}:{segment.segment_id}:unknown_target_signal={segment.target_signal}")
            connection_key = (
                segment.source_component,
                segment.source_signal,
                segment.target_component,
                segment.target_signal,
            )
            if all(connection_key) and connection_key not in connection_keys:
                errors.append(f"{chain.chain_id}:{segment.segment_id}:missing_mbse_connection={connection_key}")
    return GroundingReport(valid=not errors, errors=errors, notes=notes)


def repair_invalid_grounding(raw_taskset: TaskSet, mbse_context: MBSEContext, max_repairs: int = 2) -> TaskSet:
    current = raw_taskset
    repair_attempted = False
    for _ in range(max(int(max_repairs), 0) + 1):
        repaired_tasks: List[VerificationTask] = []
        fallback_unresolved = True
        for task in current.tasks:
            components, component_notes = _suggest_components_for_task(task, mbse_context)
            signals, signal_notes = _suggest_signals_for_task(task, mbse_context, components)
            notes = list(component_notes) + list(signal_notes)
            if components or signals:
                fallback_unresolved = False
            repair_attempted = True
            repaired_tasks.append(
                replace(
                    task,
                    grounded_components=list(components),
                    required_signals=list(signals),
                    grounded_ports=list(signals),
                    diagnostics={
                        **dict(task.diagnostics),
                        "repair_attempted": True,
                        "repair_notes": list(notes),
                        "repair_fallback_unresolved": not components and not signals,
                    },
                )
            )
        grounded = ground_taskset_to_mbse(replace(current, tasks=repaired_tasks), mbse_context)
        report = validate_grounded_taskset(grounded, mbse_context)
        if report.valid:
            effective_grounding = all(task.grounded_components or task.required_signals for task in grounded.tasks)
            status = "repaired" if repair_attempted and effective_grounding else ("grounded" if effective_grounding else "partially_grounded")
            return replace(
                grounded,
                grounding_status=status,
                meta={
                    **dict(grounded.meta),
                    "repair_attempted": repair_attempted,
                    "repair_unresolved": False,
                },
            )
        current = replace(
            grounded,
            grounding_status="fallback" if fallback_unresolved else "partially_grounded",
            meta={
                **dict(grounded.meta),
                "repair_errors": list(report.errors),
                "repair_notes": list(report.notes),
                "repair_attempted": repair_attempted,
                "repair_unresolved": fallback_unresolved,
            },
        )
    return current


def _match_components(names: Sequence[str], component_index: Dict[str, object], component_norm: Dict[str, str]) -> List[str]:
    matched: List[str] = []
    for name in names:
        if name in component_index:
            matched.append(name)
            continue
        norm = _normalize(name)
        if norm in component_norm:
            matched.append(component_norm[norm])
    return _unique(matched)


def _match_signals(names: Sequence[str], signal_norm: Dict[str, str]) -> List[str]:
    matched: List[str] = []
    for name in names:
        norm = _normalize(name)
        if norm in signal_norm:
            matched.append(signal_norm[norm])
    return _unique(matched)


def _normalize(text: str) -> str:
    pieces: List[str] = []
    token: List[str] = []
    prev_lower = False
    for ch in text or "":
        if ch.isalnum():
            if ch.isupper() and prev_lower and token:
                pieces.append("".join(token).lower())
                token = [ch]
            else:
                token.append(ch)
            prev_lower = ch.islower()
        else:
            if token:
                pieces.append("".join(token).lower())
                token = []
            prev_lower = False
    if token:
        pieces.append("".join(token).lower())
    return " ".join(pieces)


def _text_tokens(text: str) -> Set[str]:
    return {token for token in _normalize(text).split() if token}


def _task_tokens(task: VerificationTask) -> Set[str]:
    tokens = set(_text_tokens(task.objective))
    for signal_name in list(task.required_signals) + list(task.grounded_ports):
        tokens.update(_text_tokens(signal_name))
    for criterion in task.acceptance_criteria:
        tokens.update(_text_tokens(criterion.metric))
    if task.operating_regime is not None:
        for name in task.operating_regime.inputs:
            tokens.update(_text_tokens(name))
        for name in task.operating_regime.initial_conditions:
            tokens.update(_text_tokens(name))
        for assumption in task.operating_regime.assumptions:
            tokens.update(_text_tokens(assumption))
    return tokens


def _suggest_components_for_task(task: VerificationTask, mbse_context: MBSEContext) -> Tuple[List[str], List[str]]:
    component_index = {component.name: component for component in mbse_context.components}
    signal_norm, signal_to_components, _, _ = _build_signal_indexes(mbse_context)

    valid_components = [name for name in task.grounded_components if name in component_index]
    type_hints = {_normalize(value) for value in task.grounded_component_types if _normalize(value)}
    if type_hints:
        matched_by_type = _unique(
            component.name
            for component in mbse_context.components
            if _normalize(component.component_type) in type_hints
        )
        if matched_by_type:
            return matched_by_type, ["repair_components_from_component_types"]
    valid_signals = _task_signal_hints(task, signal_norm)
    notes: List[str] = []
    owner_components = _unique(
        component_name
        for signal_name in valid_signals
        for component_name in sorted(signal_to_components.get(signal_name, set()))
    )
    if owner_components:
        supported_valid_components = [
            name
            for name in valid_components
            if any(name in signal_to_components.get(signal_name, set()) for signal_name in valid_signals)
        ]
        if supported_valid_components:
            notes.append("repair_components_from_signal_owners")
            return _unique(supported_valid_components + [name for name in owner_components if name not in supported_valid_components]), notes
        notes.append("repair_reassigned_components_to_signal_owners")
        return owner_components, notes
    if valid_components:
        notes.append("repair_components_from_existing_refs")
        return _unique(valid_components), notes

    task_tokens = _task_tokens(task)
    ranked: List[Tuple[int, str]] = []
    for component in mbse_context.components:
        component_tokens = _text_tokens(component.name) | _text_tokens(component.component_type)
        component_tokens.update(token for port in component.ports for token in _text_tokens(port.name))
        overlap = len(task_tokens & component_tokens)
        if overlap > 0:
            ranked.append((overlap, component.name))
    if ranked:
        ranked.sort(key=lambda item: (-item[0], item[1]))
        notes.append("repair_components_from_text_overlap")
        best_score = ranked[0][0]
        return _unique(name for score, name in ranked if score == best_score), notes
    return [], notes


def _suggest_signals_for_task(task: VerificationTask, mbse_context: MBSEContext, components: Sequence[str]) -> Tuple[List[str], List[str]]:
    component_index = {component.name: component for component in mbse_context.components}
    signal_norm, signal_owners, _, _ = _build_signal_indexes(mbse_context)

    allowed_components = {name for name in components if name in component_index}
    notes: List[str] = []

    valid_signals = [
        signal_name
        for signal_name in _match_signals(list(task.required_signals) + list(task.grounded_ports), signal_norm)
        if signal_name in signal_owners
        and (not allowed_components or not signal_owners[signal_name].isdisjoint(allowed_components))
    ]
    if valid_signals:
        notes.append("repair_signals_from_existing_refs")
        return valid_signals, notes

    metric_signals = [
        signal_norm[_normalize(criterion.metric)]
        for criterion in task.acceptance_criteria
        if _normalize(criterion.metric) in signal_norm
        and signal_norm[_normalize(criterion.metric)] in signal_owners
        and (not allowed_components or not signal_owners[signal_norm[_normalize(criterion.metric)]].isdisjoint(allowed_components))
    ]
    if metric_signals:
        notes.append("repair_signals_from_acceptance_metrics")
        return _unique(metric_signals), notes

    task_tokens = _task_tokens(task)
    ranked: List[Tuple[int, str]] = []
    for component_name in allowed_components:
        component = component_index[component_name]
        for port in component.ports:
            overlap = len(task_tokens & (_text_tokens(port.name) | _text_tokens(port.qualified_name)))
            if overlap > 0:
                ranked.append((overlap, port.name))
    if ranked:
        ranked.sort(key=lambda item: (-item[0], item[1]))
        notes.append("repair_signals_from_text_overlap")
        best_score = ranked[0][0]
        return _unique(name for score, name in ranked if score == best_score), notes
    if len(allowed_components) == 1:
        component = component_index[next(iter(allowed_components))]
        if len(component.ports) == 1:
            notes.append("repair_signals_from_single_port_component")
            return [component.ports[0].name], notes

    connection_signals = _unique(
        signal_name
        for connection in mbse_context.connections
        for signal_name in (connection.source_signal, connection.target_signal)
        if connection.source_component in allowed_components or connection.target_component in allowed_components
    )
    if connection_signals:
        notes.append("repair_signals_from_local_connections")
        return connection_signals, notes
    return [], notes


def _task_signal_hints(task: VerificationTask, signal_norm: Dict[str, str]) -> List[str]:
    direct_hints = [
        signal_norm[_normalize(signal_name)]
        for signal_name in _unique(list(task.required_signals) + list(task.grounded_ports))
        if _normalize(signal_name) in signal_norm
    ]
    metric_hints = [
        signal_norm[_normalize(criterion.metric)]
        for criterion in task.acceptance_criteria
        if _normalize(criterion.metric) in signal_norm
    ]
    return _unique(direct_hints + metric_hints)
def _build_signal_indexes(
    mbse_context: MBSEContext,
) -> Tuple[Dict[str, str], Dict[str, Set[str]], Dict[str, Set[str]], Dict[str, Set[str]]]:
    signal_norm: Dict[str, str] = {}
    signal_owners: Dict[str, Set[str]] = {}
    component_port_aliases: Dict[str, Set[str]] = {}
    component_port_names: Dict[str, Set[str]] = {}
    for component in mbse_context.components:
        port_aliases = component_port_aliases.setdefault(component.name, set())
        raw_port_names = component_port_names.setdefault(component.name, set())
        for port in component.ports:
            canonical = port.name
            signal_owners.setdefault(canonical, set()).add(component.name)
            raw_port_names.add(canonical)
            aliases = [port.name, port.qualified_name or "", f"{component.name}.{port.name}"]
            for alias in aliases:
                norm = _normalize(alias)
                if not norm:
                    continue
                signal_norm.setdefault(norm, canonical)
                port_aliases.add(norm)
    return signal_norm, signal_owners, component_port_aliases, component_port_names


def _signal_owner_components(signal_names: Sequence[str], signal_owners: Dict[str, Set[str]]) -> List[str]:
    return _unique(
        component_name
        for signal_name in signal_names
        for component_name in sorted(signal_owners.get(signal_name, set()))
    )


def _signal_supported_by_components(
    signal_name: str,
    component_names: Sequence[str],
    signal_owners: Dict[str, Set[str]],
    *,
    component_port_names: Dict[str, Set[str]] | None = None,
) -> bool:
    owners = signal_owners.get(signal_name)
    if owners is None:
        if component_port_names and _allow_requirement_signal_without_exact_port(
            signal_name,
            component_names,
            component_port_names,
        ):
            return True
        return False
    return not owners.isdisjoint({name for name in component_names if name})


def _is_generic_port_name(name: str) -> bool:
    return _normalize(name) in _GENERIC_PORT_NAMES


def _allow_requirement_signal_without_exact_port(
    signal_name: str,
    component_names: Sequence[str],
    component_port_names: Dict[str, Set[str]],
) -> bool:
    if not signal_name:
        return False
    relevant_ports = [
        port_name
        for component_name in component_names
        for port_name in component_port_names.get(component_name, set())
        if port_name
    ]
    if not relevant_ports or not all(_is_generic_port_name(port_name) for port_name in relevant_ports):
        return False
    if _is_generic_port_name(signal_name):
        return _normalize(signal_name) not in {_normalize(port_name) for port_name in relevant_ports}
    return True


def _unique(items) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
