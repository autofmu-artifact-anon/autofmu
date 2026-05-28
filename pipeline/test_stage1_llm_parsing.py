from __future__ import annotations

import unittest

from pipeline.stage1_decomposition.decomposer import _criterion_from_raw, _regime_from_raw


class Stage1LLMParsingTest(unittest.TestCase):
    def test_string_acceptance_criterion_extracts_signal_hint(self) -> None:
        criterion = _criterion_from_raw("Trajectory of h matches archived ground truth")
        self.assertIsNotNone(criterion)
        assert criterion is not None
        self.assertEqual(criterion.metric, "h")
        self.assertEqual(criterion.operator, "descriptive")
        self.assertEqual(criterion.value, "Trajectory of h matches archived ground truth")

    def test_textual_acceptance_criterion_keeps_numeric_operator(self) -> None:
        criterion = _criterion_from_raw("temp_cell_C <= 45 C")
        self.assertIsNotNone(criterion)
        assert criterion is not None
        self.assertEqual(criterion.metric, "temp_cell_C")
        self.assertEqual(criterion.operator, "<=")
        self.assertEqual(criterion.value, 45.0)
        self.assertEqual(criterion.unit, "C")

    def test_string_operating_regime_becomes_description_only_regime(self) -> None:
        regime = _regime_from_raw("default experiment")
        self.assertIsNotNone(regime)
        assert regime is not None
        self.assertEqual(regime.description, "default experiment")
        self.assertEqual(regime.inputs, {})
        self.assertEqual(regime.initial_conditions, {})


if __name__ == "__main__":
    unittest.main()
