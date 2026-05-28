"""Graph utilities for Stage 3 structural checks.

We intentionally keep these lightweight (no networkx dependency).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set, Tuple


def tarjan_scc(nodes: Sequence[str], edges: Dict[str, Set[str]]) -> List[List[str]]:
    """Return strongly connected components (Tarjan).

    Args:
        nodes: all nodes.
        edges: adjacency mapping (directed).

    Returns:
        List of SCCs (each SCC is a list of node ids).
    """

    index = 0
    stack: List[str] = []
    on_stack: Set[str] = set()
    idx: Dict[str, int] = {}
    low: Dict[str, int] = {}
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in edges.get(v, set()):
            if w not in idx:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], idx[w])

        if low[v] == idx[v]:
            comp: List[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in nodes:
        if v not in idx:
            strongconnect(v)

    return sccs
