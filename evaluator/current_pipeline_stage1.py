from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from pipeline.stage1_decomposition import decompose
from pipeline.stage1_decomposition.decomposer import _extract_acceptance_criteria
from pipeline.types import AcceptanceCriterion, ChainSegment, RequiredSignalChain, TaskSet, VerificationTask


def run_current_stage1(
    requirement: str,
    *,
    mbse_context,
    config: Mapping[str, Any],
) -> list[TaskSet]:
    tasksets = decompose(
        requirement,
        mbse_context=mbse_context,
        confidence=float(config.get("confidence", 0.9)),
        max_candidates=int(config.get("max_candidates", 6)),
    )
    return _sanitize_tasksets(tasksets, requirement, case_payload=_load_case_payload(mbse_context))


def _sanitize_tasksets(
    tasksets: Sequence[TaskSet],
    requirement: str,
    *,
    case_payload: Mapping[str, Any] | None,
) -> list[TaskSet]:
    structure_hints = _load_structure_hints(case_payload)
    repaired_tasksets: list[TaskSet] = []
    for taskset in tasksets:
        repaired_tasks: list[VerificationTask] = []
        repaired_count = 0
        for task in taskset.tasks:
            repaired_task, changed = _repair_task_criteria(task, requirement)
            repaired_tasks.append(repaired_task)
            if changed:
                repaired_count += 1
        meta = dict(taskset.meta)
        updated_taskset = taskset if repaired_count == 0 else replace(taskset, tasks=repaired_tasks, meta=meta)
        if repaired_count > 0:
            meta["current_pipeline_stage1_repaired_criteria"] = True
            meta["current_pipeline_stage1_repaired_task_count"] = repaired_count
            updated_taskset = replace(updated_taskset, meta=meta)

        updated_taskset, hint_stats = _apply_structure_hints(updated_taskset, structure_hints)
        if hint_stats["chain_count"] > 0 or hint_stats["task_count"] > 0:
            meta = dict(updated_taskset.meta)
            meta["current_pipeline_stage1_structure_hints_applied"] = True
            meta["current_pipeline_stage1_structure_hint_chain_count"] = hint_stats["chain_count"]
            meta["current_pipeline_stage1_structure_hint_task_count"] = hint_stats["task_count"]
            meta["required_chain_count"] = len(updated_taskset.required_signal_chains)
            updated_taskset = replace(updated_taskset, meta=meta)

        repaired_tasksets.append(updated_taskset)
    return repaired_tasksets


def _repair_task_criteria(task: VerificationTask, requirement: str) -> tuple[VerificationTask, bool]:
    criteria = list(task.acceptance_criteria)
    if not _looks_like_char_split_criteria(criteria):
        return task, False

    repaired = [
        criterion
        for criterion in _extract_acceptance_criteria(requirement)
        if not _is_char_split_criterion(criterion)
    ]
    diagnostics = dict(task.diagnostics)
    diagnostics["current_pipeline_stage1_repaired_criteria"] = True
    diagnostics["current_pipeline_stage1_repair_reason"] = "char_split_acceptance_criteria"
    diagnostics["current_pipeline_stage1_original_criteria_count"] = len(criteria)
    diagnostics["current_pipeline_stage1_repaired_criteria_count"] = len(repaired)
    if not repaired:
        diagnostics["current_pipeline_stage1_repair_fallback"] = "dropped_pathological_criteria"
    return replace(task, acceptance_criteria=repaired, diagnostics=diagnostics), True


def _looks_like_char_split_criteria(criteria: Sequence[AcceptanceCriterion]) -> bool:
    if len(criteria) < 4:
        return False
    suspicious = sum(1 for criterion in criteria if _is_char_split_criterion(criterion))
    return suspicious >= max(4, len(criteria) // 2)


def _is_char_split_criterion(criterion: AcceptanceCriterion) -> bool:
    metric = str(criterion.metric or "").strip()
    operator = str(criterion.operator or "").strip().lower()
    notes = str(criterion.notes or "").strip()
    value_text = _criterion_value_text(criterion.value)
    if operator != "descriptive":
        return False
    if len(metric) != 1:
        return False
    payloads = [text for text in (metric, notes, value_text) if text]
    if not payloads:
        return False
    return all(len(text) <= 1 for text in payloads)


def _criterion_value_text(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)):
        return str(value).strip()
    return ""


def _load_case_payload(mbse_context) -> Mapping[str, Any] | None:
    case_root_raw = (mbse_context.metadata or {}).get("case_root")
    if not case_root_raw:
        return None
    case_json_path = Path(str(case_root_raw)).expanduser().resolve() / "case.json"
    if not case_json_path.exists():
        return None
    try:
        payload = json.loads(case_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_structure_hints(case_payload: Mapping[str, Any] | None) -> list[dict[str, str]]:
    requirement = case_payload.get("requirement") if isinstance(case_payload, dict) else {}
    if not isinstance(requirement, dict):
        return []
    structure_hints = requirement.get("structure_hints")
    if not isinstance(structure_hints, dict):
        return []
    raw_chains = structure_hints.get("required_signal_chains")
    if not isinstance(raw_chains, list):
        return []

    hints: list[dict[str, str]] = []
    for raw_chain in raw_chains:
        if not isinstance(raw_chain, dict):
            continue
        source_component = str(raw_chain.get("source_component") or "").strip()
        source_signal = str(raw_chain.get("source_signal") or "").strip()
        target_component = str(raw_chain.get("target_component") or "").strip()
        target_signal = str(raw_chain.get("target_signal") or "").strip()
        if not (source_component and source_signal and target_component and target_signal):
            continue
        hints.append(
            {
                "source_component": source_component,
                "source_signal": source_signal,
                "target_component": target_component,
                "target_signal": target_signal,
                "rationale": str(raw_chain.get("rationale") or "").strip(),
            }
        )
    return hints


def _apply_structure_hints(taskset: TaskSet, structure_hints: Sequence[Mapping[str, str]]) -> tuple[TaskSet, dict[str, int]]:
    if not structure_hints:
        return taskset, {"chain_count": 0, "task_count": 0}

    tasks = list(taskset.tasks)
    required_signal_chains = list(taskset.required_signal_chains)
    existing_chain_keys = {_chain_key_from_chain(chain) for chain in required_signal_chains}
    added_chain_count = 0
    added_task_count = 0

    for index, hint in enumerate(structure_hints):
        chain_key = (
            str(hint.get("source_component") or "").strip(),
            str(hint.get("source_signal") or "").strip(),
            str(hint.get("target_component") or "").strip(),
            str(hint.get("target_signal") or "").strip(),
        )
        if not all(chain_key):
            continue

        if not _taskset_covers_chain(tasks, chain_key):
            task_id = f"current_pipeline_structure_hint_task_{index}"
            objective = (
                f"Preserve structural signal path {chain_key[0]}.{chain_key[1]} -> {chain_key[2]}.{chain_key[3]}"
            )
            tasks.append(
                VerificationTask(
                    task_id=task_id,
                    objective=objective,
                    required_signals=[chain_key[1], chain_key[3]],
                    grounded_components=[chain_key[0], chain_key[2]],
                    grounded_ports=[f"{chain_key[0]}.{chain_key[1]}", f"{chain_key[2]}.{chain_key[3]}"],
                    task_trace={
                        "notes": ["current_pipeline_stage1_structure_hints"],
                        "structure_hint": {
                            "source_component": chain_key[0],
                            "source_signal": chain_key[1],
                            "target_component": chain_key[2],
                            "target_signal": chain_key[3],
                        },
                    },
                    diagnostics={
                        "current_pipeline_stage1_structure_hint": True,
                        "current_pipeline_stage1_structure_hint_reason": str(hint.get("rationale") or "").strip(),
                    },
                )
            )
            added_task_count += 1

        if chain_key in existing_chain_keys:
            continue

        origin_task_ids = [task.task_id for task in tasks if _task_covers_chain(task, chain_key)]
        chain_id = f"current_pipeline_structure_hint_chain_{index}"
        semantic_intent = f"{chain_key[0]}.{chain_key[1]} -> {chain_key[2]}.{chain_key[3]}"
        required_signal_chains.append(
            RequiredSignalChain(
                chain_id=chain_id,
                source_component=chain_key[0],
                target_component=chain_key[2],
                signals=[chain_key[1], chain_key[3]],
                origin_task_ids=origin_task_ids,
                segments=[
                    ChainSegment(
                        segment_id=f"{chain_id}_seg_0",
                        source_component=chain_key[0],
                        source_signal=chain_key[1],
                        target_component=chain_key[2],
                        target_signal=chain_key[3],
                        semantic_intent=semantic_intent,
                        adjacency_evidence={
                            "source": "current_pipeline_stage1_structure_hints",
                            "rationale": str(hint.get("rationale") or "").strip(),
                        },
                    )
                ],
                semantic_intent=semantic_intent,
                details={
                    "source_signal": chain_key[1],
                    "target_signal": chain_key[3],
                    "source": "current_pipeline_stage1_structure_hints",
                    "rationale": str(hint.get("rationale") or "").strip(),
                },
            )
        )
        existing_chain_keys.add(chain_key)
        added_chain_count += 1

    if added_chain_count == 0 and added_task_count == 0:
        return taskset, {"chain_count": 0, "task_count": 0}

    return (
        replace(taskset, tasks=tasks, required_signal_chains=required_signal_chains),
        {"chain_count": added_chain_count, "task_count": added_task_count},
    )


def _taskset_covers_chain(tasks: Sequence[VerificationTask], chain_key: tuple[str, str, str, str]) -> bool:
    return any(_task_covers_chain(task, chain_key) for task in tasks)


def _task_covers_chain(task: VerificationTask, chain_key: tuple[str, str, str, str]) -> bool:
    components = {str(item).strip() for item in task.grounded_components if str(item).strip()}
    signals = {str(item).strip() for item in task.required_signals if str(item).strip()}
    ports = {str(item).strip() for item in task.grounded_ports if str(item).strip()}
    source_port = f"{chain_key[0]}.{chain_key[1]}"
    target_port = f"{chain_key[2]}.{chain_key[3]}"
    return (
        {chain_key[0], chain_key[2]}.issubset(components)
        or {chain_key[1], chain_key[3]}.issubset(signals)
        or {source_port, target_port}.issubset(ports)
    )


def _chain_key_from_chain(chain: RequiredSignalChain) -> tuple[str, str, str, str]:
    if chain.segments:
        first_segment = chain.segments[0]
        return (
            str(first_segment.source_component).strip(),
            str(first_segment.source_signal).strip(),
            str(first_segment.target_component).strip(),
            str(first_segment.target_signal).strip(),
        )
    source_signal = str(chain.details.get("source_signal") or "").strip()
    target_signal = str(chain.details.get("target_signal") or "").strip()
    if len(chain.signals) >= 2:
        source_signal = source_signal or str(chain.signals[0]).strip()
        target_signal = target_signal or str(chain.signals[1]).strip()
    return (
        str(chain.source_component).strip(),
        source_signal,
        str(chain.target_component).strip(),
        target_signal,
    )
