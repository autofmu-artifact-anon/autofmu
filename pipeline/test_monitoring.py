from __future__ import annotations

import unittest

from pipeline.dataset_loader import load_case_from_dataset
from pipeline.monitoring import build_monitored_outputs
from pipeline.types import FMU, PortMeta


def _port(name: str, causality: str, type_name: str = "Real") -> PortMeta:
    return PortMeta(name=name, causality=causality, type=type_name)


class MonitorBindingTest(unittest.TestCase):
    def test_build_monitored_outputs_uses_requirement_aliases_for_multi_instance_case(self) -> None:
        loaded = load_case_from_dataset("case_dtaas_mass_spring_damper_monitor", dataset_root="dataset")
        selected_fmus = [
            FMU(
                uid="asset_dtaas_mass_spring_damper_monitor__m2",
                name="m2",
                ports=[
                    _port("x1", "input", "Integer"),
                    _port("x2", "input", "Integer"),
                    _port("_output", "output", "Integer"),
                ],
                inputs=["x1", "x2"],
                outputs=["_output"],
            ),
            FMU(
                uid="asset_dtaas_mass_spring_damper_monitor__msd2",
                name="msd2",
                ports=[
                    _port("x2", "output"),
                    _port("v2", "output"),
                ],
                outputs=["x2", "v2"],
            ),
            FMU(
                uid="asset_dtaas_mass_spring_damper_monitor__rti1",
                name="rti1",
                ports=[_port("y", "output", "Integer")],
                outputs=["y"],
            ),
            FMU(
                uid="asset_dtaas_mass_spring_damper_monitor__rti2",
                name="rti2",
                ports=[_port("y", "output", "Integer")],
                outputs=["y"],
            ),
        ]

        monitored_outputs, warnings = build_monitored_outputs(
            selected_fmus=selected_fmus,
            verification_requirement_payload=loaded.verification_requirement_payload,
            trajectory_manifest_payload=loaded.trajectory_manifest_payload,
            fallback_signals=["x1", "x2", "output", "soft_reset", "fk", "v1", "v2", "u", "y"],
        )

        monitored_map = {item["name"]: item.get("source", "") for item in monitored_outputs}
        self.assertEqual(
            monitored_map["x2"],
            "asset_dtaas_mass_spring_damper_monitor__msd2.x2",
        )
        self.assertEqual(
            monitored_map["v2"],
            "asset_dtaas_mass_spring_damper_monitor__msd2.v2",
        )
        self.assertEqual(
            monitored_map["y"],
            "asset_dtaas_mass_spring_damper_monitor__rti2.y",
        )
        self.assertEqual(
            monitored_map["_output"],
            "asset_dtaas_mass_spring_damper_monitor__m2._output",
        )
        self.assertNotIn("ambiguous_monitored_signal:y", warnings)


if __name__ == "__main__":
    unittest.main()
