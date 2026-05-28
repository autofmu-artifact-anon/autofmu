"""Scoring helpers for Stage 2 matching."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Sequence, Set, Tuple

from pipeline.types import FMU, TaskSet, VerificationTask


_CAMEL_RE_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_RE_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")


def _normalize_text(text: str) -> str:
    normalized = _CAMEL_RE_2.sub(r"\1 \2", text or "")
    normalized = _CAMEL_RE_1.sub(r"\1 \2", normalized)
    normalized = normalized.replace("_", " ")
    return normalized.lower()


def tokenize(text: str) -> Set[str]:
    return {token for token in re.split(r"[^a-zA-Z0-9]+", _normalize_text(text)) if token}


def task_text(task: VerificationTask) -> str:
    parts: List[str] = [task.objective]
    parts.extend(task.required_signals)
    parts.extend(task.grounded_ports)
    parts.extend(task.grounded_components)
    parts.extend(task.grounded_component_types)
    for criterion in task.acceptance_criteria:
        parts.append(criterion.metric)
        parts.append(criterion.operator)
    if task.operating_regime is not None:
        parts.extend(str(item) for item in task.operating_regime.inputs.keys())
        parts.extend(str(item) for item in task.operating_regime.initial_conditions.keys())
    return " ".join(part for part in parts if part)


def fmu_text(fmu: FMU) -> str:
    parts: List[str] = [fmu.uid, fmu.name, fmu.description]
    parts.extend(fmu.tags)
    parts.extend(fmu.inputs)
    parts.extend(fmu.outputs)
    for port in fmu.ports:
        parts.append(port.name)
        parts.append(port.description)
        parts.append(port.unit)
        parts.append(port.type)
    return " ".join(part for part in parts if part)


def pairwise_semantic_similarity(task: VerificationTask, fmu: FMU) -> float:
    matrix = _tfidf_matrix([task_text(task), fmu_text(fmu)])
    if len(matrix) != 2:
        return 0.0
    return float(_cosine_similarity(matrix[0], matrix[1]))


def pairwise_semantic_cost(task: VerificationTask, fmu: FMU) -> float:
    return float(1.0 - pairwise_semantic_similarity(task, fmu))


def semantic_cost_matrix(taskset: TaskSet, fmu_library: Sequence[FMU]) -> List[List[float]]:
    task_docs = [task_text(task) for task in taskset.tasks]
    fmu_docs = [fmu_text(fmu) for fmu in fmu_library]
    doc_matrix = _tfidf_matrix(task_docs + fmu_docs)
    task_matrix = doc_matrix[: len(task_docs)]
    fmu_matrix = doc_matrix[len(task_docs) :]
    if not task_matrix or not fmu_matrix:
        return [[0.0 for _ in fmu_docs] for _ in task_docs]
    costs = [[0.0 for _ in fmu_docs] for _ in task_docs]
    for i in range(len(task_docs)):
        for j in range(len(fmu_docs)):
            costs[i][j] = float(1.0 - _cosine_similarity(task_matrix[i], fmu_matrix[j]))
    return costs


def rank_port_candidates(signal_name: str, port_names: Sequence[str]) -> List[Tuple[str, float]]:
    signal_tokens = tokenize(signal_name)
    ranked: List[Tuple[str, float]] = []
    for port_name in port_names:
        port_tokens = tokenize(port_name)
        if not signal_tokens and not port_tokens:
            score = 0.0
        else:
            intersection = len(signal_tokens & port_tokens)
            union = len(signal_tokens | port_tokens)
            score = float(intersection / max(union, 1))
        exact = 1.0 if signal_name.lower() == port_name.lower() else 0.0
        ranked.append((port_name, float(0.85 * exact + 0.15 * score if exact else score)))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def _tfidf_matrix(documents: Sequence[str]) -> List[List[float]]:
    tokenized_docs = [Counter(_expand_tokens(doc)) for doc in documents]
    vocab = sorted({token for counts in tokenized_docs for token in counts})
    if not vocab:
        return [[0.0] for _ in documents]
    index = {token: idx for idx, token in enumerate(vocab)}
    df: Dict[str, int] = {}
    for counts in tokenized_docs:
        for token in counts.keys():
            df[token] = df.get(token, 0) + 1
    matrix = [[0.0 for _ in vocab] for _ in documents]
    n_docs = max(len(documents), 1)
    for row, counts in enumerate(tokenized_docs):
        total = float(sum(counts.values()) or 1.0)
        for token, count in counts.items():
            col = index[token]
            tf = float(count) / total
            idf = math.log((1.0 + n_docs) / (1.0 + df[token])) + 1.0
            matrix[row][col] = tf * idf
    return matrix


def _expand_tokens(text: str) -> List[str]:
    tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", _normalize_text(text)) if token]
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        if len(token) > 3:
            expanded.append(token[:4])
    return expanded


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    denom = float(left_norm * right_norm)
    if denom <= 1e-12:
        return 0.0
    return float(sum(l * r for l, r in zip(left, right)) / denom)
