"""Loop wrapper specs for Stage 3."""

from __future__ import annotations

from typing import Dict, List, Sequence

from pipeline.types import OrchestrationGraph

from .graph_utils import tarjan_scc


def detect_scc_loops(graph: OrchestrationGraph) -> List[List[str]]:
    adjacency: Dict[str, set[str]] = {node: set() for node in graph.nodes}
    for binding in graph.bindings:
        adjacency.setdefault(binding.source_fmu, set()).add(binding.target_fmu)
        adjacency.setdefault(binding.target_fmu, set())
    return [sorted(component) for component in tarjan_scc(sorted(adjacency.keys()), adjacency) if len(component) > 1]


def _ordered_loop_component(component: Sequence[str], preferred_order: Sequence[str]) -> List[str]:
    component_set = {str(node).strip() for node in component if str(node).strip()}
    ordered = [node for node in preferred_order if node in component_set]
    remainder = sorted(node for node in component_set if node not in set(ordered))
    return ordered + remainder


def build_gauss_seidel_wrapper_specs(
    loop_components: List[List[str]],
    graph: OrchestrationGraph,
    *,
    preferred_order: Sequence[str] | None = None,
) -> List[Dict[str, object]]:
    wrappers: List[Dict[str, object]] = []
    preferred = [str(node).strip() for node in list(preferred_order or []) if str(node).strip()]
    for index, component in enumerate(loop_components):
        node_order = _ordered_loop_component(component, preferred)
        loop_bindings = [
            binding
            for binding in graph.bindings
            if binding.source_fmu in node_order and binding.target_fmu in node_order
        ]
        boundary_variables = [
            f"{binding.source_fmu}.{binding.source_signal}->{binding.target_fmu}.{binding.target_signal}"
            for binding in loop_bindings
        ]
        wrappers.append(
            {
                "loop_id": f"loop_{index}",
                "nodes": node_order,
                "node_order": node_order,
                "iteration_order": [
                    {
                        "step_index": position,
                        "node": node,
                        "reads": sorted(
                            {
                                f"{binding.source_fmu}.{binding.source_signal}"
                                for binding in loop_bindings
                                if binding.target_fmu == node
                            }
                        ),
                        "writes": sorted(
                            {
                                f"{binding.target_fmu}.{binding.target_signal}"
                                for binding in loop_bindings
                                if binding.source_fmu == node
                            }
                        ),
                    }
                    for position, node in enumerate(node_order)
                ],
                "boundary_variables": boundary_variables,
                "boundary_reads": [f"{binding.source_fmu}.{binding.source_signal}" for binding in loop_bindings],
                "boundary_writes": [f"{binding.target_fmu}.{binding.target_signal}" for binding in loop_bindings],
                "convergence_signals": boundary_variables,
                "method": "gauss_seidel",
                "tol": 1e-6,
                "max_iters": 20,
                "initial_guess_policy": "last_communication_value",
                "convergence_check": {
                    "norm": "linf",
                    "signals": boundary_variables,
                    "tol": 1e-6,
                },
                "runtime_policy": {
                    "kind": "fixed_point_iteration",
                    "iterate_until_converged": True,
                    "fail_on_nonconvergence": False,
                    "fallback": "accept_last_iterate",
                },
            }
        )
    return wrappers
