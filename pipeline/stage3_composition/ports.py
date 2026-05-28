"""Port helpers for Stage 3 adapter synthesis."""

from __future__ import annotations

from typing import Any, Dict, List

def normalize_unit(unit: str) -> str:
    lowered = (unit or "").strip().lower()
    aliases = {
        "celsius": "degc",
        "c": "degc",
        "0..1": "1",
        "none": "",
        "kelvin": "k",
        "radian": "rad",
    }
    return aliases.get(lowered, lowered)
def normalize_type_name(type_name: str) -> str:
    lowered = (type_name or "").strip().lower()
    aliases = {
        "double": "real",
        "float": "real",
        "int": "integer",
        "bool": "boolean",
    }
    return aliases.get(lowered, lowered)


def coerce_scalar_for_type(value: Any, type_name: str) -> float:
    normalized = normalize_type_name(type_name)
    if normalized == "boolean":
        if isinstance(value, str):
            return 1.0 if value.strip().lower() in {"1", "true", "on", "yes"} else 0.0
        return 1.0 if float(value) >= 0.5 else 0.0
    if normalized == "integer":
        return float(int(round(float(value))))
    return float(value)


def normalize_transform(transform: Dict[str, object]) -> Dict[str, object]:
    raw = dict(transform)
    kind = str(raw.get("transform_kind") or raw.get("mode") or "pass_through").strip().lower()
    normalized: Dict[str, object] = {"transform_kind": kind}
    if kind == "unit_transform":
        normalized.update(
            {
                "source_unit": normalize_unit(str(raw.get("source_unit") or "")),
                "target_unit": normalize_unit(str(raw.get("target_unit") or "")),
                "scale": float(raw.get("scale", 1.0) or 1.0),
                "offset": float(raw.get("offset", 0.0) or 0.0),
            }
        )
        return normalized
    if kind == "mode_signal":
        mapping = raw.get("mapping") if isinstance(raw.get("mapping"), dict) else {}
        normalized.update(
            {
                "source_type": normalize_type_name(str(raw.get("source_type") or "")),
                "target_type": normalize_type_name(str(raw.get("target_type") or "")),
                "mapping": {str(key): float(value) for key, value in mapping.items()},
            }
        )
        return normalized
    if kind == "dimension_transform":
        normalized.update(
            {
                "source_dimensions": _normalize_dims(raw.get("source_dimensions") or raw.get("source_dimension")),
                "target_dimensions": _normalize_dims(raw.get("target_dimensions") or raw.get("target_dimension")),
                "aggregation": str(raw.get("aggregation") or "reshape"),
            }
        )
        return normalized
    if kind == "type_cast":
        normalized.update(
            {
                "source_type": normalize_type_name(str(raw.get("source_type") or "")),
                "target_type": normalize_type_name(str(raw.get("target_type") or "")),
            }
        )
        return normalized
    normalized.update(
        {
            key: value
            for key, value in raw.items()
            if key not in {"mode"} and value is not None
        }
    )
    normalized["transform_kind"] = "pass_through"
    return normalized


def apply_adapter_transform(value: Any, transform: Dict[str, object]) -> float | List[float]:
    normalized = normalize_transform(transform)
    kind = str(normalized.get("transform_kind") or "pass_through")
    if kind == "unit_transform":
        scale = float(normalized.get("scale", 1.0) or 1.0)
        offset = float(normalized.get("offset", 0.0) or 0.0)
        return float(value) * scale + offset
    if kind == "mode_signal":
        mapping = normalized.get("mapping") if isinstance(normalized.get("mapping"), dict) else {}
        key = _mapping_key(value)
        if key in mapping:
            return float(mapping[key])
        if isinstance(value, str) and value.strip().lower() in mapping:
            return float(mapping[value.strip().lower()])
        return 1.0 if float(value) >= 0.5 else 0.0
    if kind == "type_cast":
        return coerce_scalar_for_type(value, str(normalized.get("target_type") or "real"))
    if kind == "dimension_transform":
        values = _as_value_list(value)
        target_dims = normalized.get("target_dimensions") if isinstance(normalized.get("target_dimensions"), list) else []
        target_count = _element_count(target_dims)
        if target_count <= 1:
            return float(values[0] if values else 0.0)
        if not values:
            return [0.0 for _ in range(target_count)]
        padded = list(values[:target_count])
        while len(padded) < target_count:
            padded.append(float(values[-1]))
        return [float(item) for item in padded]
    if isinstance(value, list):
        return [float(item) for item in value]
    return float(value)


def infer_adapter_transform(kind: str, details: Dict[str, object]) -> Dict[str, object]:
    source_unit = normalize_unit(str(details.get("source_unit") or ""))
    target_unit = normalize_unit(str(details.get("target_unit") or ""))
    if kind == "unit_transform_adapter":
        scale = 1.0
        offset = 0.0
        if source_unit == "degc" and target_unit == "k":
            offset = 273.15
        elif source_unit == "k" and target_unit == "degc":
            offset = -273.15
        return {
            "transform_kind": "unit_transform",
            "source_unit": source_unit,
            "target_unit": target_unit,
            "scale": scale,
            "offset": offset,
        }
    if kind == "mode_signal_adapter":
        return {
            "transform_kind": "mode_signal",
            "source_type": normalize_type_name(str(details.get("source_port_type") or "")),
            "target_type": normalize_type_name(str(details.get("target_port_type") or "")),
            "mapping": {"0": 0.0, "1": 1.0, "false": 0.0, "true": 1.0},
        }
    if kind == "dimension_adapter":
        return {
            "transform_kind": "dimension_transform",
            "source_dimensions": details.get("source_dimensions", []),
            "target_dimensions": details.get("target_dimensions", []),
            "aggregation": "reshape",
        }
    if kind == "type_adapter":
        return {
            "transform_kind": "type_cast",
            "source_type": normalize_type_name(str(details.get("source_port_type") or "")),
            "target_type": normalize_type_name(str(details.get("target_port_type") or "")),
        }
    return {"transform_kind": "pass_through", **details}


def _normalize_dims(raw: object) -> List[int]:
    if isinstance(raw, list):
        dims: List[int] = []
        for item in raw:
            try:
                dims.append(int(item))
            except (TypeError, ValueError):
                continue
        return dims
    if raw in (None, ""):
        return []
    try:
        return [int(raw)]
    except (TypeError, ValueError):
        return []


def _element_count(dims: List[int]) -> int:
    count = 1
    for dim in dims:
        if dim <= 0:
            continue
        count *= dim
    return count


def _as_value_list(value: Any) -> List[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(value)]


def _mapping_key(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    numeric = float(value)
    if abs(numeric - round(numeric)) <= 1e-9:
        return str(int(round(numeric)))
    return f"{numeric:.12g}"
