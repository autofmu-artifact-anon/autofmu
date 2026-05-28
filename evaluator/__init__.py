"""Evaluator package for batch stage-wise and end-to-end pipeline scoring."""

from .registry import available_bundles, get_bundle, register_bundle
from .runner import build_cross_method_summary, build_shared_success_summary, run_case_evaluation, run_experiment
from .types import CaseEvaluation, EvaluationSpec, ExperimentSummary, MethodBundle

__all__ = [
    "CaseEvaluation",
    "EvaluationSpec",
    "ExperimentSummary",
    "MethodBundle",
    "available_bundles",
    "build_cross_method_summary",
    "build_shared_success_summary",
    "get_bundle",
    "register_bundle",
    "run_case_evaluation",
    "run_experiment",
]
