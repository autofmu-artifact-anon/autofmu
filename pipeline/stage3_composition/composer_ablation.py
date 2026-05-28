"""Stage 3 ablation: fixed-step direct wiring without adapters."""

from __future__ import annotations

from typing import Dict, List

from pipeline.types import CompositionResult, MatchingResult, MBSEContext, OrchestrationGraph, SimulationConfig

from .scheduler import build_fixed_step_config


def compose(matching: MatchingResult, *, mbse_context: MBSEContext) -> CompositionResult:
    del mbse_context
    connections = [
        {"source": f"{binding.source_fmu}.{binding.source_signal}", "target": f"{binding.target_fmu}.{binding.target_signal}", "kind": "direct"}
        for binding in matching.graph.bindings
    ]
    if not connections and matching.selected_fmus:
        for fmu in matching.selected_fmus[:1]:
            for signal in fmu.outputs[:1]:
                connections.append({"source": f"{fmu.uid}.{signal}", "target": f"{fmu.uid}.sink", "kind": "ablation_observe"})
    config = build_fixed_step_config(
        fmus=matching.selected_fmus,
        step_size=0.01,
        duration=1.0,
        connections=connections,
        meta={"ablation": True, "adapters": []},
    )
    graph = OrchestrationGraph(
        nodes=[fmu.uid for fmu in matching.selected_fmus],
        bindings=matching.graph.bindings,
        component_to_fmu=matching.graph.component_to_fmu,
        diagnostics={"ablation": True},
    )
    return CompositionResult(
        graph_augmented=graph,
        adapters=[],
        schedule={"kind": "fixed_step", "step_size": 0.01},
        loop_resolution=[],
        simulation_config=config,
        diagnostics={"ablation": True},
    )
