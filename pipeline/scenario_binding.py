"""Helpers for binding scenario inputs and initial conditions to FMU endpoints."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .types import FMU


def _ordered_unique_text(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _normalize_token(text: Any) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def _candidate_signal_names(name: str) -> List[str]:
    text = str(name or "").strip()
    out = [text]
    if text.endswith("_profile"):
        out.append(text[: -len("_profile")])
    return _ordered_unique_text(out)


def _signal_aliases(
    signal_name: str,
    *,
    verification_requirement_payload: Mapping[str, Any] | None = None,
) -> List[str]:
    verification = verification_requirement_payload if isinstance(verification_requirement_payload, Mapping) else {}
    aliases = verification.get("signal_aliases") if isinstance(verification.get("signal_aliases"), Mapping) else {}
    return _ordered_unique_text(
        [signal_name]
        + list(aliases.get(signal_name, []) if isinstance(aliases.get(signal_name), list) else [])
    )


def _split_endpoint(endpoint: str) -> Tuple[str, str]:
    asset_id, _, signal_name = str(endpoint or "").partition(".")
    return asset_id.strip(), signal_name.strip()


def _fmu_matches_component_hint(fmu: FMU, component_hint: str) -> bool:
    hint_norm = _normalize_token(component_hint)
    if not hint_norm:
        return False
    candidates = [
        getattr(fmu, "uid", ""),
        getattr(fmu, "name", ""),
        *list(getattr(fmu, "tags", []) or []),
    ]
    return any(hint_norm in _normalize_token(candidate) for candidate in candidates if str(candidate).strip())


def _port_causality_map(selected_fmus: Sequence[FMU]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for fmu in selected_fmus:
        asset_id = str(getattr(fmu, "uid", "")).strip()
        if not asset_id:
            continue
        if getattr(fmu, "ports", None):
            for port in getattr(fmu, "ports", []):
                signal_name = str(getattr(port, "name", "")).strip()
                if not signal_name:
                    continue
                mapping[f"{asset_id}.{signal_name}"] = str(getattr(port, "causality", "") or "").strip().lower()
        else:
            for signal_name in getattr(fmu, "inputs", []):
                text = str(signal_name or "").strip()
                if text:
                    mapping[f"{asset_id}.{text}"] = "input"
            for signal_name in getattr(fmu, "outputs", []):
                text = str(signal_name or "").strip()
                if text:
                    mapping[f"{asset_id}.{text}"] = "output"
    return mapping


def _endpoint_candidates(
    *,
    selected_fmus: Sequence[FMU],
    signal_candidates: Sequence[str],
    allowed_causalities: Sequence[str],
) -> List[str]:
    allowed = {str(item).strip().lower() for item in allowed_causalities if str(item).strip()}
    causality_map = _port_causality_map(selected_fmus)
    out: List[str] = []
    for endpoint, causality in causality_map.items():
        asset_id, signal_name = _split_endpoint(endpoint)
        del asset_id
        if allowed and causality not in allowed:
            continue
        if signal_name in signal_candidates:
            out.append(endpoint)
    return _ordered_unique_text(out)


def _task_level_component_hints(selected_task_set: Any, signal_candidates: Sequence[str], *, role: str | None) -> List[str]:
    hints: List[str] = []
    role_norm = str(role or "").strip().lower()
    for task in getattr(selected_task_set, "tasks", []) or []:
        for spec in getattr(task, "signal_specs", []) or []:
            spec_name = str(getattr(spec, "signal_name", "") or "").strip()
            source_text = str(getattr(spec, "source_text", "") or "").strip()
            if spec_name not in signal_candidates and source_text not in signal_candidates:
                continue
            spec_role = str(getattr(spec, "role", "") or "").strip().lower()
            direction = str(getattr(spec, "direction", "") or "").strip().lower()
            if role_norm == "driven" and spec_role and spec_role != "driven" and direction not in {"in", "input"}:
                continue
            if role_norm == "observed" and spec_role and spec_role != "observed" and direction not in {"out", "output"}:
                continue
            for candidate in (
                getattr(spec, "grounded_component_ref", ""),
                getattr(spec, "component_hint", ""),
            ):
                text = str(candidate or "").strip()
                if text:
                    hints.append(text)
    return _ordered_unique_text(hints)


def _resolve_targets_for_signal(
    *,
    signal_name: str,
    selected_fmus: Sequence[FMU],
    selected_task_set: Any,
    verification_requirement_payload: Mapping[str, Any] | None = None,
    allowed_causalities: Sequence[str],
    preferred_role: str | None = None,
) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    signal_candidates = _candidate_signal_names(signal_name)
    qualified_aliases = [
        alias
        for candidate in signal_candidates
        for alias in _signal_aliases(candidate, verification_requirement_payload=verification_requirement_payload)
        if "." in str(alias or "")
    ]
    direct_targets = [
        alias
        for alias in qualified_aliases
        if alias in _endpoint_candidates(
            selected_fmus=selected_fmus,
            signal_candidates=[_split_endpoint(alias)[1]],
            allowed_causalities=allowed_causalities,
        )
    ]
    if len(_ordered_unique_text(direct_targets)) == 1:
        return _ordered_unique_text(direct_targets), warnings

    endpoint_candidates = _endpoint_candidates(
        selected_fmus=selected_fmus,
        signal_candidates=signal_candidates,
        allowed_causalities=allowed_causalities,
    )
    if len(endpoint_candidates) <= 1:
        return endpoint_candidates, warnings

    component_hints = _task_level_component_hints(
        selected_task_set,
        signal_candidates,
        role=preferred_role,
    )
    if component_hints:
        hinted = [
            endpoint
            for endpoint in endpoint_candidates
            if any(
                _fmu_matches_component_hint(
                    next(
                        fmu for fmu in selected_fmus if str(getattr(fmu, "uid", "")).strip() == _split_endpoint(endpoint)[0]
                    ),
                    hint,
                )
                for hint in component_hints
            )
        ]
        hinted = _ordered_unique_text(hinted)
        if len(hinted) == 1:
            return hinted, warnings
        if len(hinted) > 1:
            endpoint_candidates = hinted

    if len(endpoint_candidates) > 1:
        warnings.append(f"ambiguous_scenario_binding:{signal_name}:{','.join(endpoint_candidates)}")
        return [], warnings
    return endpoint_candidates, warnings


def build_external_input_bindings(
    *,
    selected_fmus: Sequence[FMU],
    selected_task_set: Any,
    scenario_inputs: Mapping[str, Any] | None,
    verification_requirement_payload: Mapping[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    bindings: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for raw_name in (scenario_inputs or {}).keys():
        targets, item_warnings = _resolve_targets_for_signal(
            signal_name=str(raw_name),
            selected_fmus=selected_fmus,
            selected_task_set=selected_task_set,
            verification_requirement_payload=verification_requirement_payload,
            allowed_causalities=("input",),
            preferred_role="driven",
        )
        warnings.extend(item_warnings)
        bindings.append(
            {
                "name": _candidate_signal_names(str(raw_name))[ -1 ],
                "targets": list(targets),
                "default": None,
            }
        )
    return bindings, _ordered_unique_text(warnings)


def build_initial_condition_bindings(
    *,
    selected_fmus: Sequence[FMU],
    selected_task_set: Any,
    initial_conditions: Mapping[str, Any] | None,
    verification_requirement_payload: Mapping[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    bindings: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for raw_name in (initial_conditions or {}).keys():
        targets, item_warnings = _resolve_targets_for_signal(
            signal_name=str(raw_name),
            selected_fmus=selected_fmus,
            selected_task_set=selected_task_set,
            verification_requirement_payload=verification_requirement_payload,
            allowed_causalities=("input", "output"),
            preferred_role=None,
        )
        warnings.extend(item_warnings)
        bindings.append({"name": str(raw_name).strip(), "targets": list(targets)})
    return bindings, _ordered_unique_text(warnings)


def derive_execution_order(*, selected_fmus: Sequence[FMU], selected_task_set: Any) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for task in getattr(selected_task_set, "tasks", []) or []:
        hints = _ordered_unique_text(
            list(getattr(task, "grounded_components", []) or [])
            + list(getattr(task, "grounded_component_types", []) or [])
            + [
                str(getattr(spec, "grounded_component_ref", "") or "").strip()
                for spec in getattr(task, "signal_specs", []) or []
            ]
            + [
                str(getattr(spec, "component_hint", "") or "").strip()
                for spec in getattr(task, "signal_specs", []) or []
            ]
        )
        matches = [
            str(getattr(fmu, "uid", "")).strip()
            for fmu in selected_fmus
            if str(getattr(fmu, "uid", "")).strip()
            and any(_fmu_matches_component_hint(fmu, hint) for hint in hints if hint)
        ]
        for asset_id in _ordered_unique_text(matches):
            if asset_id in seen:
                continue
            seen.add(asset_id)
            ordered.append(asset_id)
    for fmu in selected_fmus:
        asset_id = str(getattr(fmu, "uid", "")).strip()
        if asset_id and asset_id not in seen:
            seen.add(asset_id)
            ordered.append(asset_id)
    return ordered
