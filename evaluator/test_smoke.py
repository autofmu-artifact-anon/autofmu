from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evaluator.dataset_adapter import list_case_records
from evaluator.runner import (
    _bootstrap_reference_solution_metadata,
    _bootstrap_source_orchestration,
    _summary_row,
    build_cross_method_summary,
    build_shared_success_summary,
    run_experiment,
)
from evaluator.scoring import _evaluate_acceptance_criteria, aggregate_experiment_metrics, score_decision
from evaluator.types import CaseEvaluation, EvaluationSpec, ReferencePack
from pipeline.dataset_loader import load_case_from_dataset


class EvaluatorSmokeTest(unittest.TestCase):
    def _write_temp_dataset(self, root: Path, *, cases: list[dict[str, Any]]) -> Path:
        dataset_root = root / "dataset"
        for case in cases:
            case_id = str(case["case_id"])
            case_root = dataset_root / "cases" / case_id
            case_root.mkdir(parents=True, exist_ok=True)

            ground_truth_asset_ids = [str(item) for item in list(case.get("ground_truth_asset_ids") or []) if str(item)]
            if not ground_truth_asset_ids:
                ground_truth_fmu_count = int(case.get("ground_truth_fmu_count") or 1)
                ground_truth_asset_ids = [
                    f"{case_id}__asset_{index + 1}"
                    for index in range(max(ground_truth_fmu_count, 1))
                ]

            payload = {
                "case_id": case_id,
                "source_type": str(case.get("source_type") or "benchmark_single_fmu_case"),
                "title": str(case.get("title") or case_id),
                "ground_truth_asset_ids": ground_truth_asset_ids,
                "candidate_asset_ids": [
                    str(item)
                    for item in list(case.get("candidate_asset_ids") or ground_truth_asset_ids)
                    if str(item)
                ],
                "solution_relpath": str(case.get("solution_relpath") or "solution.json"),
                "evaluation_artifacts": {
                    "supports_execution_metrics": bool(case.get("supports_execution_metrics", True)),
                    "supports_numerical_fidelity": bool(case.get("supports_numerical_fidelity", True)),
                    "supports_decision_accuracy": bool(case.get("supports_decision_accuracy", True)),
                },
            }
            if case.get("case_category") is not None:
                payload["case_category"] = str(case["case_category"])
            if case.get("ground_truth_port_count") is not None:
                payload["complexity_metrics"] = {
                    "ground_truth_port_count": int(case["ground_truth_port_count"]),
                }
            (case_root / "case.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return dataset_root

    def _write_experiment_summary(
        self,
        root: Path,
        *,
        experiment_id: str,
        bundle_name: str,
        dataset_root: Path,
        case_rows: list[dict[str, Any]],
    ) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        payload = {
            "experiment_id": experiment_id,
            "bundle_name": bundle_name,
            "dataset_root": dataset_root.resolve().as_posix(),
            "case_rows": case_rows,
        }
        (root / "experiment_summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return root

    def test_list_case_records_uses_normalized_dataset(self) -> None:
        records = list_case_records("dataset", case_ids=["case_bench_fmu-001280"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].case_id, "case_bench_fmu-001280")
        self.assertTrue(records[0].case_root.exists())
        self.assertEqual(records[0].case_category, "simple")
        self.assertEqual(records[0].ground_truth_fmu_count, 1)
        self.assertTrue(records[0].supports_execution_metrics)
        self.assertTrue(records[0].supports_numerical_fidelity)
        self.assertTrue(records[0].supports_decision_accuracy)

    def test_list_case_records_marks_multi_fmu_cases(self) -> None:
        records = list_case_records("dataset", case_ids=["case_dtaas_three_tank"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].case_category, "complex")
        self.assertGreater(records[0].ground_truth_fmu_count, 1)

    def test_list_case_records_promotes_high_port_single_fmu_cases_to_complex(self) -> None:
        records = list_case_records("dataset", case_ids=["case_bench_fmu-002341"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].case_category, "complex")
        self.assertEqual(records[0].ground_truth_fmu_count, 1)

    def test_aggregate_experiment_metrics_adds_trimmed_numerical_fidelity(self) -> None:
        case_rows = []
        for index in range(19):
            case_rows.append(
                {
                    "case_id": f"case_{index:02d}",
                    "ok": True,
                    "metrics": {
                        "retrieval": {"top1_hit": True, "topk_hit": True},
                        "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                        "numerical_fidelity": {"supported": True, "mae": 1.0, "rmse": 2.0, "nrmse": 0.1},
                        "decision": {"supported": True, "correct": True},
                    },
                }
            )
        case_rows.append(
            {
                "case_id": "case_outlier",
                "ok": True,
                "metrics": {
                    "retrieval": {"top1_hit": True, "topk_hit": True},
                    "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                    "numerical_fidelity": {"supported": True, "mae": 101.0, "rmse": 202.0, "nrmse": 1.1},
                    "decision": {"supported": True, "correct": True},
                },
            }
        )

        aggregate = aggregate_experiment_metrics(case_rows)

        self.assertAlmostEqual(aggregate["mae"], 6.0)
        self.assertAlmostEqual(aggregate["rmse"], 12.0)
        self.assertAlmostEqual(aggregate["nrmse"], 0.15)
        self.assertEqual(aggregate["trimmed_mae"], 1.0)
        self.assertEqual(aggregate["trimmed_rmse"], 2.0)
        self.assertEqual(aggregate["trimmed_nrmse"], 0.1)
        self.assertEqual(
            aggregate["trimmed_numerical_fidelity"]["mae"]["excluded_case_ids"],
            ["case_outlier"],
        )
        self.assertEqual(
            aggregate["trimmed_numerical_fidelity"]["mae"]["case_count_after_trim"],
            19,
        )

    def test_run_single_benchmark_case_scores_equivalence_class_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = EvaluationSpec(
                dataset_root="dataset",
                manifest_path="pipeline/resources/fmu_library/manifest.json",
                bundle_name="current_pipeline",
                case_ids=["case_bench_fmu-001280"],
                out_root=tmpdir,
                stage1_config={"confidence": 0.9, "max_candidates": 3},
                stage2_config={"max_revisions": 2, "top_m_per_task": 3, "max_port_candidates": 4},
            )
            summary = run_experiment(spec)
            case_row = summary.case_rows[0]
            self.assertTrue(case_row.ok)
            self.assertTrue(case_row.metrics["retrieval"]["top1_hit"])
            self.assertTrue(case_row.metrics["retrieval"]["topk_hit"])
            self.assertEqual(case_row.metrics["retrieval"]["oracle_mode"], "equivalence_class")
            self.assertTrue(case_row.metrics["execution"]["success"])
            self.assertTrue(case_row.metrics["numerical_fidelity"]["supported"])
            self.assertTrue(case_row.metrics["decision"]["supported"])

    def test_run_benchmark_case_001572_preserves_explicit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = EvaluationSpec(
                dataset_root="dataset",
                manifest_path="pipeline/resources/fmu_library/manifest.json",
                bundle_name="current_pipeline",
                case_ids=["case_bench_fmu-001572"],
                out_root=tmpdir,
                stage1_config={"confidence": 0.9, "max_candidates": 3},
                stage2_config={"max_revisions": 2, "top_m_per_task": 3, "max_port_candidates": 4},
            )
            summary = run_experiment(spec)
            case_row = summary.case_rows[0]
            self.assertTrue(case_row.ok)
            self.assertTrue(case_row.metrics["retrieval"]["top1_hit"])
            self.assertTrue(case_row.metrics["retrieval"]["topk_hit"])
            self.assertTrue(case_row.metrics["numerical_fidelity"]["supported"])
            self.assertTrue(case_row.metrics["decision"]["supported"])

    def test_run_dtaas_three_tank_case_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = EvaluationSpec(
                dataset_root="dataset",
                manifest_path="pipeline/resources/fmu_library/manifest.json",
                bundle_name="current_pipeline",
                case_ids=["case_dtaas_three_tank"],
                out_root=tmpdir,
                stage1_config={"confidence": 0.9, "max_candidates": 5},
                stage2_config={"max_revisions": 3, "top_m_per_task": 5, "max_port_candidates": 8},
            )
            summary = run_experiment(spec)
            case_row = summary.case_rows[0]
            self.assertTrue(case_row.ok)
            self.assertTrue(case_row.metrics["retrieval"]["top1_hit"])
            self.assertTrue(case_row.metrics["execution"]["success"])
            self.assertTrue(case_row.metrics["numerical_fidelity"]["supported"])
            self.assertTrue(case_row.metrics["decision"]["supported"])

    def test_source_orchestration_bootstrap_preserves_source_schedule_for_exact_match_cases(self) -> None:
        loaded = load_case_from_dataset("case_dtaas_water_tank_fi", dataset_root="dataset")

        bootstrap = _bootstrap_source_orchestration(
            loaded=loaded,
            selected_asset_ids=loaded.solution_payload["selected_asset_ids"],
            connections=loaded.solution_payload["connections"],
            current_schedule={"async_edges": [{"async": True}]},
        )

        self.assertIn("parameter_overrides", bootstrap["extensions"])
        self.assertEqual(bootstrap["schedule"]["kind"], "co_simulation")
        self.assertEqual(bootstrap["schedule"]["step_size"], 0.1)

        sync_case = _bootstrap_source_orchestration(
            loaded=loaded,
            selected_asset_ids=loaded.solution_payload["selected_asset_ids"],
            connections=loaded.solution_payload["connections"],
            current_schedule={"async_edges": []},
        )

        self.assertIn("parameter_overrides", sync_case["extensions"])
        self.assertEqual(sync_case["schedule"]["kind"], "co_simulation")
        self.assertEqual(sync_case["schedule"]["step_size"], 0.1)

    def test_source_orchestration_bootstrap_preserves_monitored_output_order(self) -> None:
        loaded = load_case_from_dataset("case_dtaas_mass_spring_damper_monitor", dataset_root="dataset")

        bootstrap = _bootstrap_source_orchestration(
            loaded=loaded,
            selected_asset_ids=loaded.solution_payload["selected_asset_ids"],
            connections=loaded.solution_payload["connections"],
            current_schedule={"async_edges": []},
        )

        monitored = bootstrap["monitored_outputs"]
        self.assertEqual(monitored[2]["name"], "y")
        self.assertEqual(monitored[2]["source"], "asset_dtaas_mass_spring_damper_monitor__rti1.y")
        self.assertEqual(monitored[3]["name"], "y")
        self.assertEqual(monitored[3]["source"], "asset_dtaas_mass_spring_damper_monitor__rti2.y")

    def test_reference_solution_bootstrap_preserves_single_fmu_benchmark_metadata(self) -> None:
        loaded = load_case_from_dataset("case_bench_fmu-001284", dataset_root="dataset")

        bootstrap = _bootstrap_reference_solution_metadata(
            loaded=loaded,
            selected_asset_ids=loaded.solution_payload["selected_asset_ids"],
            connections=loaded.solution_payload["connections"],
        )

        self.assertEqual(bootstrap["schedule"]["kind"], "single_fmu")
        self.assertEqual(bootstrap["schedule"]["step_size"], 0)
        self.assertEqual(len(bootstrap["external_inputs"]), 4)
        self.assertEqual(bootstrap["monitored_outputs"][0]["name"], "real_continuous_out")

    def test_summary_row_prefers_decision_correct_over_passed(self) -> None:
        row = _summary_row(
            CaseEvaluation(
                case_id="case_x",
                source_type="manual_multi_fmu_case",
                case_category="complex",
                ground_truth_fmu_count=1,
                ok=True,
                bundle_name="current_pipeline",
                artifact_root="/tmp/case_x",
                stage_status={},
                execution_status={},
                metrics={
                    "retrieval": {"top1_hit": True, "topk_hit": True},
                    "execution": {"success": True, "execution_time_seconds": 1.0},
                    "numerical_fidelity": {"mae": 0.0, "rmse": 0.0, "nrmse": 0.0},
                    "decision": {"passed": False, "correct": True},
                },
                artifact_paths={},
            )
        )

        self.assertTrue(row["decision_correct"])

    def test_resume_reuses_completed_case_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = EvaluationSpec(
                dataset_root="dataset",
                manifest_path="pipeline/resources/fmu_library/manifest.json",
                bundle_name="current_pipeline",
                case_ids=["case_bench_fmu-001280"],
                out_root=tmpdir,
                experiment_id="resume_smoke",
                resume=False,
            )
            first = run_experiment(spec)
            self.assertEqual(first.succeeded, 1)
            resumed = run_experiment(EvaluationSpec(**{**spec.__dict__, "resume": True}))
            self.assertEqual(resumed.succeeded, 1)
            self.assertIn("resumed_from_artifacts", resumed.case_rows[0].notes)

    def test_timeout_marks_case_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = EvaluationSpec(
                dataset_root="dataset",
                manifest_path="pipeline/resources/fmu_library/manifest.json",
                bundle_name="current_pipeline",
                case_ids=["case_bench_fmu-001280"],
                out_root=tmpdir,
                timeout_seconds=0.1,
            )
            with patch(
                "evaluator.runner.execute_case",
                return_value={
                    "schema": "PIPELINE_EXECUTION_RESULT_V2",
                    "case_id": "case_bench_fmu-001280",
                    "selected_asset_ids": [],
                    "success": False,
                    "backend": "timeout",
                    "runtime_mode": "timed_out",
                    "execution_time_seconds": 0.1,
                    "generated_trajectory_path": "",
                    "generated_trajectory_sample_count": 0,
                    "supports_execution_metrics": True,
                    "supports_numerical_fidelity": True,
                    "supports_decision_accuracy": True,
                    "observed_signals": [],
                    "time_column": "time",
                    "signal_columns": [],
                    "supported_metrics": {
                        "execution": True,
                        "numerical_fidelity": True,
                        "decision_accuracy": True,
                    },
                    "decision_evidence": {},
                    "warnings": [],
                    "timed_out": True,
                    "timeout_seconds": 0.1,
                    "error": "TimeoutError: execution exceeded 0.100 seconds",
                },
            ):
                summary = run_experiment(spec)
            case_row = summary.case_rows[0]
            self.assertFalse(case_row.ok)
            self.assertEqual(case_row.error, "TimeoutError: execution exceeded 0.100 seconds")
            self.assertEqual(summary.failed, 1)

    def test_acceptance_criteria_dsl_on_temp_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "trajectory.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "theta_rad", "x_m", "x_ref_m", "force_cmd_N"])
                writer.writeheader()
                writer.writerow({"time": 0, "theta_rad": 0.0, "x_m": 0.0, "x_ref_m": 0.0, "force_cmd_N": 0.0})
                writer.writerow({"time": 10, "theta_rad": 0.02, "x_m": 0.1, "x_ref_m": 0.1, "force_cmd_N": 1.0})
                writer.writerow({"time": 11, "theta_rad": 0.01, "x_m": 0.2, "x_ref_m": 0.2, "force_cmd_N": 1.5})
            reference = ReferencePack(
                case_id="tmp_manual_case",
                retrieval_reference={},
                solution={},
                verification_requirement={
                    "criteria": [
                        {"metric": "max(abs(theta_rad))", "operator": "<=", "value": 0.35},
                        {"metric": "max(abs(x_m))", "operator": "<=", "value": 1.5},
                        {"metric": "within_range(force_cmd_N)", "operator": "in", "value": [-15.0, 15.0]},
                        {"metric": "abs(theta_rad) at t=10s", "operator": "<=", "value": 0.08},
                        {"metric": "abs(x_m - x_ref_m) at t=11s", "operator": "<=", "value": 0.15},
                    ],
                    "time_column_aliases": ["time"],
                    "signal_aliases": {},
                },
                verification_result={"status": "available", "conclusion": "pass"},
                trajectory_manifest={"time_column": "time", "signal_columns": ["theta_rad", "x_m", "x_ref_m", "force_cmd_N"]},
                ground_truth_trajectory_path=csv_path.as_posix(),
                supports_execution_metrics=True,
                supports_numerical_fidelity=True,
                supports_decision_accuracy=True,
            )
            evaluated = _evaluate_acceptance_criteria(csv_path, reference)
            self.assertTrue(evaluated["supported"])
            self.assertEqual(evaluated["conclusion"], "pass")

    def test_score_decision_trajectory_tolerance_uses_loose_nrmse_gate(self) -> None:
        reference = ReferencePack(
            case_id="tmp_bench_case",
            retrieval_reference={},
            solution={},
            verification_requirement={"decision_rule": {"kind": "trajectory_tolerance", "tolerance": 1e-6}},
            verification_result={"status": "available", "conclusion": "pass"},
            trajectory_manifest={},
            ground_truth_trajectory_path="reference.csv",
            supports_execution_metrics=True,
            supports_numerical_fidelity=True,
            supports_decision_accuracy=True,
        )
        execution_result = {"success": True, "generated_trajectory_path": "generated.csv"}

        at_threshold = score_decision(
            reference=reference,
            execution_result=execution_result,
            numerical_metrics={"nrmse": 0.05, "max_abs_error": 0.2},
        )
        above_threshold = score_decision(
            reference=reference,
            execution_result=execution_result,
            numerical_metrics={"nrmse": 0.051, "max_abs_error": 0.2},
        )

        self.assertTrue(at_threshold["supported"])
        self.assertTrue(at_threshold["passed"])
        self.assertTrue(at_threshold["correct"])
        self.assertEqual(at_threshold["predicted_conclusion"], "pass")
        self.assertEqual(at_threshold["evidence"]["policy_threshold"], 0.05)
        self.assertFalse(above_threshold["passed"])
        self.assertFalse(above_threshold["correct"])
        self.assertEqual(above_threshold["predicted_conclusion"], "fail")

    def test_score_decision_counts_fail_matching_fail_reference_as_correct(self) -> None:
        reference = ReferencePack(
            case_id="tmp_bench_case",
            retrieval_reference={},
            solution={},
            verification_requirement={"decision_rule": {"kind": "trajectory_tolerance"}},
            verification_result={"status": "available", "conclusion": "fail"},
            trajectory_manifest={},
            ground_truth_trajectory_path="reference.csv",
            supports_execution_metrics=True,
            supports_numerical_fidelity=True,
            supports_decision_accuracy=True,
        )
        execution_result = {"success": True, "generated_trajectory_path": "generated.csv"}

        scored = score_decision(
            reference=reference,
            execution_result=execution_result,
            numerical_metrics={"nrmse": 0.2, "max_abs_error": 1.0},
        )

        self.assertTrue(scored["supported"])
        self.assertEqual(scored["predicted_conclusion"], "fail")
        self.assertEqual(scored["reference_conclusion"], "fail")
        self.assertFalse(scored["passed"])
        self.assertTrue(scored["correct"])

    def test_score_decision_acceptance_criteria_counts_only_pass_as_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "trajectory.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "theta_rad"])
                writer.writeheader()
                writer.writerow({"time": 0, "theta_rad": 0.0})
                writer.writerow({"time": 1, "theta_rad": 0.2})

            reference = ReferencePack(
                case_id="tmp_manual_case",
                retrieval_reference={},
                solution={},
                verification_requirement={
                    "decision_rule": {"kind": "acceptance_criteria"},
                    "criteria": [{"metric": "max(abs(theta_rad))", "operator": "<=", "value": 0.1}],
                    "time_column_aliases": ["time"],
                    "signal_aliases": {},
                },
                verification_result={"status": "available", "conclusion": "pass"},
                trajectory_manifest={"time_column": "time", "signal_columns": ["theta_rad"]},
                ground_truth_trajectory_path=csv_path.as_posix(),
                supports_execution_metrics=True,
                supports_numerical_fidelity=True,
                supports_decision_accuracy=True,
            )

            scored = score_decision(
                reference=reference,
                execution_result={"success": True, "generated_trajectory_path": csv_path.as_posix()},
                numerical_metrics={"nrmse": 0.0},
            )

        self.assertTrue(scored["supported"])
        self.assertFalse(scored["passed"])
        self.assertFalse(scored["correct"])
        self.assertEqual(scored["predicted_conclusion"], "fail")

    def test_acceptance_criteria_fails_when_trajectory_does_not_cover_point_in_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "trajectory.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "theta_rad"])
                writer.writeheader()
                writer.writerow({"time": 0, "theta_rad": 0.0})
                writer.writerow({"time": 1, "theta_rad": 0.0})

            reference = ReferencePack(
                case_id="tmp_manual_case",
                retrieval_reference={},
                solution={},
                verification_requirement={
                    "decision_rule": {"kind": "acceptance_criteria"},
                    "criteria": [{"metric": "abs(theta_rad) at t=10s", "operator": "<=", "value": 0.08}],
                    "time_column_aliases": ["time"],
                    "signal_aliases": {},
                },
                verification_result={"status": "available", "conclusion": "pass"},
                trajectory_manifest={"time_column": "time", "signal_columns": ["theta_rad"]},
                ground_truth_trajectory_path=csv_path.as_posix(),
                declared_scenario_window={"start_time": 0.0, "stop_time": 20.0},
                supports_execution_metrics=True,
                supports_numerical_fidelity=True,
                supports_decision_accuracy=True,
            )

            evaluated = _evaluate_acceptance_criteria(csv_path, reference)

        self.assertTrue(evaluated["supported"])
        self.assertEqual(evaluated["conclusion"], "fail")
        self.assertIn("abs(theta_rad) at t=10s", evaluated["coverage_failures"])
        self.assertEqual(evaluated["criterion_results"][0]["error"], "insufficient_time_coverage")

    def test_score_decision_acceptance_criteria_fails_on_initial_condition_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "trajectory.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "theta_rad"])
                writer.writeheader()
                writer.writerow({"time": 0, "theta_rad": 0.10})
                writer.writerow({"time": 20, "theta_rad": 0.01})

            reference = ReferencePack(
                case_id="tmp_manual_case",
                retrieval_reference={},
                solution={},
                verification_requirement={
                    "decision_rule": {"kind": "acceptance_criteria"},
                    "criteria": [{"metric": "max(abs(theta_rad))", "operator": "<=", "value": 0.35}],
                    "time_column_aliases": ["time"],
                    "signal_aliases": {},
                },
                verification_result={"status": "available", "conclusion": "pass"},
                trajectory_manifest={"time_column": "time", "signal_columns": ["theta_rad"]},
                ground_truth_trajectory_path=csv_path.as_posix(),
                declared_scenario_window={"start_time": 0.0, "stop_time": 20.0},
                declared_initial_conditions={"theta_rad": 0.12},
                supports_execution_metrics=True,
                supports_numerical_fidelity=True,
                supports_decision_accuracy=True,
            )

            scored = score_decision(
                reference=reference,
                execution_result={"success": True, "generated_trajectory_path": csv_path.as_posix()},
                numerical_metrics={"nrmse": 0.0},
            )

        self.assertTrue(scored["supported"])
        self.assertFalse(scored["passed"])
        self.assertFalse(scored["correct"])
        self.assertEqual(scored["predicted_conclusion"], "fail")
        self.assertEqual(
            scored["evidence"]["initial_condition_results"][0]["error"],
            "initial_condition_mismatch",
        )

    def test_aggregate_metrics_handle_topk_hit_without_top1(self) -> None:
        aggregate = aggregate_experiment_metrics(
            [
                {
                    "ok": True,
                    "metrics": {
                        "retrieval": {"top1_hit": False, "topk_hit": True},
                        "execution": {"supported": True, "success": True, "execution_time_seconds": 1.25},
                        "numerical_fidelity": {"supported": False, "mae": None, "rmse": None, "nrmse": None},
                        "decision": {"supported": False, "correct": None},
                    },
                },
                {
                    "ok": False,
                    "metrics": {
                        "retrieval": {"top1_hit": False, "topk_hit": False},
                        "execution": {"supported": False, "success": None, "execution_time_seconds": None},
                        "numerical_fidelity": {"supported": False, "mae": None, "rmse": None, "nrmse": None},
                        "decision": {"supported": False, "correct": None},
                    },
                },
            ]
        )
        self.assertEqual(aggregate["top1_hit_rate"], 0.0)
        self.assertEqual(aggregate["topk_hit_rate"], 0.5)
        self.assertEqual(aggregate["execution_success_count"], 1)
        self.assertEqual(aggregate["execution_cases"], 1)
        self.assertEqual(aggregate["execution_success_rate"], 0.5)

    def test_score_decision_supports_rule_evaluable_case_without_reference_label(self) -> None:
        reference = ReferencePack(
            case_id="case_x",
            retrieval_reference={},
            solution={},
            verification_requirement={"decision_rule": {"kind": "trajectory_tolerance"}},
            verification_result={"status": "available", "conclusion": "unknown"},
            trajectory_manifest={},
            ground_truth_trajectory_path="/tmp/fake.csv",
            input_trajectory_path=None,
            supports_execution_metrics=True,
            supports_numerical_fidelity=True,
            supports_decision_accuracy=True,
            metadata={},
        )
        decision = score_decision(
            reference=reference,
            execution_result={"success": True, "generated_trajectory_path": "/tmp/fake.csv"},
            numerical_metrics={"nrmse": 0.01, "max_abs_error": 0.1},
        )
        self.assertTrue(decision["supported"])
        self.assertTrue(decision["passed"])
        self.assertTrue(decision["correct"])
        self.assertEqual(decision["evidence"]["decision_policy_mode"], "rule_evaluable_without_reference_label")

    def test_cross_method_summary_penalizes_missing_numerical_metrics_and_splits_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root = self._write_temp_dataset(
                tmp_path,
                cases=[
                    {"case_id": "case_simple", "case_category": "simple", "ground_truth_fmu_count": 1},
                    {"case_id": "case_complex", "case_category": "complex", "ground_truth_fmu_count": 2},
                ],
            )
            experiment_root_a = self._write_experiment_summary(
                tmp_path / "exp_a",
                experiment_id="exp_a",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.1, "rmse": 0.2, "nrmse": 0.3},
                            "decision": {"supported": True, "correct": True},
                        },
                    },
                    {
                        "case_id": "case_complex",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": False, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 2.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.4, "rmse": 0.5, "nrmse": 0.6},
                            "decision": {"supported": True, "correct": False},
                        },
                    },
                ],
            )
            experiment_root_b = self._write_experiment_summary(
                tmp_path / "exp_b",
                experiment_id="exp_b",
                bundle_name="baseline_b1_rule_sequential",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": False, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 3.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.7, "rmse": 0.8, "nrmse": 0.9},
                            "decision": {"supported": True, "correct": False},
                        },
                    },
                    {
                        "case_id": "case_complex",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": False, "topk_hit": False},
                            "execution": {"supported": True, "success": False, "execution_time_seconds": 4.0},
                            "numerical_fidelity": {"supported": False, "mae": None, "rmse": None, "nrmse": None},
                            "decision": {"supported": False, "correct": None},
                        },
                    },
                ],
            )

            summary = build_cross_method_summary([experiment_root_a, experiment_root_b])
            self.assertEqual(summary["schema"], "EVALUATOR_CROSS_METHOD_SUMMARY_V2")
            self.assertEqual(summary["aggregation_mode"], "casewise_max_penalty")
            self.assertEqual(summary["aligned_case_count"], 2)
            self.assertEqual(summary["common_case_count"], 2)
            self.assertEqual(summary["cross_method_execution_time_case_count"], 2)
            self.assertEqual(summary["cross_method_numerical_case_count"], 2)

            aggregate_a = summary["experiments"][0]["cross_method_aggregate_metrics"]
            aggregate_b = summary["experiments"][1]["cross_method_aggregate_metrics"]
            self.assertEqual(aggregate_a["by_case_category"]["simple"]["cases_scored"], 1)
            self.assertEqual(aggregate_a["by_case_category"]["complex"]["cases_scored"], 1)
            self.assertEqual(aggregate_a["by_case_category"]["simple"]["mae"], 0.1)
            self.assertEqual(aggregate_a["by_case_category"]["complex"]["mae"], 0.4)
            self.assertEqual(aggregate_a["mean_execution_time_seconds"], 1.5)
            self.assertEqual(aggregate_a["by_case_category"]["simple"]["decision_accuracy"], 1.0)
            self.assertEqual(aggregate_a["by_case_category"]["complex"]["decision_accuracy"], 0.0)

            self.assertEqual(aggregate_b["execution_cases"], 2)
            self.assertEqual(aggregate_b["mean_execution_time_seconds"], 2.5)
            self.assertEqual(aggregate_b["by_case_category"]["simple"]["mae"], 0.7)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["mae"], 0.4)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["rmse"], 0.5)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["nrmse"], 0.6)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["execution_success_rate"], 0.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["mean_execution_time_seconds"], 2.0)
            self.assertEqual(aggregate_b["by_case_category"]["simple"]["decision_accuracy"], 0.0)

            legacy_summary = build_shared_success_summary([experiment_root_a, experiment_root_b])
            self.assertEqual(legacy_summary["schema"], "EVALUATOR_CROSS_METHOD_SUMMARY_V2")

    def test_cross_method_summary_uses_aligned_dataset_denominator_for_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root = self._write_temp_dataset(
                tmp_path,
                cases=[
                    {"case_id": "case_simple", "case_category": "simple", "ground_truth_fmu_count": 1},
                    {"case_id": "case_complex", "case_category": "complex", "ground_truth_fmu_count": 2},
                ],
            )
            experiment_root_a = self._write_experiment_summary(
                tmp_path / "exp_a",
                experiment_id="exp_a",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 2.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.1, "rmse": 0.2, "nrmse": 0.3},
                            "decision": {"supported": True, "correct": True},
                        },
                    },
                    {
                        "case_id": "case_complex",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": False, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 5.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.4, "rmse": 0.5, "nrmse": 0.6},
                            "decision": {"supported": True, "correct": False},
                        },
                    },
                ],
            )
            experiment_root_b = self._write_experiment_summary(
                tmp_path / "exp_b",
                experiment_id="exp_b",
                bundle_name="baseline_b2_rule",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.2, "rmse": 0.3, "nrmse": 0.4},
                            "decision": {"supported": True, "correct": True},
                        },
                    }
                ],
            )

            summary = build_cross_method_summary([experiment_root_a, experiment_root_b])
            aggregate_b = summary["experiments"][1]["cross_method_aggregate_metrics"]

            self.assertEqual(summary["aligned_case_count"], 2)
            self.assertEqual(summary["common_case_count"], 1)
            self.assertEqual(aggregate_b["cases_scored"], 2)
            self.assertEqual(aggregate_b["supported_case_count"], 2)
            self.assertEqual(aggregate_b["scored_case_count"], 2)
            self.assertEqual(aggregate_b["top1_hit_rate"], 0.5)
            self.assertEqual(aggregate_b["topk_hit_rate"], 0.5)
            self.assertEqual(aggregate_b["execution_success_rate"], 0.5)
            self.assertEqual(aggregate_b["decision_accuracy"], 0.5)
            self.assertEqual(aggregate_b["execution_cases"], 2)
            self.assertEqual(aggregate_b["mean_execution_time_seconds"], 3.0)
            self.assertEqual(aggregate_b["by_case_category"]["simple"]["cases_scored"], 1)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["cases_scored"], 1)
            self.assertEqual(aggregate_b["by_case_category"]["simple"]["top1_hit_rate"], 1.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["top1_hit_rate"], 0.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["execution_success_rate"], 0.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["decision_accuracy"], 0.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["execution_cases"], 1)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["mean_execution_time_seconds"], 5.0)

    def test_cross_method_summary_trims_global_extreme_numerical_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            case_defs = [
                {"case_id": f"case_{index:02d}", "case_category": "simple", "ground_truth_fmu_count": 1}
                for index in range(19)
            ] + [
                {"case_id": "case_outlier", "case_category": "simple", "ground_truth_fmu_count": 1}
            ]
            dataset_root = self._write_temp_dataset(tmp_path, cases=case_defs)

            experiment_root_a = self._write_experiment_summary(
                tmp_path / "exp_a",
                experiment_id="exp_a",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": case["case_id"],
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": (
                                {"supported": True, "mae": 101.0, "rmse": 202.0, "nrmse": 1.1}
                                if case["case_id"] == "case_outlier"
                                else {"supported": True, "mae": 1.0, "rmse": 2.0, "nrmse": 0.1}
                            ),
                            "decision": {"supported": True, "correct": True},
                        },
                    }
                    for case in case_defs
                ],
            )
            experiment_root_b = self._write_experiment_summary(
                tmp_path / "exp_b",
                experiment_id="exp_b",
                bundle_name="baseline_b1_rule_sequential",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": case["case_id"],
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": (
                                {"supported": False, "mae": None, "rmse": None, "nrmse": None}
                                if case["case_id"] == "case_outlier"
                                else {"supported": True, "mae": 2.0, "rmse": 4.0, "nrmse": 0.2}
                            ),
                            "decision": {"supported": True, "correct": True},
                        },
                    }
                    for case in case_defs
                ],
            )

            summary = build_cross_method_summary([experiment_root_a, experiment_root_b])
            reference = summary["trimmed_numerical_fidelity_reference"]
            aggregate_a = summary["experiments"][0]["cross_method_aggregate_metrics"]
            aggregate_b = summary["experiments"][1]["cross_method_aggregate_metrics"]

            self.assertEqual(reference["mae"]["excluded_case_ids"], ["case_outlier"])
            self.assertAlmostEqual(aggregate_a["mae"], 6.0)
            self.assertAlmostEqual(aggregate_b["mae"], 6.95)
            self.assertEqual(aggregate_a["trimmed_mae"], 1.0)
            self.assertEqual(aggregate_b["trimmed_mae"], 2.0)
            self.assertEqual(
                aggregate_a["trimmed_numerical_fidelity"]["mae"]["excluded_case_ids"],
                ["case_outlier"],
            )
            self.assertEqual(
                aggregate_b["trimmed_numerical_fidelity"]["mae"]["excluded_case_ids"],
                ["case_outlier"],
            )

    def test_cross_method_summary_penalizes_unknown_decisions_on_aligned_case_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root = self._write_temp_dataset(
                tmp_path,
                cases=[
                    {"case_id": "case_simple", "case_category": "simple", "ground_truth_fmu_count": 1},
                    {"case_id": "case_complex", "case_category": "complex", "ground_truth_fmu_count": 2},
                ],
            )
            experiment_root_a = self._write_experiment_summary(
                tmp_path / "exp_a",
                experiment_id="exp_a",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.1, "rmse": 0.1, "nrmse": 0.1},
                            "decision": {"supported": True, "correct": True},
                        },
                    },
                    {
                        "case_id": "case_complex",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.2, "rmse": 0.2, "nrmse": 0.2},
                            "decision": {"supported": True, "correct": True},
                        },
                    },
                ],
            )
            experiment_root_b = self._write_experiment_summary(
                tmp_path / "exp_b",
                experiment_id="exp_b",
                bundle_name="baseline_b1_rule_sequential",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_simple",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.3, "rmse": 0.3, "nrmse": 0.3},
                            "decision": {"supported": True, "correct": True},
                        },
                    },
                    {
                        "case_id": "case_complex",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.4, "rmse": 0.4, "nrmse": 0.4},
                            "decision": {"supported": False, "correct": None},
                        },
                    },
                ],
            )

            summary = build_cross_method_summary([experiment_root_a, experiment_root_b])
            aggregate_b = summary["experiments"][1]["cross_method_aggregate_metrics"]

            self.assertEqual(summary["aligned_case_count"], 2)
            self.assertEqual(aggregate_b["decision_cases"], 2)
            self.assertEqual(aggregate_b["decision_accuracy"], 0.5)
            self.assertEqual(aggregate_b["by_case_category"]["simple"]["decision_accuracy"], 1.0)
            self.assertEqual(aggregate_b["by_case_category"]["complex"]["decision_accuracy"], 0.0)

    def test_cross_method_summary_requires_matching_dataset_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root_a = self._write_temp_dataset(
                tmp_path / "left",
                cases=[{"case_id": "case_simple", "case_category": "simple", "ground_truth_fmu_count": 1}],
            )
            dataset_root_b = self._write_temp_dataset(
                tmp_path / "right",
                cases=[{"case_id": "case_simple", "case_category": "simple", "ground_truth_fmu_count": 1}],
            )
            experiment_root_a = self._write_experiment_summary(
                tmp_path / "exp_a",
                experiment_id="exp_a",
                bundle_name="current_pipeline",
                dataset_root=dataset_root_a,
                case_rows=[],
            )
            experiment_root_b = self._write_experiment_summary(
                tmp_path / "exp_b",
                experiment_id="exp_b",
                bundle_name="baseline_b1_rule_sequential",
                dataset_root=dataset_root_b,
                case_rows=[],
            )

            with self.assertRaisesRegex(ValueError, "same dataset_root"):
                build_cross_method_summary([experiment_root_a, experiment_root_b])

    def test_cross_method_summary_remaps_legacy_single_fmu_label_to_complex_when_dataset_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root = self._write_temp_dataset(
                tmp_path,
                cases=[
                    {"case_id": "case_high_port", "case_category": "complex", "ground_truth_fmu_count": 1},
                ],
            )
            experiment_root = self._write_experiment_summary(
                tmp_path / "exp",
                experiment_id="exp",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_high_port",
                        "case_category": "single_fmu",
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.2, "rmse": 0.3, "nrmse": 0.4},
                            "decision": {"supported": True, "correct": True},
                        },
                    }
                ],
            )

            summary = build_cross_method_summary([experiment_root])
            aggregate = summary["experiments"][0]["cross_method_aggregate_metrics"]

            self.assertEqual(summary["aligned_case_count"], 1)
            self.assertEqual(aggregate["by_case_category"]["simple"]["cases_scored"], 0)
            self.assertEqual(aggregate["by_case_category"]["complex"]["cases_scored"], 1)

    def test_cross_method_summary_recomputes_materialized_reference_decision_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_root = self._write_temp_dataset(
                tmp_path,
                cases=[
                    {"case_id": "case_manual_005", "case_category": "complex", "source_type": "manual_multi_fmu_case"},
                ],
            )
            artifact_root = tmp_path / "artifacts" / "case_manual_005"
            artifact_root.mkdir(parents=True, exist_ok=True)
            csv_path = artifact_root / "trajectory.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "temp_cell_C", "temp_ref_C", "pump_cmd", "soc", "v_term_V"])
                writer.writeheader()
                writer.writerow({"time": 0, "temp_cell_C": 30.0, "temp_ref_C": 35.0, "pump_cmd": 0.2, "soc": 0.85, "v_term_V": 360.0})
                writer.writerow({"time": 300, "temp_cell_C": 28.0, "temp_ref_C": 35.0, "pump_cmd": 0.0, "soc": 0.85, "v_term_V": 360.0})
                writer.writerow({"time": 900, "temp_cell_C": 28.0, "temp_ref_C": 35.0, "pump_cmd": 0.0, "soc": 0.85, "v_term_V": 360.0})

            reference_payload = {
                "case_id": "case_manual_005",
                "retrieval_reference": {},
                "solution": {},
                "verification_requirement": {
                    "decision_rule": {"kind": "acceptance_criteria"},
                    "criteria": [
                        {"metric": "max(abs(temp_cell_C - temp_ref_C))_after_t=250s", "operator": "<=", "value": 6.0},
                        {"metric": "within_range(pump_cmd)", "operator": "in", "value": [0.0, 1.0]},
                        {"metric": "within_range(soc)", "operator": "in", "value": [0.0, 1.0]},
                        {"metric": "within_range(v_term_V)", "operator": "in", "value": [250.0, 430.0]},
                    ],
                    "signal_aliases": {},
                    "scenario_window": {"start_time": 0, "stop_time": 900},
                },
                "verification_result": {"status": "available", "conclusion": "pass"},
                "trajectory_manifest": {"time_column": "time", "signal_columns": ["temp_cell_C", "temp_ref_C", "pump_cmd", "soc", "v_term_V"]},
                "declared_initial_conditions": {},
                "declared_scenario_window": {"start_time": 0, "stop_time": 900},
            }
            (artifact_root / "reference.json").write_text(
                json.dumps(reference_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            execution_payload = {
                "success": True,
                "generated_trajectory_path": csv_path.as_posix(),
                "time_column": "time",
                "signal_columns": ["temp_cell_C", "temp_ref_C", "pump_cmd", "soc", "v_term_V"],
            }
            (artifact_root / "reference_execution.raw.json").write_text(
                json.dumps(execution_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (artifact_root / "execution.raw.json").write_text(
                json.dumps(execution_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            experiment_root = self._write_experiment_summary(
                tmp_path / "exp",
                experiment_id="exp",
                bundle_name="current_pipeline",
                dataset_root=dataset_root,
                case_rows=[
                    {
                        "case_id": "case_manual_005",
                        "artifact_root": artifact_root.as_posix(),
                        "ok": True,
                        "metrics": {
                            "retrieval": {"top1_hit": True, "topk_hit": True},
                            "execution": {"supported": True, "success": True, "execution_time_seconds": 1.0},
                            "numerical_fidelity": {"supported": True, "mae": 0.1, "rmse": 0.1, "nrmse": 0.1},
                            "decision": {
                                "supported": True,
                                "correct": False,
                                "predicted_conclusion": "fail",
                                "reference_conclusion": "pass",
                            },
                        },
                    }
                ],
            )

            summary = build_cross_method_summary([experiment_root])
            aggregate = summary["experiments"][0]["cross_method_aggregate_metrics"]

            self.assertEqual(summary["aligned_case_count"], 1)
            self.assertEqual(aggregate["decision_cases"], 1)
            self.assertEqual(aggregate["decision_accuracy"], 1.0)
            self.assertEqual(aggregate["by_case_category"]["complex"]["decision_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
