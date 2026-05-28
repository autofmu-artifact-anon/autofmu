from __future__ import annotations

import unittest
from pathlib import Path

from dataset.common import parse_sysml_model
from pipeline.dataset_loader import load_case_from_dataset


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = REPO_ROOT / "dataset"


class ParseSysMLInterfaceTest(unittest.TestCase):
    def test_manual_001_uses_interface_flow_pairs_instead_of_port_cross_product(self) -> None:
        sysml_path = DATASET_ROOT / "sources" / "cases" / "case_manual_001" / "system.sysml"
        payload = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name)
        connections = {
            (
                str(item.get("source_component") or ""),
                str(item.get("source_signal") or ""),
                str(item.get("target_component") or ""),
                str(item.get("target_signal") or ""),
            )
            for item in payload.get("connections", [])
        }
        expected = {
            ("controller", "current_A", "battery", "current_A"),
            ("battery", "voltage_V", "controller", "voltage_V"),
            ("battery", "soc", "controller", "soc"),
            ("battery", "coreTemperature_C", "controller", "coreTemperature_C"),
            ("controller", "pumpCommand", "coolingLoop", "pumpCommand"),
            ("controller", "fanCommand", "coolingLoop", "fanCommand"),
            ("battery", "surfaceTemperature_C", "coolingLoop", "batterySurfaceTemperature_C"),
            ("battery", "heatGeneration_W", "coolingLoop", "heatLoad_W"),
            ("coolingLoop", "coolantInletTemperature_C", "battery", "coolantInletTemperature_C"),
            ("coolingLoop", "coolantFlow_kgps", "battery", "coolantFlow_kgps"),
        }
        self.assertEqual(connections, expected)
        self.assertNotIn(("controller", "current_A", "battery", "coolantInletTemperature_C"), connections)

    def test_manual_002_preserves_feedback_links_from_interface_connect_syntax(self) -> None:
        sysml_path = DATASET_ROOT / "sources" / "cases" / "case_manual_002" / "system.sysml"
        payload = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name)
        connections = {
            (
                str(item.get("source_component") or ""),
                str(item.get("source_signal") or ""),
                str(item.get("target_component") or ""),
                str(item.get("target_signal") or ""),
            )
            for item in payload.get("connections", [])
        }
        expected = {
            ("controller", "force_cmd_N", "plant", "force_cmd_N"),
            ("plant", "x_m", "controller", "x_m"),
            ("plant", "x_dot_mps", "controller", "x_dot_mps"),
            ("plant", "theta_meas_rad", "estimator", "theta_meas_rad"),
            ("plant", "theta_dot_meas_rps", "estimator", "theta_dot_meas_rps"),
            ("estimator", "theta_hat_rad", "controller", "theta_hat_rad"),
            ("estimator", "theta_dot_hat_rps", "controller", "theta_dot_hat_rps"),
        }
        self.assertEqual(connections, expected)

    def test_manual_005_recovers_bind_based_component_links(self) -> None:
        sysml_path = DATASET_ROOT / "cases" / "case_manual_005" / "system.sysml"
        payload = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name)
        connections = {
            (
                str(item.get("source_component") or ""),
                str(item.get("source_signal") or ""),
                str(item.get("target_component") or ""),
                str(item.get("target_signal") or ""),
            )
            for item in payload.get("connections", [])
        }
        expected = {
            ("thermalController", "pump_cmd", "coolantLoopPlant", "pump_cmd"),
            ("batteryPackPlant", "heat_gen_W", "coolantLoopPlant", "heat_in_W"),
            ("coolantLoopPlant", "coolant_temp_C", "batteryPackPlant", "coolant_in_temp_C"),
            ("batteryPackPlant", "temp_cell_C", "thermalController", "temp_cell_C"),
            ("coolantLoopPlant", "coolant_temp_C", "thermalController", "coolant_temp_C"),
        }
        self.assertEqual(connections, expected)

    def test_manual_005_recovers_bind_based_component_connections(self) -> None:
        sysml_path = DATASET_ROOT / "cases" / "case_manual_005" / "system.sysml"
        payload = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name)
        connections = {
            (
                str(item.get("source_component") or ""),
                str(item.get("source_signal") or ""),
                str(item.get("target_component") or ""),
                str(item.get("target_signal") or ""),
            )
            for item in payload.get("connections", [])
        }
        expected = {
            ("thermalController", "pump_cmd", "coolantLoopPlant", "pump_cmd"),
            ("batteryPackPlant", "heat_gen_W", "coolantLoopPlant", "heat_in_W"),
            ("coolantLoopPlant", "coolant_temp_C", "batteryPackPlant", "coolant_in_temp_C"),
            ("batteryPackPlant", "temp_cell_C", "thermalController", "temp_cell_C"),
            ("coolantLoopPlant", "coolant_temp_C", "thermalController", "coolant_temp_C"),
        }
        self.assertTrue(expected <= connections)
        self.assertNotIn(("thermalController", "enable", "batteryPackPlant", "i_load_A"), connections)

    def test_dataset_loader_prefers_reparsed_sysml_connections(self) -> None:
        loaded = load_case_from_dataset("case_manual_001", dataset_root=str(DATASET_ROOT))
        connections = {
            (item.source_component, item.source_signal, item.target_component, item.target_signal)
            for item in loaded.mbse_context.connections
        }
        self.assertEqual(len(connections), 10)
        self.assertIn(("controller", "pumpCommand", "coolingLoop", "pumpCommand"), connections)
        self.assertNotIn(("controller", "current_A", "battery", "coolantInletTemperature_C"), connections)


if __name__ == "__main__":
    unittest.main()
