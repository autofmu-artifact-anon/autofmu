#!/usr/bin/env python3
"""Offline synthetic simulation for the ship propulsion reference case.

Generates eight monitored signals across a 300-second, five-phase operating
profile.  The signal dynamics are consistent with the case study described
in the paper (Section 5.5) and with the figure generators in latex/.

Outputs
-------
output/simulated_timeseries.csv
    Time-series data for all monitored signals plus environment inputs.
output/command_events.csv
    Phase-transition events with cruise speed and sea state values.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import numpy as np


CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "output"
N_POINTS = 3000
T_END = 300.0


def _load_json(name: str) -> dict:
    with open(CASE_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _ramp(t: np.ndarray, t0: float, t1: float, v0: float, v1: float) -> np.ndarray:
    frac = np.clip((t - t0) / (t1 - t0), 0.0, 1.0)
    return v0 + (v1 - v0) * frac


def build_environment(t: np.ndarray):
    cruise_speed = np.piecewise(
        t,
        [t < 40, (t >= 40) & (t < 100), (t >= 100) & (t < 160),
         (t >= 160) & (t < 240), t >= 240],
        [lambda t: _ramp(t, 0, 40, 0, 12),
         lambda t: np.full_like(t, 12.0),
         lambda t: np.full_like(t, 12.0),
         lambda t: np.full_like(t, 14.0),
         lambda t: _ramp(t, 240, 300, 14, 8)],
    )
    sea_state = np.piecewise(
        t,
        [t < 100, (t >= 100) & (t < 160), (t >= 160) & (t < 240), t >= 240],
        [2.0, 6.0, 4.0, 3.0],
    )
    return cruise_speed, sea_state


def build_signals(t: np.ndarray, cruise_speed: np.ndarray, sea_state: np.ndarray):
    rng = np.random.default_rng(42)

    rpm_target = cruise_speed * (114.7 / 14.0)
    tau_rpm = 8.0
    rpm = np.zeros_like(t)
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        rpm[i] = rpm[i - 1] + (rpm_target[i] - rpm[i - 1]) * dt / tau_rpm
    rpm += rng.normal(0, 0.05, len(t))
    rpm = np.clip(rpm, 0, 130)

    kt_base = 0.18 + 0.07 * (rpm / 114.7)
    kt = np.clip(kt_base, 0.170, 0.260)

    thrust = 0.08 * rpm ** 2 * (kt / 0.22)
    thrust = np.clip(thrust, 0, 900)

    stress_base = 0.3 + 0.5 * (rpm / 114.7)
    stress_transient = np.zeros_like(t)
    for t0 in [0, 40, 100, 160, 240]:
        mask = (t >= t0) & (t < t0 + 15)
        stress_transient[mask] += 0.15 * np.exp(-(t[mask] - t0) / 4.0)
    shaft_stress = np.clip(stress_base + stress_transient, 0, 0.90)
    idx_peak = np.argmin(np.abs(t - 163))
    shaft_stress[idx_peak - 5 : idx_peak + 10] = np.linspace(0.78, 0.82, 15)

    cav_base = 0.6 - 0.3 * (rpm / 114.7) - 0.05 * (sea_state / 6.0)
    cav = np.clip(cav_base, 0.05, 1.0)
    phase3_mask = (t >= 100) & (t < 160)
    cav[phase3_mask] = np.clip(cav[phase3_mask] - 0.15, 0.10, 1.0)
    idx_cav_min = np.argmin(np.abs(t - 130))
    cav[idx_cav_min - 3 : idx_cav_min + 3] = 0.12

    res = np.clip(0.3 + 0.4 * (rpm / 114.7) + 0.1 * (sea_state / 6.0), 0.10, 0.90)

    therm_base = 0.4 - 0.25 * (rpm / 114.7) - 0.1 * (sea_state / 6.0)
    therm = np.clip(therm_base, 0.05, 0.5)
    idx_therm_min = np.argmin(np.abs(t - 155))
    therm[idx_therm_min - 5 : idx_therm_min + 5] = np.linspace(0.10, 0.08, 10)

    sfoc = np.clip(200 - 10 * (rpm / 114.7), 170, 240)

    return {
        "K_T": kt,
        "RPM": rpm,
        "Thrust": thrust,
        "cavitation_margin": cav,
        "resistance_margin": res,
        "shaft_torsional_stress": shaft_stress,
        "thermal_margin": therm,
        "SFOC": sfoc,
    }


def write_timeseries(
    path: Path,
    t: np.ndarray,
    cruise_speed: np.ndarray,
    sea_state: np.ndarray,
    signals: dict[str, np.ndarray],
) -> None:
    headers = ["time", "cruise_speed", "sea_state"] + list(signals.keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(len(t)):
            row = [
                f"{t[i]:.4f}",
                f"{cruise_speed[i]:.4f}",
                f"{sea_state[i]:.1f}",
            ]
            for key in signals:
                row.append(f"{signals[key][i]:.6f}")
            writer.writerow(row)


def write_command_events(
    path: Path,
    phases: list[dict],
) -> None:
    headers = ["time", "phase", "cruise_speed_kn", "sea_state"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for phase in phases:
            writer.writerow({
                "time": phase["start_s"],
                "phase": phase["name"],
                "cruise_speed_kn": phase["cruise_speed_kn"],
                "sea_state": phase["sea_state"],
            })


def main() -> None:
    requirement = _load_json("requirement.json")
    phases = requirement["scenario"]["phases"]

    t = np.linspace(0, T_END, N_POINTS)
    cruise_speed, sea_state = build_environment(t)
    signals = build_signals(t, cruise_speed, sea_state)

    ts_path = OUTPUT_DIR / "simulated_timeseries.csv"
    write_timeseries(ts_path, t, cruise_speed, sea_state, signals)
    print(f"Wrote {len(t)} rows to {ts_path}")

    ev_path = OUTPUT_DIR / "command_events.csv"
    write_command_events(ev_path, phases)
    print(f"Wrote {len(phases)} events to {ev_path}")


if __name__ == "__main__":
    main()
