"""Conformal helpers for Stage 1 filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class ConformalDecision:
    score: float
    item: object
    p_value: float
    threshold: float
    accepted: bool
    accepted_by: str
    nonconformity: float
    fallback_retained: bool = False


def p_value_for_score(score: float, calibration_scores: Sequence[float]) -> float:
    bounded = max(0.0, min(1.0, float(score)))
    calibration = [max(0.0, min(1.0, float(item))) for item in calibration_scores]
    if not calibration:
        return 1.0
    nonconformity = 1.0 - bounded
    calibration_nonconformity = [1.0 - item for item in calibration]
    ge = sum(1 for item in calibration_nonconformity if item >= nonconformity)
    return float((ge + 1) / (len(calibration_nonconformity) + 1))


def nonconformity_for_score(score: float) -> float:
    return float(1.0 - max(0.0, min(1.0, float(score))))


def filter_by_confidence(
    scored: Sequence[Tuple[float, object]],
    *,
    calibration_scores: Iterable[float],
    confidence: float,
    keep_at_least: int = 1,
) -> List[ConformalDecision]:
    accepted: List[ConformalDecision] = []
    threshold = max(0.0, min(1.0, 1.0 - float(confidence)))
    scores = list(calibration_scores)
    for score, item in scored:
        bounded_score = max(0.0, min(1.0, float(score)))
        p_value = p_value_for_score(bounded_score, scores)
        if p_value >= threshold:
            accepted.append(
                ConformalDecision(
                    score=bounded_score,
                    item=item,
                    p_value=float(p_value),
                    threshold=threshold,
                    accepted=True,
                    accepted_by="p_value",
                    nonconformity=nonconformity_for_score(bounded_score),
                    fallback_retained=False,
                )
            )
    if accepted:
        accepted.sort(key=lambda item: (-item.score, -item.p_value, item.fallback_retained))
        return accepted
    fallback = sorted(scored, key=lambda item: -float(item[0]))[: max(int(keep_at_least), 1)]
    return [
        ConformalDecision(
            score=max(0.0, min(1.0, float(score))),
            item=item,
            p_value=float(p_value_for_score(float(score), scores)),
            threshold=threshold,
            accepted=False,
            accepted_by="forced_fallback",
            nonconformity=nonconformity_for_score(float(score)),
            fallback_retained=True,
        )
        for score, item in fallback
    ]
