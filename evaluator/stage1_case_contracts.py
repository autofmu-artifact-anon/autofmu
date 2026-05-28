from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from pipeline.types import ChainSegment, RequiredSignalChain, TaskSet, VerificationTask


def apply_case_structure_hints(
    tasksets: Sequence[TaskSet],
    *,
    case_payload: Mapping[str, Any] | None,
) -> list[TaskSet]:
    structure_hints = _load_structure_hints(case_payload)
    if not structure_hints:
        return list(tasksets)

    updated_tasksets: list[TaskSet] = []
    for taskset in tasksets:
        updated_taskset, hint_stats = _apply_structure_hints(taskset, structure_hints)
        if hint_stats["chain_count"] > 0 or hint_stats["task_count"] > 0:
            meta = dict(updated_taskset.meta)
            meta["case_structure_hints_applied"] = True
            meta["case_structure_hint_chain_count"] = hint_stats["chain_count"]
            meta["case_structure_hint_task_count"] = hint_stats["task_count"]
            meta["required_chain_count"] = len(updated_taskset.required_signal_chains)
            updated_taskset = replace(updated_taskset, meta=meta)
        updated_tasksets.append(updated_taskset)
    return updated_tasksets


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


def _apply_structure_hints(
    taskset: TaskSet,
    structure_hints: Sequence[Mapping[str, str]],
) -> tuple[TaskSet, dict[str, int]]:
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
            task_id = f"case_structure_hint_task_{index}"
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
                        "notes": ["case_structure_hints"],
                        "structure_hint": {
                            "source_component": chain_key[0],
                            "source_signal": chain_key[1],
                            "target_component": chain_key[2],
                            "target_signal": chain_key[3],
                        },
                    },
                    diagnostics={
                        "case_structure_hint": True,
                        "case_structure_hint_reason": str(hint.get("rationale") or "").strip(),
                    },
                )
            )
            added_task_count += 1

        if chain_key in existing_chain_keys:
            continue

        origin_task_ids = [task.task_id for task in tasks if _task_covers_chain(task, chain_key)]
        chain_id = f"case_structure_hint_chain_{index}"
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
                            "source": "case_structure_hints",
                            "rationale": str(hint.get("rationale") or "").strip(),
                        },
                    )
                ],
                semantic_intent=semantic_intent,
                details={
                    "source_signal": chain_key[1],
                    "target_signal": chain_key[3],
                    "source": "case_structure_hints",
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
