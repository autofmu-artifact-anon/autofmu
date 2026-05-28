"""Stage 3 — composition.

Public API:
- compose(task_set, fmu_set) -> SimulationConfig

Ablation:
- compose_ablation(task_set, fmu_set) -> SimulationConfig
"""

from .composer import compose
from .composer_ablation import compose as compose_ablation

__all__ = ["compose", "compose_ablation"]
