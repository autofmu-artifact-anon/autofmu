from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, runtime_checkable

from pipeline.types import CompositionResult, FMU, MatchingResult, MBSEContext, TaskSet


@runtime_checkable
class Stage1Method(Protocol):
    def __call__(
        self,
        requirement: str,
        *,
        mbse_context: MBSEContext,
        config: Mapping[str, Any],
    ) -> List[TaskSet]:
        ...


@runtime_checkable
class Stage2Method(Protocol):
    def __call__(
        self,
        task_candidates: List[TaskSet],
        *,
        mbse_context: MBSEContext,
        fmu_library: List[FMU],
        config: Mapping[str, Any],
    ) -> MatchingResult:
        ...


@runtime_checkable
class Stage3Method(Protocol):
    def __call__(
        self,
        matching_result: MatchingResult,
        *,
        mbse_context: MBSEContext,
        config: Mapping[str, Any],
    ) -> CompositionResult:
        ...


@dataclass(frozen=True)
class MethodBundle:
    name: str
    description: str
    stage1: Stage1Method
    stage2: Stage2Method
    stage3: Stage3Method
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationSpec:
    dataset_root: str = "dataset"
    manifest_path: str = "pipeline/resources/fmu_library/manifest.json"
    bundle_name: str = "current_pipeline"
    case_ids: List[str] = field(default_factory=list)
    out_root: str = "evaluator/runs"
    experiment_id: Optional[str] = None
    fail_fast: bool = False
    workers: int = 1
    timeout_seconds: Optional[float] = 100.0
    resume: bool = False
    stage1_config: Dict[str, Any] = field(default_factory=dict)
    stage2_config: Dict[str, Any] = field(default_factory=dict)
    stage3_config: Dict[str, Any] = field(default_factory=dict)
    disable_reference_bootstrap: bool = False


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    source_type: str
    case_root: Path
    title: str = ""
    case_category: str = "simple"
    ground_truth_fmu_count: int = 0
    ground_truth_asset_ids: List[str] = field(default_factory=list)
    candidate_asset_ids: List[str] = field(default_factory=list)
    solution_relpath: str = "solution.json"
    supports_execution_metrics: bool = False
    supports_numerical_fidelity: bool = False
    supports_decision_accuracy: bool = False
    evaluation_artifacts: Dict[str, Any] = field(default_factory=dict)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferencePack:
    case_id: str
    retrieval_reference: Dict[str, Any]
    solution: Dict[str, Any]
    verification_requirement: Dict[str, Any]
    verification_result: Dict[str, Any]
    trajectory_manifest: Dict[str, Any]
    ground_truth_trajectory_path: Optional[str] = None
    input_trajectory_path: Optional[str] = None
    declared_scenario_window: Dict[str, Any] = field(default_factory=dict)
    declared_initial_conditions: Dict[str, Any] = field(default_factory=dict)
    supports_execution_metrics: bool = False
    supports_numerical_fidelity: bool = False
    supports_decision_accuracy: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    source_type: str
    case_category: str
    ground_truth_fmu_count: int
    ok: bool
    bundle_name: str
    artifact_root: str
    stage_status: Dict[str, Any]
    execution_status: Dict[str, Any]
    metrics: Dict[str, Any]
    artifact_paths: Dict[str, str]
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperimentSummary:
    experiment_id: str
    bundle_name: str
    dataset_root: str
    output_root: str
    cases_total: int
    succeeded: int
    failed: int
    aggregate_metrics: Dict[str, Any]
    case_rows: List[CaseEvaluation] = field(default_factory=list)
