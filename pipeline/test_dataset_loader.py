from __future__ import annotations

import unittest
from pathlib import Path

from dataset.common import parse_sysml_model
from pipeline.dataset_loader import load_case_from_dataset


class DatasetLoaderSysmlFallbackTest(unittest.TestCase):
    def test_parse_manual_case_source_sysml_uses_interface_flows(self) -> None:
        sysml_path = Path("dataset/sources/cases/case_manual_001/system.sysml")
        parsed = parse_sysml_model(sysml_path.read_text(encoding="utf-8"), sysml_name=sysml_path.name)
        connections = {
            (
                item["source_component"],
                item["source_signal"],
                item["target_component"],
                item["target_signal"],
            )
            for item in parsed["connections"]
        }
        self.assertEqual(len(connections), 10)
        self.assertIn(("controller", "current_A", "battery", "current_A"), connections)
        self.assertIn(("controller", "pumpCommand", "coolingLoop", "pumpCommand"), connections)
        self.assertIn(("battery", "heatGeneration_W", "coolingLoop", "heatLoad_W"), connections)
        self.assertNotIn(("controller", "current_A", "battery", "coolantInletTemperature_C"), connections)

    def test_load_case_prefers_source_sysml_when_normalized_case_lacks_it(self) -> None:
        loaded = load_case_from_dataset("case_manual_001", dataset_root="dataset")
        connections = {
            (
                item.source_component,
                item.source_signal,
                item.target_component,
                item.target_signal,
            )
            for item in loaded.mbse_context.connections
        }
        self.assertEqual(len(connections), 10)
        self.assertEqual(
            Path(str(loaded.mbse_context.metadata["sysml_path"])).resolve(),
            Path("dataset/sources/cases/case_manual_001/system.sysml").resolve(),
        )
        self.assertIn(("coolingLoop", "coolantFlow_kgps", "battery", "coolantFlow_kgps"), connections)
        self.assertNotIn(("controller", "fanCommand", "battery", "ambientTemperature_C"), connections)


if __name__ == "__main__":
    unittest.main()
