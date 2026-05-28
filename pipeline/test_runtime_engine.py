from __future__ import annotations

import unittest

from pipeline.runtime_engine import (
    _aligned_to_period,
    _asset_execution_order,
    _expanded_start_values,
    _record_bound_signal,
    _record_unsourced_signal,
    _run_fixed_point_loop,
    _schedule_asset_periods,
    _single_fmu_simulation_kwargs,
)
from pipeline.types import FMU, SimulationConfig


class _FakeInstance:
    def __init__(self, variables, values):
        self.variables = variables
        self._values = values

    def read_values(self, names):
        return {name: self._values[name] for name in names if name in self._values}


class _FakePythonModel:
    def __init__(self):
        self.theta = 0.0
        self.theta_rad = 0.0


class _FakeLoopInstance:
    def __init__(self):
        self.variables = {
            "u": {"causality": "input"},
            "y": {"causality": "output"},
        }
        self._state = {"u": 0.0, "y": 0.0}
        self.warnings = []

    def read_values(self, names):
        return {name: self._state[name] for name in names if name in self._state}

    def set_values(self, mapping):
        self._state.update(mapping)

    def step(self, current_time, step_size):
        del current_time, step_size
        self._state["y"] = 0.5 * (float(self._state.get("u", 0.0)) + 1.0)

    def snapshot_state(self):
        return dict(self._state)

    def restore_state(self, state):
        self._state = dict(state)

    def free_state(self, state):
        del state


class _FailingSnapshotLoopInstance(_FakeLoopInstance):
    def snapshot_state(self):
        raise RuntimeError("snapshot unavailable")


class RuntimeEngineSignalSelectionTest(unittest.TestCase):
    def test_expanded_start_values_map_output_name_to_state_aliases(self) -> None:
        instance = type(
            "FakeRuntime",
            (),
            {
                "model": _FakePythonModel(),
                "variables": {"theta_rad": {"causality": "output"}, "theta_rad_state": {"causality": "local"}},
            },
        )()

        expanded = _expanded_start_values(instance, {"theta_rad": 0.12})

        self.assertEqual(expanded["theta_rad"], 0.12)
        self.assertEqual(expanded["theta"], 0.12)
        self.assertEqual(expanded["theta_rad_state"], 0.12)

    def test_asset_execution_order_preserves_predicted_order(self) -> None:
        simulation_config = SimulationConfig(
            step_size=0.01,
            duration=1.0,
            fmus=[
                FMU(uid="asset_plant", name="InvertedPendulumPlant"),
                FMU(uid="asset_controller", name="PendulumController"),
            ],
        )

        ordered = _asset_execution_order(
            {"selected_asset_ids": ["controller", "plant"]},
            simulation_config,
        )

        self.assertEqual(ordered[:2], ["asset_controller", "asset_plant"])

    def test_unsourced_signal_prefers_unique_output_over_same_named_input(self) -> None:
        row = {}
        warnings = []
        active_instances = {
            "asset_m2": _FakeInstance(
                {"x2": {"causality": "input"}},
                {"x2": 91},
            ),
            "asset_msd2": _FakeInstance(
                {"x2": {"causality": "output"}},
                {"x2": 0.482877},
            ),
        }

        _record_unsourced_signal(
            row=row,
            warnings=warnings,
            signal_name="x2",
            stage_assets=["asset_m2", "asset_msd2"],
            active_instances=active_instances,
        )

        self.assertEqual(row["x2"], 0.482877)
        self.assertNotIn("asset_m2.x2", row)
        self.assertEqual(warnings, [])

    def test_unsourced_signal_qualifies_ambiguous_output_names(self) -> None:
        row = {}
        warnings = []
        active_instances = {
            "asset_rti1": _FakeInstance(
                {"y": {"causality": "output"}},
                {"y": 100},
            ),
            "asset_rti2": _FakeInstance(
                {"y": {"causality": "output"}},
                {"y": 0},
            ),
        }

        _record_unsourced_signal(
            row=row,
            warnings=warnings,
            signal_name="y",
            stage_assets=["asset_rti1", "asset_rti2"],
            active_instances=active_instances,
        )

        self.assertNotIn("y", row)
        self.assertEqual(row["asset_rti1.y"], 100)
        self.assertEqual(row["asset_rti2.y"], 0)
        self.assertTrue(any(item.startswith("ambiguous_monitored_signal:y:") for item in warnings))

    def test_bound_signal_reads_exact_source_endpoint(self) -> None:
        row = {}
        warnings = []
        active_instances = {
            "asset_rti1": _FakeInstance(
                {"y": {"causality": "output"}},
                {"y": 100},
            ),
            "asset_rti2": _FakeInstance(
                {"y": {"causality": "output"}},
                {"y": 0},
            ),
        }

        _record_bound_signal(
            row=row,
            warnings=warnings,
            monitored_name="y",
            source_endpoint="asset_rti2.y",
            active_instances=active_instances,
        )

        self.assertEqual(row["y"], 0)
        self.assertEqual(warnings, [])

    def test_schedule_asset_periods_prefers_per_node_periods(self) -> None:
        simulation_config = SimulationConfig(
            step_size=0.01,
            duration=1.0,
            scheduler={"per_node_period": {"asset_controller": 0.1}},
        )

        periods = _schedule_asset_periods(
            {},
            simulation_config,
            stage_assets=["asset_controller", "asset_plant"],
            default_step=0.01,
        )

        self.assertEqual(periods["asset_controller"], 0.1)
        self.assertEqual(periods["asset_plant"], 0.01)

    def test_schedule_asset_periods_prefers_fixed_step_solution_schedule_over_multirate_scheduler(self) -> None:
        simulation_config = SimulationConfig(
            step_size=0.01,
            duration=1.0,
            scheduler={"per_node_period": {"asset_controller": 0.01, "asset_plant": 0.02}},
        )

        periods = _schedule_asset_periods(
            {"kind": "co_simulation", "step_size": 0.1},
            simulation_config,
            stage_assets=["asset_controller", "asset_plant"],
            default_step=0.1,
        )

        self.assertEqual(periods["asset_controller"], 0.1)
        self.assertEqual(periods["asset_plant"], 0.1)

    def test_single_fmu_simulation_kwargs_omit_step_controls_for_zero_step_single_fmu_schedule(self) -> None:
        kwargs = _single_fmu_simulation_kwargs(
            {"kind": "single_fmu", "step_size": 0.0},
            SimulationConfig(step_size=0.01, duration=1.0),
        )

        self.assertEqual(kwargs, {})

    def test_single_fmu_simulation_kwargs_preserve_output_interval_for_declared_single_fmu_step(self) -> None:
        kwargs = _single_fmu_simulation_kwargs(
            {"kind": "single_fmu", "step_size": 0.02},
            SimulationConfig(step_size=0.01, duration=1.0),
        )

        self.assertEqual(kwargs, {"output_interval": 0.02})

    def test_aligned_to_period_detects_comm_points(self) -> None:
        self.assertTrue(_aligned_to_period(0.1, 0.1))
        self.assertTrue(_aligned_to_period(0.3, 0.1))
        self.assertFalse(_aligned_to_period(0.05, 0.1))

    def test_fixed_point_loop_iterates_snapshot_capable_nodes(self) -> None:
        instances = {
            "asset_a": _FakeLoopInstance(),
            "asset_b": _FakeLoopInstance(),
        }
        processed = _run_fixed_point_loop(
            loop_wrapper={
                "loop_id": "loop_0",
                "node_order": ["asset_a", "asset_b"],
                "convergence_signals": ["asset_a.y->asset_b.u", "asset_b.y->asset_a.u"],
                "tol": 1e-6,
                "max_iters": 20,
                "runtime_policy": {"kind": "fixed_point_iteration", "iterate_until_converged": True},
            },
            time_point=1.0,
            stage_start_time=0.0,
            stage_stop_time=1.0,
            stage_assets=["asset_a", "asset_b"],
            active_instances=instances,
            connection_by_target={
                "asset_a.u": "asset_b.y",
                "asset_b.u": "asset_a.y",
            },
            external_bindings={},
            scenario_inputs={},
            asset_periods={"asset_a": 1.0, "asset_b": 1.0},
            asset_last_step_time={"asset_a": 0.0, "asset_b": 0.0},
            warnings=[],
        )

        self.assertEqual(processed, ["asset_a", "asset_b"])
        self.assertGreater(instances["asset_a"].read_values(["y"])["y"], 0.99)
        self.assertGreater(instances["asset_b"].read_values(["y"])["y"], 0.99)

    def test_fixed_point_loop_falls_back_when_snapshot_raises(self) -> None:
        instances = {
            "asset_a": _FailingSnapshotLoopInstance(),
            "asset_b": _FakeLoopInstance(),
        }
        warnings = []

        processed = _run_fixed_point_loop(
            loop_wrapper={
                "loop_id": "loop_0",
                "node_order": ["asset_a", "asset_b"],
                "convergence_signals": ["asset_a.y->asset_b.u", "asset_b.y->asset_a.u"],
                "tol": 1e-6,
                "max_iters": 20,
                "runtime_policy": {"kind": "fixed_point_iteration", "iterate_until_converged": True},
            },
            time_point=1.0,
            stage_start_time=0.0,
            stage_stop_time=1.0,
            stage_assets=["asset_a", "asset_b"],
            active_instances=instances,
            connection_by_target={
                "asset_a.u": "asset_b.y",
                "asset_b.u": "asset_a.y",
            },
            external_bindings={},
            scenario_inputs={},
            asset_periods={"asset_a": 1.0, "asset_b": 1.0},
            asset_last_step_time={"asset_a": 0.0, "asset_b": 0.0},
            warnings=warnings,
        )

        self.assertEqual(processed, [])
        self.assertTrue(any(item.startswith("loop_snapshot_failed:loop_0:asset_a:RuntimeError") for item in warnings))


if __name__ == "__main__":
    unittest.main()
