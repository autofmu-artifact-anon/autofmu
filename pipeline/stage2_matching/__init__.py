"""Stage 2 — task-set candidates + FMU library -> best (TaskSet, FMU-set).

Public API:
- match(task_sets, fmu_library) -> (task_set, fmu_set)

Ablation:
- match_ablation(task_sets, fmu_library) -> (task_set, fmu_set)
"""

from .matcher import match
from .matcher_ablation import match as match_ablation

__all__ = ["match", "match_ablation"]
