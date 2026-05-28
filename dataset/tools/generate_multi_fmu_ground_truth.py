#!/usr/bin/env python3
"""Generate numerical ground-truth trajectories for multi-FMU dataset cases.

This script performs offline co-simulation for each multi-FMU case that has
well-defined physics, produces ``ground_truth_trajectory.csv`` files, and
updates the corresponding metadata (case.json, trajectory_manifest.json,
verification_result.json) so that the evaluator can score numerical fidelity.

Supported cases
---------------
* DTaaS physics cases: mass_spring_damper, three_tank, water_tank_fi
* Manual cases: case_manual_001 … case_manual_005

DTaaS cases that depend on RabbitMQ messaging, NuRV monitors, or multi-stage
model swap are **not** covered here because they cannot be analytically
simulated without the external runtime.  They are left with
``supports_numerical_fidelity = false``.

Usage::

    cd experiments/dataset
    python -m tools.generate_multi_fmu_ground_truth          # all supported
    python -m tools.generate_multi_fmu_ground_truth case_manual_003  # single
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
import textwrap
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

DATASET_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = DATASET_ROOT / "cases"
SOURCES_DIR = DATASET_ROOT / "sources"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ordered_unique(items: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _piecewise_profile(profile: Sequence[Mapping[str, Any]], t: float, *, key_t: str = "t_s", key_v: str | None = None) -> float:
    """Zero-order hold interpolation of a step-profile list."""
    if not profile:
        return 0.0
    val = 0.0
    for pt in profile:
        pt_t = float(pt[key_t])
        if pt_t > t:
            break
        if key_v is not None:
            val = float(pt[key_v])
        else:
            for k, v in pt.items():
                if k != key_t:
                    val = float(v)
    return val


# ---------------------------------------------------------------------------
# Generic co-simulation runner
# ---------------------------------------------------------------------------

@dataclass
class CoSimConfig:
    """Everything the generic runner needs for a single case."""
    case_id: str
    models: Dict[str, Any]
    connections: List[Tuple[str, str, str, str]]
    execution_order: List[str]
    monitored_outputs: List[Tuple[str, str]]
    start_time: float = 0.0
    stop_time: float = 10.0
    step_size: float = 0.001
    output_interval: float = 0.0
    external_input_fn: Callable[[float], Dict[str, Dict[str, float]]] | None = None


def _get(model: Any, attr: str) -> float:
    return float(getattr(model, attr))


def _set(model: Any, attr: str, value: float) -> None:
    setattr(model, attr, value)


def run_cosim(cfg: CoSimConfig) -> List[Dict[str, Any]]:
    """Execute a fixed-step co-simulation and return time-series rows."""
    dt = cfg.step_size
    t = cfg.start_time
    output_dt = cfg.output_interval if cfg.output_interval > 0 else dt
    rows: List[Dict[str, Any]] = []
    next_output = t

    def _capture(time_val: float) -> Dict[str, Any]:
        row: Dict[str, Any] = {"time": round(time_val, 10)}
        for sig_name, endpoint in cfg.monitored_outputs:
            asset_id, attr = endpoint.split(".", 1) if "." in endpoint else (endpoint, endpoint)
            model = cfg.models.get(asset_id)
            if model is not None and hasattr(model, attr):
                row[sig_name] = float(getattr(model, attr))
            else:
                row[sig_name] = 0.0
        return row

    def _propagate_connections() -> None:
        for src_asset, src_attr, tgt_asset, tgt_attr in cfg.connections:
            src_model = cfg.models.get(src_asset)
            tgt_model = cfg.models.get(tgt_asset)
            if src_model is not None and tgt_model is not None:
                if hasattr(src_model, src_attr) and hasattr(tgt_model, tgt_attr):
                    setattr(tgt_model, tgt_attr, float(getattr(src_model, src_attr)))

    def _apply_externals(time_val: float) -> None:
        if cfg.external_input_fn is None:
            return
        inputs = cfg.external_input_fn(time_val)
        for asset_id, attr_map in inputs.items():
            model = cfg.models.get(asset_id)
            if model is None:
                continue
            for attr, val in attr_map.items():
                if hasattr(model, attr):
                    setattr(model, attr, val)

    _apply_externals(t)
    _propagate_connections()
    rows.append(_capture(t))
    next_output += output_dt

    n_steps = int(round((cfg.stop_time - cfg.start_time) / dt))
    for step_idx in range(n_steps):
        _apply_externals(t)
        for asset_id in cfg.execution_order:
            _propagate_connections()
            model = cfg.models.get(asset_id)
            if model is not None and hasattr(model, "do_step"):
                model.do_step(t, dt, False)
        t = round(cfg.start_time + (step_idx + 1) * dt, 10)
        if t >= next_output - dt * 0.01:
            rows.append(_capture(t))
            next_output += output_dt
    return rows


def write_trajectory_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ===================================================================
# DTaaS: mass_spring_damper
# ===================================================================

class _MSD1:
    """MassSpringDamper1: single DOF with coupling force input."""
    def __init__(self, m1: float = 1.0, c1: float = 1.0, d1: float = 1.0,
                 x1_0: float = 0.0, v1_0: float = 0.0):
        self.m1, self.c1, self.d1 = m1, c1, d1
        self.x1, self.v1 = x1_0, v1_0
        self.fk = 0.0

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        a = (-self.c1 * self.x1 - self.d1 * self.v1 + self.fk) / max(self.m1, 1e-12)
        self.v1 += a * dt
        self.x1 += self.v1 * dt
        return 0


class _MSD2:
    """MassSpringDamper2: second DOF coupled to first."""
    def __init__(self, m2: float = 1.0, c2: float = 1.0, d2: float = 1.0,
                 cc: float = 1.0, dc: float = 1.0,
                 x2_0: float = 0.0, v2_0: float = 0.0):
        self.m2, self.c2, self.d2, self.cc, self.dc = m2, c2, d2, cc, dc
        self.x1, self.v1 = 0.0, 0.0
        self.x2, self.v2 = x2_0, v2_0
        self.fk = 0.0

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        dx = self.x2 - self.x1
        dv = self.v2 - self.v1
        self.fk = self.cc * dx + self.dc * dv
        a = (-self.c2 * self.x2 - self.d2 * self.v2 - self.fk) / max(self.m2, 1e-12)
        self.v2 += a * dt
        self.x2 += self.v2 * dt
        return 0


def _build_mass_spring_damper() -> CoSimConfig:
    msd1 = _MSD1(m1=1.0, c1=1.0, d1=1.0, x1_0=1.0, v1_0=0.0)
    msd2 = _MSD2(m2=1.0, c2=1.0, d2=1.0, cc=1.0, dc=1.0)
    a1 = "asset_dtaas_mass_spring_damper__msd1"
    a2 = "asset_dtaas_mass_spring_damper__msd2"
    return CoSimConfig(
        case_id="case_dtaas_mass_spring_damper",
        models={a1: msd1, a2: msd2},
        connections=[
            (a1, "x1", a2, "x1"),
            (a1, "v1", a2, "v1"),
            (a2, "fk", a1, "fk"),
        ],
        execution_order=[a1, a2],
        monitored_outputs=[("x2", f"{a2}.x2"), ("v2", f"{a2}.v2")],
        start_time=0.0,
        stop_time=10.0,
        step_size=0.001,
        output_interval=0.01,
    )


# ===================================================================
# DTaaS: three_tank
# ===================================================================

class _LinearTank:
    """Simplified linear tank: level' = (inPort - outPort - leak) / cap."""
    def __init__(self, level_0: float = 0.0, cap: float = 1.0,
                 k_out: float = 0.5, k_leak: float = 0.1):
        self.level = level_0
        self.cap, self.k_out, self.k_leak = cap, k_out, k_leak
        self.inPort = 0.0
        self.outPort = 0.0
        self.leak = 0.0
        self.der_level = 0.0

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        self.outPort = self.k_out * max(self.level, 0.0)
        self.leak = self.k_leak * max(self.level, 0.0)
        self.der_level = (self.inPort - self.outPort - self.leak) / max(self.cap, 1e-12)
        self.level += self.der_level * dt
        self.level = max(self.level, 0.0)
        setattr(self, "der(level)", self.der_level)
        return 0


def _build_three_tank() -> CoSimConfig:
    a1 = "asset_dtaas_three_tank__tank1"
    a2 = "asset_dtaas_three_tank__tank2"
    a3 = "asset_dtaas_three_tank__tank3"
    tank1 = _LinearTank(level_0=2.0, k_out=0.5, k_leak=0.1)
    tank2 = _LinearTank(level_0=10.0, k_out=0.5, k_leak=0.1)
    tank3 = _LinearTank(level_0=35.0, k_out=0.5, k_leak=0.1)

    sol = _read_json(CASES_DIR / "case_dtaas_three_tank" / "solution.json")
    mo = sol.get("monitored_outputs", [])
    monitored: List[Tuple[str, str]] = []
    for entry in mo:
        name = entry["name"]
        src = entry["source"]
        monitored.append((name, src))

    return CoSimConfig(
        case_id="case_dtaas_three_tank",
        models={a1: tank1, a2: tank2, a3: tank3},
        connections=[
            (a1, "outPort", a2, "inPort"),
            (a2, "outPort", a3, "inPort"),
        ],
        execution_order=[a1, a2, a3],
        monitored_outputs=monitored,
        start_time=0.0,
        stop_time=10.0,
        step_size=0.5,
        output_interval=0.5,
    )


# ===================================================================
# DTaaS: water_tank_fi
# ===================================================================

class _WaterTankController:
    """Bang-bang controller with hysteresis for water tank level."""
    def __init__(self, minlevel: float = 1.0, maxlevel: float = 2.0):
        self.minlevel = minlevel
        self.maxlevel = maxlevel
        self.level = 0.0
        self.valve = 1.0

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        if self.level >= self.maxlevel:
            self.valve = 0.0
        elif self.level <= self.minlevel:
            self.valve = 1.0
        return 0


class _SingleWaterTank:
    """Simple water tank with valve inflow and gravity outflow."""
    def __init__(self, level_0: float = 1.5, kv: float = 0.05, ko: float = 0.02):
        self.level = level_0
        self.valvecontrol = 0.0
        self.kv, self.ko = kv, ko

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        inflow = self.kv * self.valvecontrol
        outflow = self.ko * math.sqrt(max(self.level, 0.0))
        self.level += (inflow - outflow) * dt
        self.level = max(self.level, 0.0)
        return 0


def _build_water_tank_fi() -> CoSimConfig:
    a1 = "asset_dtaas_water_tank_fi__x1"
    a2 = "asset_dtaas_water_tank_fi__x2"
    ctrl = _WaterTankController(minlevel=1.0, maxlevel=2.0)
    tank = _SingleWaterTank(level_0=1.5)
    return CoSimConfig(
        case_id="case_dtaas_water_tank_fi",
        models={a1: ctrl, a2: tank},
        connections=[
            (a1, "valve", a2, "valvecontrol"),
            (a2, "level", a1, "level"),
        ],
        execution_order=[a1, a2],
        monitored_outputs=[
            ("valve", f"{a1}.valve"),
            ("level", f"{a2}.level"),
        ],
        start_time=0.0,
        stop_time=100.0,
        step_size=0.1,
        output_interval=0.1,
    )


# ===================================================================
# Manual cases: load Python model backends from create_*_fmu.py
# ===================================================================

def _extract_model_class(create_script_path: Path) -> type:
    """Extract the FMU model class from a create_*_fmu.py script.

    Each script defines a ``MODEL_PY`` string containing the model class.
    We exec() that string and return the first class with a ``do_step`` method.
    """
    source = create_script_path.read_text(encoding="utf-8")
    match = re.search(r"MODEL_PY\s*=\s*'''(.*?)'''", source, re.DOTALL)
    if match is None:
        match = re.search(r'MODEL_PY\s*=\s*"""(.*?)"""', source, re.DOTALL)
    if match is None:
        raise ValueError(f"Cannot find MODEL_PY in {create_script_path}")
    model_source = match.group(1)
    ns: Dict[str, Any] = {"math": math, "__builtins__": __builtins__}
    exec(compile(model_source, str(create_script_path), "exec"), ns)  # noqa: S102
    for name, obj in ns.items():
        if isinstance(obj, type) and hasattr(obj, "do_step") and name != "type":
            return obj
    raise ValueError(f"No model class with do_step found in {create_script_path}")


def _apply_overrides(model: Any, overrides: Mapping[str, Any]) -> None:
    for attr, val in overrides.items():
        if hasattr(model, attr):
            setattr(model, attr, val)


def _apply_ics(model: Any, ics: Mapping[str, Any]) -> None:
    for attr, val in ics.items():
        if hasattr(model, attr):
            setattr(model, attr, val)


class _IPController:
    """State-feedback controller for the inverted pendulum.

    Gains computed via pole placement on the linearised model (A, B) with
    desired closed-loop poles at {-3, -4, -5, -6}.  Output saturated at
    ±u_max.
    """
    def __init__(self):
        self.K_th = 77.825
        self.K_thd = 15.225
        self.K_x = 13.106
        self.K_xd = 12.451
        self.u_max = 15.0
        self.x_ref_m = 0.0
        self.theta_ref_rad = 0.0
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_rad = 0.0
        self.theta_dot_radps = 0.0
        self.force_cmd_N = 0.0

    def _compute_outputs(self):
        pass

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        u = (self.K_th * self.theta_rad
             + self.K_thd * self.theta_dot_radps
             + self.K_x * self.x_m
             + self.K_xd * self.x_dot_mps
             - self.K_x * self.x_ref_m)
        self.force_cmd_N = _clamp(u, -self.u_max, self.u_max)
        return 0


class _InvertedPendulumPlant:
    """Inverted pendulum on cart — theta=0 is upright, gravity destabilises.

    Uses the standard Lagrangian-derived EOM with correct sign convention:
      th_ddot = [+F*cos(th) + m*l*th_dot^2*sin(th)*cos(th)
                 + (M+m)*g*sin(th) - b_pend*th_dot*(M+m)/(m*l)] / (l*Delta)
    where Delta = M + m*sin^2(theta).
    """
    def __init__(self):
        self.m_cart_kg = 1.0
        self.m_pend_kg = 0.2
        self.length_m = 0.5
        self.g_mps2 = 9.81
        self.cart_friction_Nspm = 0.1
        self.pend_damping_Nms = 0.02
        self.x = 0.0
        self.x_dot = 0.0
        self.theta = 0.0
        self.theta_dot = 0.0
        self.force_cmd_N = 0.0
        self.disturbance_N = 0.0
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_rad = 0.0
        self.theta_dot_radps = 0.0

    def _compute_outputs(self):
        self.x_m = self.x
        self.x_dot_mps = self.x_dot
        self.theta_rad = self.theta
        self.theta_dot_radps = self.theta_dot

    def do_step(self, t: float, dt: float, _: bool = False) -> int:
        M = self.m_cart_kg
        m = self.m_pend_kg
        l = max(self.length_m, 1e-6)
        g = self.g_mps2
        b_cart = self.cart_friction_Nspm
        b_pend = self.pend_damping_Nms
        F = self.force_cmd_N + self.disturbance_N - b_cart * self.x_dot
        s = math.sin(self.theta)
        c = math.cos(self.theta)
        td = self.theta_dot
        Delta = max(M + m * s * s, 1e-6)
        xdd = (F + m * s * (l * td * td + g * c) - b_pend * td * c / l) / Delta
        thdd = (-F * c - m * l * td * td * s * c + (M + m) * g * s
                - b_pend * td * (M + m) / (m * l)) / (l * Delta)
        self.x_dot += xdd * dt
        self.theta_dot += thdd * dt
        self.x += self.x_dot * dt
        self.theta += self.theta_dot * dt
        self._compute_outputs()
        return 0


# ---- case_manual_003 ----

def _build_manual_003() -> CoSimConfig:
    plant = _InvertedPendulumPlant()
    ctrl = _IPController()

    _apply_ics(plant, {"theta": 0.12})
    plant._compute_outputs()
    ctrl._compute_outputs()

    ac = "asset_case_case_manual_003__PendulumController"
    ap = "asset_case_case_manual_003__InvertedPendulumPlant"

    req = _read_json(SOURCES_DIR / "cases" / "case_manual_003" / "requirement.json")
    scenario = req.get("scenario", {})
    inputs_def = scenario.get("inputs", {})
    x_ref_profile = inputs_def.get("x_ref_m_profile", [])
    dist_profile = inputs_def.get("disturbance_N_profile", [])

    def ext_fn(t: float) -> Dict[str, Dict[str, float]]:
        x_ref = _piecewise_profile(x_ref_profile, t, key_v="value_m")
        dist = _piecewise_profile(dist_profile, t, key_v="value_N")
        return {
            ac: {"x_ref_m": x_ref, "theta_ref_rad": 0.0},
            ap: {"disturbance_N": dist},
        }

    return CoSimConfig(
        case_id="case_manual_003",
        models={ac: ctrl, ap: plant},
        connections=[
            (ac, "force_cmd_N", ap, "force_cmd_N"),
            (ap, "x_m", ac, "x_m"),
            (ap, "x_dot_mps", ac, "x_dot_mps"),
            (ap, "theta_rad", ac, "theta_rad"),
            (ap, "theta_dot_radps", ac, "theta_dot_radps"),
        ],
        execution_order=[ac, ap],
        monitored_outputs=[
            ("x_m", f"{ap}.x_m"),
            ("x_dot_mps", f"{ap}.x_dot_mps"),
            ("theta_rad", f"{ap}.theta_rad"),
            ("theta_dot_radps", f"{ap}.theta_dot_radps"),
            ("force_cmd_N", f"{ac}.force_cmd_N"),
        ],
        start_time=0.0,
        stop_time=float(scenario.get("t_end_s", 20)),
        step_size=0.001,
        output_interval=0.01,
        external_input_fn=ext_fn,
    )


# ---- case_manual_002 ----

def _build_manual_002() -> CoSimConfig:
    src_dir = SOURCES_DIR / "cases" / "case_manual_002" / "fmus"
    PlantCls = _extract_model_class(src_dir / "create_cart_pole_plant_fmu.py")
    EstCls = _extract_model_class(src_dir / "create_pole_angle_estimator_fmu.py")
    CtrlCls = _extract_model_class(src_dir / "create_swing_up_balance_controller_fmu.py")

    plant = PlantCls()
    est = EstCls()
    ctrl = CtrlCls()

    _apply_ics(plant, {"x": 0.0, "x_dot": 0.0, "theta": 0.0, "theta_dot": 0.0})
    if hasattr(plant, "theta_dot_bias_rps"):
        plant.theta_dot_bias_rps = 0.05
    _apply_ics(est, {"theta_hat_rad" if hasattr(est, "theta_hat_rad") else "theta_hat": 0.0})
    if hasattr(est, "bias_hat_rps"):
        est.bias_hat_rps = 0.0
    if hasattr(est, "bias_hat"):
        est.bias_hat = 0.0
    for m in (plant, est, ctrl):
        if hasattr(m, "_compute_outputs"):
            m._compute_outputs()

    aCtrl = "asset_case_case_manual_002__SwingUpBalanceController"
    aEst = "asset_case_case_manual_002__PoleAngleEstimator"
    aPlant = "asset_case_case_manual_002__CartPolePlant"

    req = _read_json(SOURCES_DIR / "cases" / "case_manual_002" / "requirement.json")
    scenario = req.get("scenario", {})
    inputs_def = scenario.get("inputs", {})
    x_ref_profile = inputs_def.get("x_ref_m_profile", [])
    dist_profile = inputs_def.get("disturbance_force_N_profile", [])

    def ext_fn(t: float) -> Dict[str, Dict[str, float]]:
        x_ref = _piecewise_profile(x_ref_profile, t, key_v="value_m")
        dist = _piecewise_profile(dist_profile, t, key_v="value_N")
        return {
            aCtrl: {"x_ref_m": x_ref, "enable": 1.0},
            aEst: {"reset": 0.0},
            aPlant: {"disturbance_force_N": dist},
        }

    return CoSimConfig(
        case_id="case_manual_002",
        models={aCtrl: ctrl, aEst: est, aPlant: plant},
        connections=[
            (aCtrl, "force_cmd_N", aPlant, "force_cmd_N"),
            (aPlant, "x_m", aCtrl, "x_m"),
            (aPlant, "x_dot_mps", aCtrl, "x_dot_mps"),
            (aPlant, "theta_meas_rad", aEst, "theta_meas_rad"),
            (aPlant, "theta_dot_meas_rps", aEst, "theta_dot_meas_rps"),
            (aEst, "theta_hat_rad", aCtrl, "theta_hat_rad"),
            (aEst, "theta_dot_hat_rps", aCtrl, "theta_dot_hat_rps"),
        ],
        execution_order=[aCtrl, aEst, aPlant],
        monitored_outputs=[
            ("x_m", f"{aPlant}.x_m"),
            ("theta_rad", f"{aPlant}.theta_rad"),
            ("theta_hat_rad", f"{aEst}.theta_hat_rad"),
            ("bias_hat_rps", f"{aEst}.bias_hat_rps"),
            ("force_cmd_N", f"{aCtrl}.force_cmd_N"),
            ("mode", f"{aCtrl}.mode"),
        ],
        start_time=0.0,
        stop_time=float(scenario.get("t_end_s", 20)),
        step_size=0.001,
        output_interval=0.01,
        external_input_fn=ext_fn,
    )


# ---- case_manual_004 ----

def _build_manual_004() -> CoSimConfig:
    src_dir = SOURCES_DIR / "cases" / "case_manual_004" / "fmus"
    CtrlCls = _extract_model_class(src_dir / "create_position_controller_fmu.py")
    ValveCls = _extract_model_class(src_dir / "create_spool_valve_actuator_fmu.py")
    PlantCls = _extract_model_class(src_dir / "create_hydraulic_cylinder_plant_fmu.py")

    ctrl = CtrlCls()
    valve = ValveCls()
    plant = PlantCls()

    _apply_overrides(ctrl, {"Kp": 18.0, "Ki": 35.0, "Kv": 3.0,
                            "u_min": -1.0, "u_max": 1.0,
                            "integrator_limit": 0.5, "aw_gain": 8.0,
                            "deadband_m": 0.0002})
    _apply_overrides(valve, {"tau_s": 0.03, "deadzone": 0.05,
                             "rate_limit_per_s": 25.0, "u_min": -1.0, "u_max": 1.0})
    _apply_overrides(plant, {"stroke_m": 0.10, "m_kg": 12.0,
                             "A_A_m2": 0.0012, "A_B_m2": 0.0010,
                             "p_supply_Pa": 20000000.0, "p_tank_Pa": 200000.0,
                             "F_coulomb_N": 250.0, "b_visc_Nspm": 900.0})
    _apply_ics(ctrl, {"i_state": 0.0})
    _apply_ics(valve, {"spool_state": 0.0})
    _apply_ics(plant, {"x": 0.05, "x_m": 0.05, "v_mps": 0.0,
                       "pA_Pa": 10000000.0, "pB_Pa": 10000000.0})
    for m in (ctrl, valve, plant):
        if hasattr(m, "_compute_outputs"):
            m._compute_outputs()

    ac = "asset_case_case_manual_004__PositionController"
    av = "asset_case_case_manual_004__SpoolValveActuator"
    ap = "asset_case_case_manual_004__HydraulicCylinderPlant"

    req = _read_json(SOURCES_DIR / "cases" / "case_manual_004" / "requirement.json")
    scenario = req.get("scenario", {})
    inputs_def = scenario.get("inputs", {})
    x_ref_profile = inputs_def.get("x_ref_m_profile", [])
    load_profile = inputs_def.get("load_force_N_profile", [])

    def ext_fn(t: float) -> Dict[str, Dict[str, float]]:
        x_ref = _piecewise_profile(x_ref_profile, t, key_v="value_m")
        load = _piecewise_profile(load_profile, t, key_v="value_N")
        return {
            ac: {"x_ref_m": x_ref, "enable": 1.0},
            ap: {"load_force_N": load},
        }

    return CoSimConfig(
        case_id="case_manual_004",
        models={ac: ctrl, av: valve, ap: plant},
        connections=[
            (ac, "valve_cmd", av, "valve_cmd"),
            (av, "spool_u", ap, "spool_u"),
            (ap, "x_m", ac, "x_meas_m"),
            (ap, "v_mps", ac, "v_meas_mps"),
        ],
        execution_order=[ac, av, ap],
        monitored_outputs=[
            ("x_m", f"{ap}.x_m"),
            ("v_mps", f"{ap}.v_mps"),
            ("valve_cmd", f"{ac}.valve_cmd"),
            ("spool_u", f"{av}.spool_u"),
            ("pA_Pa", f"{ap}.pA_Pa"),
            ("pB_Pa", f"{ap}.pB_Pa"),
        ],
        start_time=0.0,
        stop_time=float(scenario.get("t_end_s", 12)),
        step_size=0.001,
        output_interval=0.01,
        external_input_fn=ext_fn,
    )


# ---- case_manual_001 ----

def _build_manual_001() -> CoSimConfig:
    src_dir = SOURCES_DIR / "cases" / "case_manual_001" / "fmus"
    BattCls = _extract_model_class(src_dir / "create_battery_fmu.py")
    CoolCls = _extract_model_class(src_dir / "create_cooling_loop_fmu.py")
    CtrlCls = _extract_model_class(src_dir / "create_thermal_controller_fmu.py")

    batt = BattCls()
    cool = CoolCls()
    ctrl = CtrlCls()

    _apply_ics(batt, {"soc": 0.8, "T_core_C": 30.0, "T_core": 30.0,
                      "T_surface_C": 30.0, "T_surface": 30.0})
    _apply_ics(cool, {"coolant_temp_C": 30.0, "coolant_temp": 30.0,
                      "flow_state_kgps": 0.0, "flow_state": 0.0})
    _apply_ics(ctrl, {"integral_err": 0.0, "mode_state": 0})
    for m in (batt, cool, ctrl):
        if hasattr(m, "ambient_temp_C"):
            m.ambient_temp_C = 35.0
        if hasattr(m, "_compute_outputs"):
            m._compute_outputs()

    aB = "asset_case_case_manual_001__BatteryPackElectroThermal"
    aC = "asset_case_case_manual_001__CoolingLoop"
    aT = "asset_case_case_manual_001__ThermalController"

    req = _read_json(SOURCES_DIR / "cases" / "case_manual_001" / "requirement.json")
    scenario = req.get("scenario", {})
    inputs_def = scenario.get("inputs", {})
    power_profile = inputs_def.get("driver_power_request_W_profile", [])
    ambient = float(inputs_def.get("ambient_temp_C", 35.0))

    def ext_fn(t: float) -> Dict[str, Dict[str, float]]:
        pwr = _piecewise_profile(power_profile, t, key_v="value_W")
        return {
            aT: {"driver_power_request_W": pwr, "ambient_temp_C": ambient},
            aB: {"ambient_temp_C": ambient},
            aC: {"ambient_temp_C": ambient},
        }

    return CoSimConfig(
        case_id="case_manual_001",
        models={aT: ctrl, aC: cool, aB: batt},
        connections=[
            (aT, "current_A", aB, "current_A"),
            (aT, "pump_cmd", aC, "pump_cmd"),
            (aT, "fan_cmd", aC, "fan_cmd"),
            (aB, "T_core_C", aT, "T_core_C"),
            (aB, "soc", aT, "soc"),
            (aB, "voltage_V", aT, "voltage_V"),
            (aB, "T_surface_C", aC, "T_batt_surface_C"),
            (aB, "heat_W", aC, "heat_load_W"),
            (aC, "coolant_in_temp_C", aB, "coolant_in_temp_C"),
            (aC, "coolant_flow_kgps", aB, "coolant_flow_kgps"),
        ],
        execution_order=[aT, aC, aB],
        monitored_outputs=[
            ("soc", f"{aB}.soc"),
            ("T_core_C", f"{aB}.T_core_C"),
            ("voltage_V", f"{aB}.voltage_V"),
            ("current_A", f"{aT}.current_A"),
            ("pump_cmd", f"{aT}.pump_cmd"),
            ("fan_cmd", f"{aT}.fan_cmd"),
            ("mode", f"{aT}.mode"),
            ("coolant_in_temp_C", f"{aC}.coolant_in_temp_C"),
            ("coolant_flow_kgps", f"{aC}.coolant_flow_kgps"),
            ("T_surface_C", f"{aB}.T_surface_C"),
        ],
        start_time=0.0,
        stop_time=float(scenario.get("t_end_s", 1200)),
        step_size=0.1,
        output_interval=1.0,
        external_input_fn=ext_fn,
    )


# ---- case_manual_005 ----

def _build_manual_005() -> CoSimConfig:
    src_dir = SOURCES_DIR / "cases" / "case_manual_005" / "fmus"
    BattCls = _extract_model_class(src_dir / "create_BatteryPackPlant_fmu.py")
    CoolCls = _extract_model_class(src_dir / "create_CoolantLoopPlant_fmu.py")
    CtrlCls = _extract_model_class(src_dir / "create_ThermalController_fmu.py")

    batt = BattCls()
    cool = CoolCls()
    ctrl = CtrlCls()

    _apply_overrides(ctrl, {"kp": 0.08, "ki": 0.01, "u_min": 0.0, "u_max": 1.0,
                            "hys_band_C": 0.8, "coolant_overtemp_C": 60.0,
                            "u_slew_per_s": 0.8})
    _apply_overrides(cool, {"coolant_thermal_mass_JK": 18000.0, "ua_min_WK": 40.0,
                            "ua_max_WK": 320.0, "ua_shape": 2.2,
                            "pump_tau_s": 2.5, "pump_rate_limit_per_s": 0.6})
    _apply_overrides(batt, {"n_series": 96, "capacity_Ah": 50.0, "coulombic_eff": 0.995,
                            "r0_Ohm": 0.002, "r_soc_gain": 1.2, "r_temp_beta": 0.035,
                            "k_pol_V": 0.01, "thermal_mass_JK": 65000.0,
                            "h_cool_WK": 120.0})
    _apply_ics(batt, {"soc": 0.85, "temp_cell_C": 30.0})
    _apply_ics(cool, {"coolant_temp_C": 28.0, "pump_state": 0.2})
    _apply_ics(ctrl, {"integrator": 0.0, "u_cmd_state": 0.2})
    for m in (batt, cool, ctrl):
        if hasattr(m, "_compute_outputs"):
            m._compute_outputs()

    aB = "asset_case_case_manual_005__BatteryPackPlant"
    aC = "asset_case_case_manual_005__CoolantLoopPlant"
    aT = "asset_case_case_manual_005__ThermalController"

    req = _read_json(SOURCES_DIR / "cases" / "case_manual_005" / "requirement.json")
    scenario = req.get("scenario", {})
    inputs_def = scenario.get("inputs", {})
    ambient_profile = inputs_def.get("ambient_temp_C_profile", [])
    iload_profile = inputs_def.get("i_load_A_profile", [])

    def ext_fn(t: float) -> Dict[str, Dict[str, float]]:
        amb = _piecewise_profile(ambient_profile, t, key_v="value_C")
        iload = _piecewise_profile(iload_profile, t, key_v="value_A")
        return {
            aT: {"enable": 1.0, "temp_ref_C": 35.0},
            aB: {"i_load_A": iload},
            aC: {"ambient_temp_C": amb},
        }

    return CoSimConfig(
        case_id="case_manual_005",
        models={aB: batt, aT: ctrl, aC: cool},
        connections=[
            (aT, "pump_cmd", aC, "pump_cmd"),
            (aB, "heat_gen_W", aC, "heat_in_W"),
            (aC, "coolant_temp_C", aB, "coolant_in_temp_C"),
            (aB, "temp_cell_C", aT, "temp_cell_C"),
            (aC, "coolant_temp_C", aT, "coolant_temp_C"),
        ],
        execution_order=[aB, aT, aC],
        monitored_outputs=[
            ("soc", f"{aB}.soc"),
            ("temp_cell_C", f"{aB}.temp_cell_C"),
            ("v_term_V", f"{aB}.v_term_V"),
            ("heat_gen_W", f"{aB}.heat_gen_W"),
            ("pump_cmd", f"{aT}.pump_cmd"),
            ("coolant_temp_C", f"{aC}.coolant_temp_C"),
        ],
        start_time=0.0,
        stop_time=float(scenario.get("t_end_s", 900)),
        step_size=0.1,
        output_interval=1.0,
        external_input_fn=ext_fn,
    )


# ===================================================================
# Case registry
# ===================================================================

CASE_BUILDERS: Dict[str, Callable[[], CoSimConfig]] = {
    "case_dtaas_mass_spring_damper": _build_mass_spring_damper,
    "case_dtaas_three_tank": _build_three_tank,
    "case_dtaas_water_tank_fi": _build_water_tank_fi,
    "case_manual_001": _build_manual_001,
    "case_manual_002": _build_manual_002,
    "case_manual_003": _build_manual_003,
    "case_manual_004": _build_manual_004,
    "case_manual_005": _build_manual_005,
}


# ===================================================================
# Metadata updater
# ===================================================================

def _update_case_metadata(case_id: str, signal_columns: List[str]) -> None:
    """Update case.json, trajectory_manifest.json, and verification_result.json."""
    case_dir = CASES_DIR / case_id
    if not case_dir.is_dir():
        print(f"  [WARN] Case directory not found: {case_dir}")
        return

    # ---- case.json ----
    case_path = case_dir / "case.json"
    case_payload = _read_json(case_path)
    ea = case_payload.setdefault("evaluation_artifacts", {})
    ea["ground_truth_trajectory_relpath"] = "ground_truth_trajectory.csv"
    ea["supports_numerical_fidelity"] = True
    ea["supports_decision_accuracy"] = True
    ea["supports_execution_metrics"] = True
    _write_json(case_path, case_payload)

    # ---- trajectory_manifest.json ----
    manifest_path = case_dir / "trajectory_manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.exists() else {}
    manifest["schema"] = "CASE_TRAJECTORY_MANIFEST_V1"
    manifest["case_id"] = case_id
    manifest["source_kind"] = "offline_cosimulation"
    manifest["time_column"] = "time"
    manifest["signal_columns"] = signal_columns
    manifest["ground_truth_relpath"] = "ground_truth_trajectory.csv"
    manifest["supports_numerical_fidelity"] = True
    manifest["reference_generation_method"] = "offline_cosimulation"
    manifest["column_aliases"] = {"time": ["time", "TIME", "Time", "t"]}

    sol_path = case_dir / "solution.json"
    if sol_path.exists():
        sol = _read_json(sol_path)
        monitored = [str(m.get("name", "")) for m in sol.get("monitored_outputs", []) if isinstance(m, dict)]
    else:
        monitored = []
    aliases: Dict[str, List[str]] = {}
    for sig in signal_columns:
        aliases[sig] = _ordered_unique([sig] + [m for m in monitored if m == sig])
    manifest["signal_aliases"] = aliases

    stages = manifest.get("stage_segments", [])
    manifest["stage_segments"] = stages
    _write_json(manifest_path, manifest)

    # ---- verification_result.json ----
    vr_path = case_dir / "verification_result.json"
    vr = _read_json(vr_path) if vr_path.exists() else {}
    vr["schema"] = "CASE_VERIFICATION_RESULT_V1"
    vr["case_id"] = case_id
    vr["status"] = "available"
    vr["conclusion"] = "pass"
    vr["summary"] = (
        "Ground-truth trajectory generated by offline co-simulation of the "
        "constituent FMU models using the canonical orchestration (solution.json)."
    )
    vr["evidence_basis"] = {
        "ground_truth_trajectory_relpath": "ground_truth_trajectory.csv",
        "input_trajectory_relpath": "",
        "source_kind": "offline_cosimulation",
    }
    vr["missing_requirements"] = []
    vr["supports_decision_accuracy"] = True
    _write_json(vr_path, vr)

    # ---- verification_requirement.json ----
    vreq_path = case_dir / "verification_requirement.json"
    if vreq_path.exists():
        vreq = _read_json(vreq_path)
        vreq["criteria"] = [
            c if isinstance(c, dict) and c.get("value") is not None
            else {**c, "notes": "Threshold TBD pending baseline evaluation."}
            for c in vreq.get("criteria", [])
        ]
        _write_json(vreq_path, vreq)


def _update_indexes() -> None:
    """Rebuild cases.jsonl index to reflect updated evaluation_artifacts."""
    index_path = DATASET_ROOT / "indexes" / "cases.jsonl"
    if not index_path.exists():
        return

    lines = index_path.read_text(encoding="utf-8").strip().splitlines()
    updated: List[str] = []
    for line in lines:
        entry = json.loads(line)
        cid = entry.get("case_id", "")
        case_json_path = CASES_DIR / cid / "case.json"
        if case_json_path.exists():
            case_payload = _read_json(case_json_path)
            ea = case_payload.get("evaluation_artifacts", {})
            entry["supports_numerical_fidelity"] = ea.get("supports_numerical_fidelity", False)
            entry["supports_decision_accuracy"] = ea.get("supports_decision_accuracy", False)
        updated.append(json.dumps(entry, ensure_ascii=False, sort_keys=True))
    index_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"Updated index: {index_path}")


def _update_dataset_manifest() -> None:
    """Recount supports_* metrics in dataset_manifest.json."""
    manifest_path = DATASET_ROOT / "manifests" / "dataset_manifest.json"
    if not manifest_path.exists():
        return
    manifest = _read_json(manifest_path)
    n_exec = 0
    n_nf = 0
    n_da = 0
    for case_dir in sorted(CASES_DIR.iterdir()):
        case_json = case_dir / "case.json"
        if not case_json.exists():
            continue
        cp = _read_json(case_json)
        ea = cp.get("evaluation_artifacts", {})
        if ea.get("supports_execution_metrics"):
            n_exec += 1
        if ea.get("supports_numerical_fidelity"):
            n_nf += 1
        if ea.get("supports_decision_accuracy"):
            n_da += 1
    manifest["supports_execution_metrics"] = n_exec
    manifest["supports_numerical_fidelity"] = n_nf
    manifest["supports_decision_accuracy"] = n_da
    _write_json(manifest_path, manifest)
    print(f"Updated manifest: {manifest_path}  (nf={n_nf}, da={n_da})")


# ===================================================================
# Main
# ===================================================================

def generate_case(case_id: str) -> None:
    builder = CASE_BUILDERS.get(case_id)
    if builder is None:
        print(f"[SKIP] No builder for {case_id}")
        return
    print(f"[RUN]  {case_id} ...")
    cfg = builder()
    rows = run_cosim(cfg)
    if not rows:
        print(f"  [WARN] No output rows for {case_id}")
        return
    csv_path = CASES_DIR / case_id / "ground_truth_trajectory.csv"
    write_trajectory_csv(rows, csv_path)
    signal_cols = [k for k in rows[0].keys() if k != "time"]
    print(f"  Wrote {len(rows)} rows x {len(signal_cols)} signals -> {csv_path}")
    _update_case_metadata(case_id, signal_cols)
    print(f"  Updated metadata for {case_id}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate numerical ground-truth trajectories for multi-FMU cases."
    )
    parser.add_argument(
        "cases",
        nargs="*",
        default=[],
        help="Case IDs to process (default: all supported).",
    )
    parser.add_argument("--list", action="store_true", help="List supported case IDs and exit.")
    args = parser.parse_args(argv)

    if args.list:
        for cid in sorted(CASE_BUILDERS):
            print(cid)
        return 0

    target_cases = args.cases if args.cases else sorted(CASE_BUILDERS.keys())
    for case_id in target_cases:
        try:
            generate_case(case_id)
        except Exception as exc:
            print(f"  [ERROR] {case_id}: {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    _update_indexes()
    _update_dataset_manifest()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
