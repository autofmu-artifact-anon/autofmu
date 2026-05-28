"""Shared types for the unified requirement-to-orchestration pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AcceptanceCriterion:
    metric: str
    operator: str
    value: Any
    unit: str = ""
    notes: str = ""


@dataclass(frozen=True)
class OperatingRegime:
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    initial_conditions: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class TaskSignalSpec:
    signal_name: str
    direction: str = ""
    component_hint: str = ""
    port_hint: str = ""
    unit_hint: str = ""
    type_hint: str = ""
    role: str = ""
    source_text: str = ""
    grounded_component_ref: str = ""
    grounded_port_ref: str = ""


@dataclass(frozen=True)
class TaskConstraint:
    metric: str
    operator: str
    value: Any
    unit: str = ""
    grounded_signal: str = ""
    scope: str = "task"
    source_text: str = ""
    grounded_component_ref: str = ""
    grounded_port_ref: str = ""


@dataclass(frozen=True)
class VerificationTask:
    task_id: str
    objective: str
    required_signals: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    signal_specs: List[TaskSignalSpec] = field(default_factory=list)
    constraint_set: List[TaskConstraint] = field(default_factory=list)
    operating_regime: Optional[OperatingRegime] = None
    grounded_components: List[str] = field(default_factory=list)
    grounded_component_types: List[str] = field(default_factory=list)
    grounded_ports: List[str] = field(default_factory=list)
    task_trace: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChainSegment:
    segment_id: str
    source_component: str
    source_signal: str
    target_component: str
    target_signal: str
    must_route: bool = True
    semantic_intent: str = ""
    adjacency_evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskSet:
    tasks: List[VerificationTask]
    rationale: str = ""
    score: float = 0.0
    p_value: float = 0.0
    task_set_id: str = ""
    generation_source: str = ""
    grounding_status: str = ""
    required_signal_chains: List["RequiredSignalChain"] = field(default_factory=list)
    conformal_info: Dict[str, Any] = field(default_factory=dict)
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PortMeta:
    name: str
    causality: str = "local"
    variability: str = "continuous"
    type: str = "Real"
    unit: str = ""
    description: str = ""
    dimensions: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class FMUCapabilities:
    needs_execution_tool: bool = False
    can_handle_variable_communication_step_size: bool = True
    can_interpolate_inputs: bool = False
    can_run_asynchronously: bool = False
    can_be_instantiated_only_once_per_process: bool = False
    provides_directional_derivatives: bool = False
    fixed_internal_step_size: Optional[float] = None


@dataclass(frozen=True)
class FMU:
    uid: str
    name: str
    description: str = ""
    path: Optional[str] = None
    fmi_version: str = "2.0"
    fmi_types: List[str] = field(default_factory=list)
    ports: List[PortMeta] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    capabilities: FMUCapabilities = field(default_factory=FMUCapabilities)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MBSEPort:
    component: str
    name: str
    direction: str
    type_hint: str = ""
    qualified_name: str = ""


@dataclass(frozen=True)
class MBSEComponent:
    name: str
    component_type: str
    ports: List[MBSEPort] = field(default_factory=list)


@dataclass(frozen=True)
class MBSEConnection:
    source_component: str
    source_signal: str
    target_component: str
    target_signal: str


@dataclass(frozen=True)
class MBSEContext:
    package_name: str
    system_name: str
    components: List[MBSEComponent] = field(default_factory=list)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    connections: List[MBSEConnection] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskAssignment:
    task_id: str
    task_index: int
    fmu_uid: str
    score: float = 0.0
    cost: float = 0.0
    hard_ok: bool = False
    semantic_cost: float = 0.0
    hard_mask_value: float = 0.0
    transport_mass: float = 0.0
    revision_index: int = 0
    reasons: List[str] = field(default_factory=list)
    grounded_components: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PortBinding:
    source_fmu: str
    source_signal: str
    target_fmu: str
    target_signal: str
    score: float
    chain_id: str = ""
    segment_id: str = ""
    selected_by: str = "score"
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DiscrepancyEdge:
    source_fmu: str
    source_signal: str
    target_fmu: str
    target_signal: str
    kind: str
    details: Dict[str, Any] = field(default_factory=dict)
    chain_id: str = ""
    segment_id: str = ""
    preserves_signal_path: bool = False
    preservation_evidence: Dict[str, Any] = field(default_factory=dict)
    source_port_meta: Dict[str, Any] = field(default_factory=dict)
    target_port_meta: Dict[str, Any] = field(default_factory=dict)
    local_mbse_context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RequiredSignalChain:
    chain_id: str
    source_component: str
    target_component: str
    signals: List[str] = field(default_factory=list)
    origin_task_ids: List[str] = field(default_factory=list)
    segments: List[ChainSegment] = field(default_factory=list)
    semantic_intent: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BindingCandidate:
    source_port: PortMeta
    target_port: PortMeta
    score: float = 0.0
    chain_id: str = ""
    segment_id: str = ""
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    causality_ok: bool = False
    topology_ok: bool = False
    preserves_signal_path: bool = False
    routeable: bool = False
    discrepancy_kind: Optional[str] = None
    discrepancy_details: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class OrchestrationGraph:
    nodes: List[str] = field(default_factory=list)
    port_nodes: List[str] = field(default_factory=list)
    bindings: List[PortBinding] = field(default_factory=list)
    component_to_fmu: Dict[str, str] = field(default_factory=dict)
    required_signal_chains: List[RequiredSignalChain] = field(default_factory=list)
    binding_candidates: List[Dict[str, Any]] = field(default_factory=list)
    closure_ok: bool = False
    closure_failures: List[Dict[str, Any]] = field(default_factory=list)
    routing_failures: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchingResult:
    task_set: TaskSet
    assignments: List[TaskAssignment]
    selected_fmus: List[FMU]
    graph: OrchestrationGraph
    discrepancy_set: List[DiscrepancyEdge] = field(default_factory=list)
    revision_trace: List[Dict[str, Any]] = field(default_factory=list)
    final_cost: float = 0.0
    transport_plans: List[Dict[str, Any]] = field(default_factory=list)
    mask_history: List[Dict[str, Any]] = field(default_factory=list)
    taskset_results: List[Dict[str, Any]] = field(default_factory=list)
    selected_task_set_cost: float = 0.0
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterSpec:
    adapter_id: str
    kind: str
    source: str
    target: str
    transform: Dict[str, Any] = field(default_factory=dict)
    stateful: bool = False
    artifact_kind: str = ""
    artifact_path: str = ""
    inserted_node_id: str = ""
    io_contract: Dict[str, Any] = field(default_factory=dict)
    generation_source: str = ""
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SimulationConfig:
    step_size: float
    duration: float
    fmus: List[FMU] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    scheduler: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompositionResult:
    graph_augmented: OrchestrationGraph
    adapters: List[AdapterSpec]
    schedule: Dict[str, Any]
    loop_resolution: List[Dict[str, Any]]
    simulation_config: SimulationConfig
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineResult:
    task_candidates: List[TaskSet]
    selected_task_set: TaskSet
    selected_fmus: List[FMU]
    matching_result: MatchingResult
    composition_result: CompositionResult
    simulation_config: SimulationConfig
    predicted_solution: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
