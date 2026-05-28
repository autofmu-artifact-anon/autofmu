from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dataset.tools.validate_dataset import validate


class ValidateDatasetContractTest(unittest.TestCase):
    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _build_minimal_dataset(self, root: Path, *, include_verification_result: bool = True) -> None:
        (root / "assets" / "asset_demo").mkdir(parents=True, exist_ok=True)
        (root / "cases" / "case_demo").mkdir(parents=True, exist_ok=True)
        (root / "indexes").mkdir(parents=True, exist_ok=True)
        (root / "manifests").mkdir(parents=True, exist_ok=True)
        (root / "sources" / "demo_source").mkdir(parents=True, exist_ok=True)

        (root / "assets" / "asset_demo" / "model.fmu").write_text("dummy\n", encoding="utf-8")
        self._write_json(
            root / "assets" / "asset_demo" / "asset.json",
            {
                "schema": "UNIFIED_ASSET_V1",
                "asset_id": "asset_demo",
                "name": "Demo",
                "fmu_relpath": "model.fmu",
                "metadata_relpath": "metadata.json",
                "ports": [{"name": "y", "causality": "output"}],
            },
        )
        self._write_json(root / "assets" / "asset_demo" / "metadata.json", {"schema": "UNIFIED_FMU_METADATA_V1"})

        case_dir = root / "cases" / "case_demo"
        self._write_json(
            case_dir / "case.json",
            {
                "schema": "UNIFIED_CASE_V1",
                "case_id": "case_demo",
                "source_type": "demo_case",
                "title": "Demo",
                "requirement": {
                    "text": "Verify the demo output under the configured schedule.",
                    "signals_of_interest": ["y"],
                },
                "mbse": {"components": [], "connections": []},
                "ground_truth_asset_ids": ["asset_demo"],
                "solution_relpath": "solution.json",
                "evaluation_artifacts": {
                    "retrieval_reference_relpath": "retrieval_reference.json",
                    "verification_requirement_relpath": "verification_requirement.json",
                    "verification_result_relpath": "verification_result.json",
                    "trajectory_manifest_relpath": "trajectory_manifest.json",
                    "ground_truth_trajectory_relpath": "",
                    "input_trajectory_relpath": "",
                    "supports_execution_metrics": True,
                    "supports_numerical_fidelity": False,
                    "supports_decision_accuracy": False,
                },
                "provenance": {"source_root": "sources/demo_source"},
            },
        )
        self._write_json(
            case_dir / "solution.json",
            {
                "schema": "UNIFIED_SOLUTION_V1",
                "case_id": "case_demo",
                "selected_asset_ids": ["asset_demo"],
                "connections": [],
                "schedule": {"kind": "single_fmu", "start_time": 0.0, "stop_time": 1.0, "step_size": 0.1},
                "monitored_outputs": [{"name": "y", "source": "asset_demo.y"}],
            },
        )
        self._write_json(
            case_dir / "retrieval_reference.json",
            {
                "schema": "CASE_RETRIEVAL_REFERENCE_V1",
                "case_id": "case_demo",
                "oracle_mode": "exact_asset_set",
                "acceptable_asset_sets": [["asset_demo"]],
                "equivalence_class_id": "",
                "equivalence_reason": "",
            },
        )
        self._write_json(
            case_dir / "verification_requirement.json",
            {
                "schema": "CASE_VERIFICATION_REQUIREMENT_V1",
                "case_id": "case_demo",
                "title": "Verification requirement",
                "text": "The output y should be observable for the full run.",
                "signals": ["y"],
                "scenario_window": {"start_time": 0.0, "stop_time": 1.0, "step_size": 0.1},
                "judgement_policy": "manual_review",
                "derivation_basis": {"family": "demo"},
                "criteria": [{"metric": "observable(y)", "operator": "==", "value": True}],
                "decision_rule": {"kind": "manual_review"},
                "tolerances": {},
                "time_column_aliases": ["time", "Time"],
                "signal_aliases": {"y": ["y", "asset_demo.y"]},
            },
        )
        if include_verification_result:
            self._write_json(
                case_dir / "verification_result.json",
                {
                    "schema": "CASE_VERIFICATION_RESULT_V1",
                    "case_id": "case_demo",
                    "status": "pending_execution",
                    "conclusion": "unknown",
                    "summary": "Execution has not been run yet.",
                    "evidence_basis": {
                        "ground_truth_trajectory_relpath": "",
                        "input_trajectory_relpath": "",
                        "source_kind": "none",
                    },
                    "missing_requirements": ["ground_truth_trajectory"],
                    "supports_decision_accuracy": False,
                },
            )
        self._write_json(
            case_dir / "trajectory_manifest.json",
            {
                "schema": "CASE_TRAJECTORY_MANIFEST_V1",
                "case_id": "case_demo",
                "source_kind": "none",
                "time_column": "",
                "signal_columns": ["y"],
                "ground_truth_relpath": "",
                "input_relpath": "",
                "supports_numerical_fidelity": False,
                "column_aliases": {"time": []},
                "signal_aliases": {"y": ["y", "asset_demo.y"]},
                "stage_segments": [],
                "reference_generation_method": "none",
            },
        )

    def test_validate_writes_case_index_support_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._build_minimal_dataset(root)
            result = validate(dataset_root=root)
            self.assertEqual(result["issues"], [])
            self.assertEqual(result["case_category_counts"], {"simple": 1, "complex": 0})

            rows = [json.loads(line) for line in (root / "indexes" / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_category"], "simple")
            self.assertEqual(rows[0]["complexity_metrics"]["ground_truth_port_count"], 1)
            self.assertTrue(rows[0]["supports_execution_metrics"])
            self.assertFalse(rows[0]["supports_numerical_fidelity"])
            self.assertFalse(rows[0]["supports_decision_accuracy"])
            case_payload = json.loads((root / "cases" / "case_demo" / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(case_payload["case_category"], "simple")
            self.assertEqual(case_payload["complexity_metrics"]["rule_id"], "simple_complex_v1")

    def test_validate_reports_missing_verification_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._build_minimal_dataset(root, include_verification_result=False)
            result = validate(dataset_root=root)
            self.assertIn("case case_demo missing artifact file verification_result", result["issues"])

    def test_validate_requires_retrieval_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._build_minimal_dataset(root)
            (root / "cases" / "case_demo" / "retrieval_reference.json").unlink()
            result = validate(dataset_root=root)
            self.assertIn("case case_demo missing artifact file retrieval_reference", result["issues"])


if __name__ == "__main__":
    unittest.main()
