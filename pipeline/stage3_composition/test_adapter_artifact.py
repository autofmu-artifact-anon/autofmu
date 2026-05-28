from __future__ import annotations

import ctypes
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from pipeline.stage3_composition.adapter_artifact import build_adapter_artifact
from pipeline.types import AdapterSpec


class AdapterArtifactTest(unittest.TestCase):
    def test_build_adapter_artifact_without_legacy_dependency(self) -> None:
        adapter_spec = AdapterSpec(
            adapter_id="adapter_temperature_c_to_k",
            kind="unit_transform_adapter",
            source="plant.temperature_C",
            target="controller.temperature_K",
            transform={"transform_kind": "unit_transform", "scale": 1.0, "offset": 273.15},
            inserted_node_id="adapter_temperature_c_to_k",
            io_contract={
                "inputs": [{"name": "temperature_C"}],
                "outputs": [{"name": "temperature_K"}],
            },
            notes=["test"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = build_adapter_artifact(adapter_spec, out_dir=Path(tmpdir))

            adapter_dir = Path(artifact["adapter_dir"])
            glue_py = Path(artifact["glue_py"])
            synthesis_json = Path(artifact["synthesis_json"])
            model_description_xml = Path(artifact["model_description_xml"])
            fmu_path = Path(artifact["fmu_path"])

            self.assertTrue(adapter_dir.is_dir())
            self.assertTrue(glue_py.is_file())
            self.assertTrue(synthesis_json.is_file())
            self.assertTrue(model_description_xml.is_file())
            self.assertTrue(fmu_path.is_file())

            synthesis = json.loads(synthesis_json.read_text(encoding="utf-8"))
            self.assertEqual(synthesis["adapter_id"], adapter_spec.adapter_id)
            self.assertEqual(synthesis["model_name"], adapter_spec.inserted_node_id)
            self.assertEqual(synthesis["operators_used"], ["derived", "identity"])
            self.assertEqual(synthesis["mappings"][1]["op"]["params"]["transform_kind"], "unit_transform")
            self.assertEqual(synthesis["mappings"][1]["op"]["params"]["offset"], 273.15)

            with zipfile.ZipFile(fmu_path, "r") as zf:
                names = set(zf.namelist())
            self.assertIn("modelDescription.xml", names)
            self.assertIn("resources/glue.py", names)
            self.assertIn("resources/synthesis.json", names)
            self.assertIn("sources/adapter_fmu.c", names)
            if (adapter_dir / "binaries" / "linux64" / "adapter_temperature_c_to_k.so").exists():
                lib = ctypes.CDLL(str(adapter_dir / "binaries" / "linux64" / "adapter_temperature_c_to_k.so"))
                self.assertTrue(hasattr(lib, "fmi2GetBoolean"))
                self.assertTrue(hasattr(lib, "fmi2SetBoolean"))
                self.assertTrue(hasattr(lib, "fmi2GetFMUstate"))
                self.assertTrue(hasattr(lib, "fmi2SerializeFMUstate"))
                self.assertTrue(hasattr(lib, "fmi2DeSerializeFMUstate"))
                self.assertTrue(hasattr(lib, "fmi2GetDirectionalDerivative"))
                self.assertTrue(hasattr(lib, "fmi2SetRealInputDerivatives"))
                self.assertTrue(hasattr(lib, "fmi2GetRealOutputDerivatives"))
                try:
                    from fmpy import extract, read_model_description
                    from fmpy.simulation import instantiate_fmu
                except ImportError:
                    pass
                else:
                    unzipdir = extract(str(fmu_path))
                    model_description = read_model_description(str(fmu_path), validate=False)
                    fmu = instantiate_fmu(unzipdir, model_description, "CoSimulation")
                    try:
                        fmu.instantiate()
                    finally:
                        fmu.freeInstance()


if __name__ == "__main__":
    unittest.main()
