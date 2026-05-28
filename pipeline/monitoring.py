"""Helpers for building monitored output bindings from verification specs."""

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


def collect_target_signal_names(
    *,
    verification_requirement_payload: Mapping[str, Any] | None = None,
    trajectory_manifest_payload: Mapping[str, Any] | None = None,
    fallback_signals: Sequence[str] = (),
) -> List[str]:
    verification = verification_requirement_payload if isinstance(verification_requirement_payload, Mapping) else {}
    manifest = trajectory_manifest_payload if isinstance(trajectory_manifest_payload, Mapping) else {}
    criteria = verification.get("criteria") if isinstance(verification.get("criteria"), list) else []
    decision_rule = verification.get("decision_rule") if isinstance(verification.get("decision_rule"), Mapping) else {}

    criterion_signals: List[str] = []
    for item in criteria:
        if not isinstance(item, Mapping):
            continue
        for key in ("signal", "lhs_signal", "rhs_signal"):
            text = str(item.get(key) or "").strip()
            if text:
                criterion_signals.append(text)
        values = item.get("signals")
        if isinstance(values, list):
            criterion_signals.extend(str(value) for value in values)

    explicit_signals = _ordered_unique_text(
        list(manifest.get("signal_columns", []) if isinstance(manifest.get("signal_columns"), list) else [])
        + list(decision_rule.get("signals", []) if isinstance(decision_rule.get("signals"), list) else [])
        + list(verification.get("signals", []) if isinstance(verification.get("signals"), list) else [])
        + criterion_signals
    )
    if explicit_signals:
        return explicit_signals
    return _ordered_unique_text(list(fallback_signals))


def build_monitored_outputs(
    *,
    selected_fmus: Sequence[FMU],
    verification_requirement_payload: Mapping[str, Any] | None = None,
    trajectory_manifest_payload: Mapping[str, Any] | None = None,
    fallback_signals: Sequence[str] = (),
    graph_bindings: Sequence[Any] = (),
) -> Tuple[List[Dict[str, str]], List[str]]:
    target_signals = collect_target_signal_names(
        verification_requirement_payload=verification_requirement_payload,
        trajectory_manifest_payload=trajectory_manifest_payload,
        fallback_signals=fallback_signals,
    )
    endpoint_causality = _endpoint_causality_map(selected_fmus)
    output_endpoints_by_name = _output_endpoints_by_signal(selected_fmus)

    binding_sources: set[str] = set()
    for binding in graph_bindings:
        src_fmu = str(getattr(binding, "source_fmu", "") or "").strip()
        src_sig = str(getattr(binding, "source_signal", "") or "").strip()
        if src_fmu and src_sig:
            binding_sources.add(f"{src_fmu}.{src_sig}")

    monitored: List[Dict[str, str]] = []
    warnings: List[str] = []
    seen_sources: set[str] = set()

    for signal_name in target_signals:
        aliases = _signal_aliases(
            signal_name,
            verification_requirement_payload=verification_requirement_payload,
            trajectory_manifest_payload=trajectory_manifest_payload,
        )
        source, all_sources, signal_warnings = _resolve_monitored_source(
            signal_name,
            aliases=aliases,
            endpoint_causality=endpoint_causality,
            output_endpoints_by_name=output_endpoints_by_name,
            binding_sources=binding_sources,
        )
        warnings.extend(signal_warnings)
        if source:
            if source not in seen_sources:
                monitored.append({"name": signal_name, "source": source})
                seen_sources.add(source)
        elif all_sources:
            for src in all_sources:
                if src not in seen_sources:
                    monitored.append({"name": signal_name, "source": src})
                    seen_sources.add(src)
        else:
            monitored.append({"name": signal_name})

    return monitored, _ordered_unique_text(warnings)


def _signal_aliases(
    signal_name: str,
    *,
    verification_requirement_payload: Mapping[str, Any] | None = None,
    trajectory_manifest_payload: Mapping[str, Any] | None = None,
) -> List[str]:
    verification = verification_requirement_payload if isinstance(verification_requirement_payload, Mapping) else {}
    manifest = trajectory_manifest_payload if isinstance(trajectory_manifest_payload, Mapping) else {}
    verification_aliases = (
        verification.get("signal_aliases") if isinstance(verification.get("signal_aliases"), Mapping) else {}
    )
    manifest_aliases = manifest.get("signal_aliases") if isinstance(manifest.get("signal_aliases"), Mapping) else {}
    return _ordered_unique_text(
        [signal_name]
        + list(verification_aliases.get(signal_name, []) if isinstance(verification_aliases.get(signal_name), list) else [])
        + list(manifest_aliases.get(signal_name, []) if isinstance(manifest_aliases.get(signal_name), list) else [])
    )


def _endpoint_causality_map(selected_fmus: Sequence[FMU]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for fmu in selected_fmus:
        uid = str(getattr(fmu, "uid", "")).strip()
        if not uid:
            continue
        if getattr(fmu, "ports", None):
            for port in getattr(fmu, "ports", []):
                name = str(getattr(port, "name", "")).strip()
                if not name:
                    continue
                mapping[f"{uid}.{name}"] = str(getattr(port, "causality", "") or "").strip().lower()
        else:
            for name in getattr(fmu, "outputs", []):
                text = str(name or "").strip()
                if text:
                    mapping[f"{uid}.{text}"] = "output"
            for name in getattr(fmu, "inputs", []):
                text = str(name or "").strip()
                if text:
                    mapping.setdefault(f"{uid}.{text}", "input")
    return mapping


def _output_endpoints_by_signal(selected_fmus: Sequence[FMU]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    endpoint_causality = _endpoint_causality_map(selected_fmus)
    for endpoint, causality in endpoint_causality.items():
        if causality != "output":
            continue
        _, signal_name = _split_endpoint(endpoint)
        if signal_name:
            out.setdefault(signal_name, []).append(endpoint)
    return {key: _ordered_unique_text(values) for key, values in out.items()}


def _resolve_monitored_source(
    signal_name: str,
    *,
    aliases: Sequence[str],
    endpoint_causality: Mapping[str, str],
    output_endpoints_by_name: Mapping[str, Sequence[str]],
    binding_sources: set[str] = frozenset(),
) -> Tuple[str, List[str], List[str]]:
    """Returns (best_source, all_sources, warnings).
    best_source is set when unambiguous; all_sources lists every matching
    output endpoint so the caller can emit one monitored entry per FMU."""
    warnings: List[str] = []
    qualified_aliases = [alias for alias in aliases if "." in alias]
    output_aliases = [alias for alias in qualified_aliases if endpoint_causality.get(alias) == "output"]
    invalid_aliases = [
        alias
        for alias in qualified_aliases
        if alias in endpoint_causality and endpoint_causality.get(alias) != "output"
    ]
    for alias in invalid_aliases:
        warnings.append(
            f"invalid_monitor_binding:{signal_name}:{alias}:{endpoint_causality.get(alias, 'unknown')}"
        )

    unique_output_aliases = _ordered_unique_text(output_aliases)
    if len(unique_output_aliases) == 1:
        return unique_output_aliases[0], unique_output_aliases, warnings
    if len(unique_output_aliases) > 1:
        if binding_sources:
            binding_hits = [a for a in unique_output_aliases if a in binding_sources]
            if len(binding_hits) == 1:
                return binding_hits[0], unique_output_aliases, warnings
        return "", unique_output_aliases, warnings

    output_name_matches = _ordered_unique_text(output_endpoints_by_name.get(signal_name, []))
    if len(output_name_matches) == 1:
        return output_name_matches[0], output_name_matches, warnings
    if len(output_name_matches) > 1:
        if binding_sources:
            binding_hits = [m for m in output_name_matches if m in binding_sources]
            if len(binding_hits) == 1:
                return binding_hits[0], output_name_matches, warnings
        return "", output_name_matches, warnings
    return "", [], warnings


def _split_endpoint(endpoint: str) -> Tuple[str, str]:
    asset_id, _, signal_name = str(endpoint or "").partition(".")
    return asset_id.strip(), signal_name.strip()
