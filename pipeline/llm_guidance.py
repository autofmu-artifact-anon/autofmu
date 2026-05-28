"""Shared prompt and validation helpers for pipeline LLM calls."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence


_CAMEL_RE_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_RE_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")


def normalize_text(text: str) -> str:
    normalized = _CAMEL_RE_2.sub(r"\1 \2", text or "")
    normalized = _CAMEL_RE_1.sub(r"\1 \2", normalized)
    normalized = normalized.replace("_", " ")
    return normalized.lower()


def tokenize(text: str) -> List[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9]+", normalize_text(text)) if token]


def goal_is_aligned(summary: str, reference: str, *, min_common_tokens: int = 2, min_overlap: float = 0.2) -> bool:
    summary_tokens = set(tokenize(summary))
    reference_tokens = set(tokenize(reference))
    if not summary_tokens or not reference_tokens:
        return False
    overlap = summary_tokens & reference_tokens
    if len(overlap) >= min_common_tokens:
        return True
    return (len(overlap) / max(1, len(reference_tokens))) >= float(min_overlap)


def unique_strings(values: Iterable[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def build_strict_json_system_prompt(
    *,
    role: str,
    task_goal: str,
    output_contract: Sequence[str],
    validity_rules: Sequence[str],
) -> str:
    sections = [
        f"You are {role}.",
        f"Current task goal: {task_goal}",
        "Return exactly one JSON object and no markdown.",
        "Only use entities, signals, ports, values, and relationships that are explicitly present in the provided context.",
        "If the context is insufficient, return the safest empty or fallback value instead of inventing information.",
        "Output contract:",
        *[f"- {item}" for item in output_contract],
        "Validity rules:",
        *[f"- {item}" for item in validity_rules],
    ]
    return "\n".join(sections)
