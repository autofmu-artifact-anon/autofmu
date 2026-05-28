"""Stage 1 — requirement decomposition.

Public API:
- decompose(requirement: str, confidence: float = 0.9) -> list[TaskSet]

Ablation:
- decompose_ablation(requirement: str) -> list[TaskSet]
"""

from .decomposer import decompose
from .decomposer_ablation import decompose as decompose_ablation

__all__ = ["decompose", "decompose_ablation"]
