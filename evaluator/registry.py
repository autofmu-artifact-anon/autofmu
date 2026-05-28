from __future__ import annotations

from typing import Dict, List

from .types import MethodBundle


_REGISTRY: Dict[str, MethodBundle] = {}


def register_bundle(bundle: MethodBundle) -> None:
    _REGISTRY[bundle.name] = bundle


def get_bundle(name: str) -> MethodBundle:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY)) or "<empty>"
        raise KeyError(f"Unknown evaluator bundle {name!r}. Available: {known}") from exc


def available_bundles() -> List[str]:
    return sorted(_REGISTRY)
