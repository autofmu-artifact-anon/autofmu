"""Calibration artifact loading and conformal filtering for Stage 1."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Sequence

from pipeline.types import MBSEContext, TaskSet

from .conformal import filter_by_confidence


def compute_verifiability_score(taskset: TaskSet, requirement: str, mbse_context: MBSEContext) -> Dict[str, float]:
    all_component_names = {component.name for component in mbse_context.components}
    all_signals = {port.name for component in mbse_context.components for port in component.ports}
    req_tokens = {token for token in _tokenize(requirement)}
    grounded_components = {name for task in taskset.tasks for name in task.grounded_components}
    grounded_signals = {name for task in taskset.tasks for name in task.required_signals}
    criteria_count = sum(len(task.acceptance_criteria) for task in taskset.tasks)
    constraint_count = sum(len(task.constraint_set) for task in taskset.tasks)
    regime_count = sum(1 for task in taskset.tasks if task.operating_regime is not None)
    topology_hits = sum(1 for task in taskset.tasks if len(task.grounded_components) > 1)
    total_segments = sum(len(chain.segments) for chain in taskset.required_signal_chains)
    grounded_segments = sum(
        1
        for chain in taskset.required_signal_chains
        for segment in chain.segments
        if segment.source_component in all_component_names
        and segment.target_component in all_component_names
        and (not segment.source_signal or segment.source_signal in all_signals)
        and (not segment.target_signal or segment.target_signal in all_signals)
    )

    component_coverage = len(grounded_components & all_component_names) / max(len(all_component_names), 1)
    signal_coverage = len(grounded_signals & all_signals) / max(len(all_signals), 1) if all_signals else 1.0
    criteria_coverage = min(1.0, criteria_count / max(len(taskset.tasks), 1))
    constraint_completeness = min(1.0, constraint_count / max(len(taskset.tasks), 1))
    regime_coverage = min(1.0, regime_count / max(len(taskset.tasks), 1))
    topology_alignment = min(1.0, topology_hits / max(len(mbse_context.connections), 1)) if mbse_context.connections else 1.0
    chain_completeness = float(grounded_segments / max(total_segments, 1)) if total_segments else 1.0
    requirement_grounding = 0.0
    if req_tokens:
        component_tokens = {token for value in grounded_components for token in _tokenize(value)}
        signal_tokens = {token for value in grounded_signals for token in _tokenize(value)}
        requirement_grounding = len(req_tokens & (component_tokens | signal_tokens)) / max(len(req_tokens), 1)

    final_score = (
        0.22 * component_coverage
        + 0.20 * signal_coverage
        + 0.12 * criteria_coverage
        + 0.12 * constraint_completeness
        + 0.10 * regime_coverage
        + 0.12 * topology_alignment
        + 0.07 * chain_completeness
        + 0.05 * requirement_grounding
    )
    return {
        "component_coverage": float(component_coverage),
        "signal_coverage": float(signal_coverage),
        "criteria_coverage": float(criteria_coverage),
        "constraint_completeness": float(constraint_completeness),
        "regime_coverage": float(regime_coverage),
        "topology_alignment": float(topology_alignment),
        "chain_completeness": float(chain_completeness),
        "requirement_grounding": float(requirement_grounding),
        "final_score": float(max(0.0, min(1.0, final_score))),
    }


def load_calibration_model(path: str | Path) -> Dict[str, object]:
    artifact_path = Path(path).resolve()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    scores = payload.get("calibration_scores")
    if not isinstance(scores, list):
        raise ValueError("stage1 calibration artifact missing calibration_scores")
    numeric_scores = [float(item) for item in scores]
    calibration_size = int(payload.get("calibration_size") or len(numeric_scores))
    confidence_levels = [float(item) for item in payload.get("confidence_levels", [0.8, 0.9, 0.95])]
    score_summary = {
        "min": float(min(numeric_scores)) if numeric_scores else None,
        "max": float(max(numeric_scores)) if numeric_scores else None,
        "mean": float(sum(numeric_scores) / len(numeric_scores)) if numeric_scores else None,
    }
    return {
        "artifact_version": str(payload.get("artifact_version") or "stage1_calibration_v1"),
        "artifact_path": str(artifact_path),
        "calibration_size": calibration_size,
        "calibration_scores": numeric_scores,
        "confidence_levels": confidence_levels,
        "score_summary": score_summary,
    }


def apply_conformal_filter(
    raw_tasksets: Sequence[TaskSet],
    *,
    calibration_model: Dict[str, object],
    confidence: float,
    keep_at_least: int = 1,
) -> List[TaskSet]:
    calibration_scores = calibration_model.get("calibration_scores")
    if not isinstance(calibration_scores, list):
        raise ValueError("calibration_model missing calibration_scores")
    scored = [(float(taskset.score), taskset) for taskset in raw_tasksets]
    filtered = filter_by_confidence(
        scored,
        calibration_scores=[float(item) for item in calibration_scores],
        confidence=float(confidence),
        keep_at_least=keep_at_least,
    )
    output: List[TaskSet] = []
    threshold = None
    p_value_threshold = max(0.0, min(1.0, 1.0 - float(confidence)))
    if calibration_scores:
        alpha = max(0.0, min(1.0, 1.0 - float(confidence)))
        ordered = sorted(float(item) for item in calibration_scores)
        rank = min(len(ordered) - 1, max(0, int(math.floor((1.0 - alpha) * len(ordered))) - 1))
        threshold = ordered[rank]
    calibration_metadata = {
        "artifact_version": calibration_model.get("artifact_version"),
        "artifact_path": calibration_model.get("artifact_path"),
        "calibration_size": calibration_model.get("calibration_size"),
        "confidence_levels": list(calibration_model.get("confidence_levels", [])),
        "score_summary": dict(calibration_model.get("score_summary", {})),
    }
    for decision in filtered:
        taskset = decision.item
        generation_source = str(taskset.generation_source or taskset.meta.get("generation_source") or "")
        engineering_fallback = generation_source == "fallback"
        effective_accepted = bool(decision.accepted and not engineering_fallback)
        effective_accepted_by = "engineering_fallback" if engineering_fallback else decision.accepted_by
        effective_fallback_retained = bool(decision.fallback_retained or engineering_fallback)
        calibrated_member = bool(effective_accepted and effective_accepted_by == "p_value")
        candidate_status = "forced_fallback"
        if engineering_fallback:
            candidate_status = "engineering_fallback"
        elif calibrated_member:
            candidate_status = "calibrated_accept"
        output.append(
            replace(
                taskset,
                score=float(decision.score),
                p_value=float(decision.p_value),
                conformal_info={
                    "threshold": threshold,
                    "p_value_threshold": p_value_threshold,
                    "p_value": float(decision.p_value),
                    "accepted": effective_accepted,
                    "accepted_by": effective_accepted_by,
                    "nonconformity": float(decision.nonconformity),
                    "fallback_retained": effective_fallback_retained,
                    "engineering_fallback": engineering_fallback,
                    "calibrated_member": calibrated_member,
                    "candidate_status": candidate_status,
                    "selection_semantics": "calibrated_set" if calibrated_member else "pipeline_continuity_fallback",
                    "confidence": float(confidence),
                    "calibration_artifact": calibration_metadata,
                },
                meta={
                    **dict(taskset.meta),
                    "calibration_artifact_version": calibration_model.get("artifact_version"),
                    "calibration_artifact_path": calibration_model.get("artifact_path"),
                    "calibration_size": calibration_model.get("calibration_size"),
                    "calibration_confidence_levels": list(calibration_model.get("confidence_levels", [])),
                    "calibration_score_summary": dict(calibration_model.get("score_summary", {})),
                    "confidence": float(confidence),
                    "p_value_threshold": p_value_threshold,
                    "p_value": float(decision.p_value),
                    "accepted": effective_accepted,
                    "accepted_by": effective_accepted_by,
                    "nonconformity": float(decision.nonconformity),
                    "fallback_retained": effective_fallback_retained,
                    "forced_fallback": bool(decision.fallback_retained and not engineering_fallback),
                    "engineering_fallback": engineering_fallback,
                    "calibrated_member": calibrated_member,
                    "candidate_status": candidate_status,
                    "selection_semantics": "calibrated_set" if calibrated_member else "pipeline_continuity_fallback",
                },
            )
        )
    output.sort(key=lambda item: (-item.score, -item.p_value, item.task_set_id or item.rationale))
    return output


def _tokenize(text: str) -> List[str]:
    current = []
    token = []
    for ch in text or "":
        if ch.isalnum():
            token.append(ch.lower())
        elif token:
            current.append("".join(token))
            token = []
    if token:
        current.append("".join(token))
    return current
