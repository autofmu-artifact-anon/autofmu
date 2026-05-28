#!/usr/bin/env python3
"""
FMU Semantic Enhancement Preprocessor

Batch processes FMU files to perform:
1) metadata parsing (modelDescription.xml etc.)
2) reproducible behavior probing scenarios (step, ramp, sine)
3) feature extraction that reflects dynamic behavior
4) semantic artifacts written next to each FMU (no modification of FMU zip)

The output is intended to feed later SysML generation and FMU matching.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

try:
    from fmpy import simulate_fmu, read_model_description
except Exception as e:  # pragma: no cover
    raise SystemExit("FMPy is required: pip install fmpy") from e

try:
    from scipy.signal import welch  # type: ignore
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False

try:
    import requests  # type: ignore
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

try:
    from tqdm import tqdm  # type: ignore
    TQDM_AVAILABLE = True
except Exception:
    TQDM_AVAILABLE = False


logger = logging.getLogger("enhance_fmu_semantics")

SCRIPT_DIR = Path(__file__).resolve().parent
def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(6):
        if (cur / "fmu-benchmark" / "scripts").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


REPO_ROOT = _find_repo_root(SCRIPT_DIR)
EXTRACTOR_DIR = REPO_ROOT / "fmu-benchmark" / "scripts"
if EXTRACTOR_DIR.exists():
    sys.path.insert(0, str(EXTRACTOR_DIR))


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _simple_type(var_type: str) -> str:
    if var_type in {"Real", "Float32", "Float64"}:
        return "Real"
    if var_type in {
        "Integer",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "Enumeration",
        "Clock",
    }:
        return "Integer"
    if var_type == "Boolean":
        return "Boolean"
    return var_type


def discover_fmus(root: Path) -> List[Path]:
    fmus: List[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".fmu"):
                fmus.append(Path(dirpath) / fn)
    return sorted(fmus)


def semantic_artifact_paths(fmu_path: Path) -> Dict[str, Path]:
    """Return expected artifact paths next to the FMU."""
    return {
        "semantic": fmu_path.with_suffix(".semantic.json"),
        "timeseries": fmu_path.with_suffix(".timeseries.csv.gz"),
        "report": fmu_path.with_suffix(".report.md"),
        "errors": fmu_path.with_suffix(".errors.json"),
    }


def semantic_is_valid(semantic_path: Path) -> bool:
    """Lightweight validation of a semantic.json file."""
    try:
        data = json.loads(semantic_path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and "version" in data and "features" in data
    except Exception:
        return False


def is_fmu_completed(fmu_path: Path) -> bool:
    """
    Determine if an FMU has completed semantic artifacts.
    Used for resume; requires semantic + timeseries + report.
    """
    paths = semantic_artifact_paths(fmu_path)
    if not (paths["semantic"].exists() and paths["timeseries"].exists() and paths["report"].exists()):
        return False
    return semantic_is_valid(paths["semantic"])


def extract_metadata(fmu_path: Path) -> Dict[str, Any]:
    """
    Prefer repository extractor for robustness.
    Fallback to fmpy.read_model_description.
    """
    try:
        from fmu_metadata_extractor import extract_fmu_metadata  # type: ignore

        return extract_fmu_metadata(fmu_path)
    except Exception as e:
        logger.debug("Repo metadata extractor failed for %s: %s", fmu_path, e)
        md = read_model_description(str(fmu_path), validate=False)
        variables = []
        for v in md.modelVariables:
            vt = _simple_type(v.type)
            variables.append(
                {
                    "name": v.name,
                    "valueReference": int(v.valueReference),
                    "causality": v.causality or "local",
                    "variability": v.variability or "continuous",
                    "type": vt,
                    "description": v.description or "",
                    "unit": getattr(v, "unit", "") or "",
                    "start": getattr(v, "start", None),
                    "min": getattr(v, "min", None),
                    "max": getattr(v, "max", None),
                    "nominal": getattr(v, "nominal", None),
                    "derivative": getattr(v, "derivative", None),
                }
            )
        return {
            "fmi": {
                "fmiVersion": md.fmiVersion,
                "fmiTypes": md.fmiTypes or [],
                "modelName": md.modelName or fmu_path.stem,
                "guid": md.guid or getattr(md, "instantiationToken", ""),
                "description": md.description or "",
                "author": md.author or "",
                "generationTool": md.generationTool or "",
                "generationDateAndTime": md.generationDateAndTime or "",
                "variableNamingConvention": md.variableNamingConvention or "flat",
                "numberOfEventIndicators": int(getattr(md, "numberOfEventIndicators", 0) or 0),
                "defaultExperiment": {
                    k: _safe_float(getattr(md.defaultExperiment, k, None))
                    for k in ["startTime", "stopTime", "stepSize", "tolerance"]
                    if _safe_float(getattr(md.defaultExperiment, k, None)) is not None
                },
            },
            "implementation": {"platforms": md.platforms or []},
            "variables": variables,
            "interface": {
                "inputs": [v.name for v in md.modelVariables if v.causality == "input"],
                "outputs": [v.name for v in md.modelVariables if v.causality == "output"],
            },
        }


def infer_fmi_type(meta: Dict[str, Any]) -> Optional[str]:
    types = meta.get("fmi", {}).get("fmiTypes", []) or []
    if "CoSimulation" in types:
        return "CoSimulation"
    if "ModelExchange" in types:
        return "ModelExchange"
    return None


def infer_sim_config(meta: Dict[str, Any], duration: Optional[float], step_size: Optional[float]) -> Tuple[float, float, float]:
    default_exp = meta.get("fmi", {}).get("defaultExperiment", {}) or {}
    start = _safe_float(default_exp.get("startTime"), 0.0) or 0.0
    stop = _safe_float(default_exp.get("stopTime"))
    dt = _safe_float(default_exp.get("stepSize"))

    if duration is not None:
        stop = start + duration
    if stop is None:
        stop = start + 5.0
    if step_size is not None:
        dt = step_size
    if dt is None or dt <= 0:
        dt = max((stop - start) / 200.0, 1e-3)

    return start, stop, dt


def select_inputs(variables: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    candidates = [
        v
        for v in variables
        if v.get("causality") == "input" and _simple_type(v.get("type", "")) in {"Real", "Integer", "Boolean"}
    ]
    def score(v: Dict[str, Any]) -> Tuple[int, int]:
        variability = v.get("variability", "continuous")
        var_score = 0 if variability == "continuous" else 1
        has_bounds = 0 if ("min" in v and "max" in v) else 1
        return (var_score, has_bounds)
    candidates.sort(key=score)
    return candidates[:top_k]


def select_outputs(variables: List[Dict[str, Any]], top_k: int) -> Tuple[List[Dict[str, Any]], str]:
    outs = [
        v
        for v in variables
        if v.get("causality") == "output" and _simple_type(v.get("type", "")) in {"Real", "Integer", "Boolean"}
    ]
    if outs:
        return outs[:top_k], "outputs"

    states = [v for v in variables if v.get("derivative") is not None and _simple_type(v.get("type", "")) == "Real"]
    if states:
        return states[:top_k], "states"

    locals_real = [v for v in variables if v.get("causality") == "local" and _simple_type(v.get("type", "")) == "Real"]
    if locals_real:
        return locals_real[:top_k], "locals"

    any_real = [v for v in variables if _simple_type(v.get("type", "")) == "Real"]
    return any_real[:top_k], "any_real"


def infer_scale(var: Dict[str, Any]) -> Tuple[float, float]:
    """Return (offset, scale) for signal generation."""
    vmin = _safe_float(var.get("min"))
    vmax = _safe_float(var.get("max"))
    nominal = _safe_float(var.get("nominal"))
    start = _safe_float(var.get("start"))

    if vmin is not None and vmax is not None and vmax > vmin and np.isfinite(vmin) and np.isfinite(vmax):
        scale = vmax - vmin
        offset = (vmax + vmin) / 2.0
    elif nominal is not None and nominal > 0 and np.isfinite(nominal):
        scale = 2.0 * nominal
        offset = start if start is not None else 0.0
    elif start is not None and np.isfinite(start):
        scale = max(abs(start) * 0.2, 1.0)
        offset = start
    else:
        scale = 1.0
        offset = 0.0
    return offset, scale


def clamp(x: np.ndarray, vmin: Optional[float], vmax: Optional[float]) -> np.ndarray:
    if vmin is not None:
        x = np.maximum(x, vmin)
    if vmax is not None:
        x = np.minimum(x, vmax)
    return x


def generate_input_signal(t: np.ndarray, var: Dict[str, Any], kind: str) -> np.ndarray:
    stype = _simple_type(var.get("type", "Real"))
    offset, scale = infer_scale(var)
    vmin = _safe_float(var.get("min"))
    vmax = _safe_float(var.get("max"))

    duration = t[-1] - t[0] if len(t) > 1 else 1.0
    if stype == "Boolean":
        step_time = t[0] + 0.3 * duration
        sig = np.where(t < step_time, 0.0, 1.0)
        return sig

    if stype == "Integer":
        low = offset - 0.5 * scale
        high = offset + 0.5 * scale
        if kind == "sine":
            kind = "ramp"
        if kind == "step":
            step_time = t[0] + 0.3 * duration
            sig = np.where(t < step_time, low, high)
        elif kind == "ramp":
            sig = np.linspace(low, high, len(t))
        else:
            sig = np.full(len(t), offset)
        sig = clamp(sig, vmin, vmax)
        return np.round(sig).astype(np.float64)

    # Real
    amp = 0.5 * scale
    low = offset - amp
    high = offset + amp

    if kind == "step":
        step_time = t[0] + 0.3 * duration
        sig = np.where(t < step_time, low, high)
    elif kind == "ramp":
        sig = np.linspace(low, high, len(t))
    elif kind == "sine":
        # at least 1-3 cycles in duration
        freq = max(1.0 / duration, 0.1)
        sig = offset + amp * np.sin(2 * np.pi * freq * (t - t[0]))
    else:
        sig = np.full(len(t), offset)

    return clamp(sig.astype(np.float64), vmin, vmax)


def build_input_data(inputs: List[Dict[str, Any]], t: np.ndarray, kind: str) -> Optional[np.ndarray]:
    if not inputs:
        return None
    dtype = [("time", np.float64)]
    for inp in inputs:
        dtype.append((inp["name"], np.float64))
    data = np.zeros(len(t), dtype=dtype)
    data["time"] = t
    for inp in inputs:
        data[inp["name"]] = generate_input_signal(t, inp, kind)
    return data


def run_simulation(
    fmu_path: Path,
    input_data: Optional[np.ndarray],
    start: float,
    stop: float,
    dt: float,
    observe: Sequence[str],
    fmi_type: Optional[str],
    timeout: float,
) -> np.ndarray:
    try:
        sim = simulate_fmu(
            str(fmu_path),
            start_time=start,
            stop_time=stop,
            output_interval=dt,
            fmi_type=fmi_type,
            input=input_data,
            output=list(observe) if observe else None,
            validate=False,
            timeout=timeout,
            record_events=True,
        )
        return np.asarray(sim)
    except Exception:
        # fallback without output filter
        sim = simulate_fmu(
            str(fmu_path),
            start_time=start,
            stop_time=stop,
            output_interval=dt,
            fmi_type=fmi_type,
            input=input_data,
            validate=False,
            timeout=timeout,
            record_events=True,
        )
        return np.asarray(sim)


def basic_stats(y: np.ndarray) -> Dict[str, float]:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y)]
    if len(y) == 0:
        return {}
    return {
        "mean": float(np.mean(y)),
        "variance": float(np.var(y)),
        "std": float(np.std(y)),
        "min": float(np.min(y)),
        "max": float(np.max(y)),
        "peak_to_peak": float(np.ptp(y)),
        "first": float(y[0]),
        "last": float(y[-1]),
    }


def steady_state(y: np.ndarray, frac: float = 0.1) -> Optional[float]:
    y = np.asarray(y, dtype=np.float64)
    if len(y) < 5:
        return None
    n_tail = max(int(len(y) * frac), 1)
    tail = y[-n_tail:]
    tail = tail[np.isfinite(tail)]
    if len(tail) == 0:
        return None
    return float(np.mean(tail))


def step_metrics(t: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    if len(t) < 5:
        return {}
    y = np.asarray(y, dtype=np.float64)
    finite = np.isfinite(y)
    t = t[finite]
    y = y[finite]
    if len(t) < 5:
        return {}

    n_head = max(int(0.1 * len(y)), 1)
    baseline = float(np.mean(y[:n_head]))
    final = steady_state(y) or float(y[-1])
    amp = final - baseline
    if abs(amp) < 1e-8:
        return {"baseline": baseline, "final": final, "amplitude": amp}

    # normalize for positive amplitude
    yn = (y - baseline) / amp
    # rise time 10%->90%
    try:
        t10 = t[np.where(yn >= 0.1)[0][0]]
        t90 = t[np.where(yn >= 0.9)[0][0]]
        rise_time = float(t90 - t10)
    except Exception:
        rise_time = None

    # overshoot
    if amp > 0:
        overshoot = float((np.max(y) - final) / amp)
    else:
        overshoot = float((np.min(y) - final) / amp)

    # settling time within 2%
    band = 0.02
    upper = final + band * abs(amp)
    lower = final - band * abs(amp)
    settling_time = None
    for i in range(len(y)):
        if np.all((y[i:] >= lower) & (y[i:] <= upper)):
            settling_time = float(t[i] - t[0])
            break

    # steady slope to detect integrator-like
    tail_n = max(int(len(y) * 0.2), 2)
    tail_t = t[-tail_n:]
    tail_y = y[-tail_n:]
    try:
        coeff = np.polyfit(tail_t - tail_t[0], tail_y, 1)
        steady_slope = float(coeff[0])
    except Exception:
        steady_slope = 0.0

    return {
        "baseline": baseline,
        "final": final,
        "amplitude": float(amp),
        "rise_time": rise_time,
        "overshoot_ratio": overshoot,
        "settling_time": settling_time,
        "steady_slope": steady_slope,
    }


def spectral_metrics(t: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    y = np.asarray(y, dtype=np.float64)
    finite = np.isfinite(y)
    y = y[finite]
    t = t[finite]
    if len(y) < 8:
        return {}
    dt = float(np.median(np.diff(t)))
    if dt <= 0:
        return {}
    fs = 1.0 / dt
    y0 = y - np.mean(y)

    if SCIPY_AVAILABLE:
        nperseg = min(256, len(y0))
        freqs, psd = welch(y0, fs=fs, nperseg=nperseg)
    else:
        freqs = np.fft.rfftfreq(len(y0), dt)
        psd = np.abs(np.fft.rfft(y0)) ** 2

    mask = freqs > 0
    freqs = freqs[mask]
    psd = psd[mask]
    if len(psd) == 0 or float(np.sum(psd)) <= 0:
        return {}

    total = float(np.sum(psd))
    dom_idx = int(np.argmax(psd))
    dom_freq = float(freqs[dom_idx])
    dom_power_ratio = float(psd[dom_idx] / total)
    centroid = float(np.sum(freqs * psd) / total)
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * psd) / total))
    low_ratio = float(np.sum(psd[freqs <= centroid]) / total)

    return {
        "dominant_frequency_hz": dom_freq,
        "dominant_power_ratio": dom_power_ratio,
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "low_freq_energy_ratio": low_ratio,
    }


def lag_phase(u: np.ndarray, y: np.ndarray, t: np.ndarray, dom_freq: Optional[float]) -> Dict[str, Any]:
    u = np.asarray(u, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    finite = np.isfinite(u) & np.isfinite(y)
    u = u[finite]
    y = y[finite]
    t = t[finite]
    if len(u) < 8:
        return {}
    u0 = u - np.mean(u)
    y0 = y - np.mean(y)
    corr = np.correlate(y0, u0, mode="full")
    lags = np.arange(-len(u0) + 1, len(u0))
    lag_idx = int(lags[np.argmax(corr)])
    dt = float(np.median(np.diff(t)))
    lag_sec = float(lag_idx * dt)
    phase = None
    if dom_freq and dom_freq > 0:
        phase = float(2 * np.pi * dom_freq * lag_sec)
    return {"lag_seconds": lag_sec, "phase_radians_at_dom_freq": phase}


def stability_flags(y: np.ndarray, var_meta: Dict[str, Any]) -> Dict[str, Any]:
    y = np.asarray(y, dtype=np.float64)
    finite_mask = np.isfinite(y)
    diverged = not np.all(finite_mask)
    y_f = y[finite_mask] if np.any(finite_mask) else y

    vmin = _safe_float(var_meta.get("min"))
    vmax = _safe_float(var_meta.get("max"))
    saturated = False
    if vmin is not None or vmax is not None:
        tol = 0.01 * (abs(vmax - vmin) if (vmin is not None and vmax is not None) else 1.0)
        if vmin is not None:
            saturated |= bool(np.mean(y_f <= vmin + tol) > 0.1)
        if vmax is not None:
            saturated |= bool(np.mean(y_f >= vmax - tol) > 0.1)

    # jump / event density estimate
    if len(y_f) >= 3:
        dy = np.diff(y_f)
        dy_std = float(np.std(dy)) or 0.0
        jump_thr = max(5.0 * dy_std, 1e-6)
        jump_count = int(np.sum(np.abs(dy) > jump_thr))
    else:
        jump_count = 0

    return {
        "diverged": diverged,
        "saturated": saturated,
        "jump_count": jump_count,
    }


def label_behavior(
    basic: Dict[str, float],
    step_m: Dict[str, Any],
    spec_m: Dict[str, Any],
    flags: Dict[str, Any],
    duration: float,
) -> List[str]:
    labels: List[str] = []
    if flags.get("diverged"):
        labels.append("divergent")
        return labels

    ptp = basic.get("peak_to_peak", 0.0)
    std = basic.get("std", 0.0)
    if ptp < 1e-6 or std < 1e-6:
        labels.append("dead-zone")

    if flags.get("saturated"):
        labels.append("saturation")

    if flags.get("jump_count", 0) / max(duration, 1e-6) > 5.0:
        labels.append("discrete-event-heavy")

    dom_ratio = spec_m.get("dominant_power_ratio")
    dom_freq = spec_m.get("dominant_frequency_hz")
    if dom_ratio is not None and dom_ratio > 0.3 and dom_freq is not None and dom_freq > 0:
        labels.append("oscillatory")

    steady_slope = step_m.get("steady_slope")
    settling_time = step_m.get("settling_time")
    amp = step_m.get("amplitude", 0.0)
    if steady_slope is not None and abs(steady_slope) > 0.05 * abs(amp) / max(duration, 1e-6):
        if settling_time is None:
            labels.append("integrator-like")

    if not labels:
        low_ratio = spec_m.get("low_freq_energy_ratio", 0.0)
        if low_ratio > 0.7:
            labels.append("low-pass-like")
        else:
            labels.append("other")

    return sorted(set(labels))


@dataclass
class ScenarioConfig:
    kind: str
    start_time: float
    stop_time: float
    step_size: float
    seed: int = 0


@dataclass
class ScenarioOutcome:
    kind: str
    success: bool
    error: str = ""
    timeseries: Optional[pd.DataFrame] = None


def call_llm_guidance(
    meta: Dict[str, Any],
    base_url: str,
    model: str,
    api_key: Optional[str],
    timeout: float,
) -> Dict[str, Any]:
    if not api_key:
        return {}
    if not REQUESTS_AVAILABLE:
        return {}

    # keep prompt small for reproducibility/cost
    vars_short = []
    for v in meta.get("variables", [])[:200]:
        vars_short.append(
            {
                "name": v.get("name", ""),
                "causality": v.get("causality", ""),
                "variability": v.get("variability", ""),
                "type": _simple_type(v.get("type", "")),
                "unit": v.get("unit", ""),
                "description": v.get("description", "")[:80],
            }
        )

    prompt = {
        "task": "Propose a reasonable reproducible usage scenario for probing FMU behavior.",
        "constraints": [
            "Return JSON only.",
            "Select up to 3 representative inputs and up to 5 representative outputs by exact name.",
            "Scenario must include step, ramp, sine excitations.",
            "Do not invent variables not in the list.",
        ],
        "model_info": meta.get("fmi", {}),
        "variables": vars_short,
        "output_schema": {
            "inputs": ["..."],
            "outputs": ["..."],
            "narrative": "short scenario description",
        },
    }

    messages = [
        {"role": "system", "content": "You are a careful FMI/FMUs engineer."},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
    ]
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        r = requests.post(base_url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return {"prompt": prompt, "raw_response": content}
    except Exception as e:
        return {"prompt": prompt, "error": str(e)}


def apply_llm_selection(
    guidance: Dict[str, Any],
    variables: List[Dict[str, Any]],
    inputs: List[Dict[str, Any]],
    outputs: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    raw = guidance.get("raw_response")
    if not raw:
        return inputs, outputs, None
    try:
        parsed = json.loads(raw)
    except Exception:
        return inputs, outputs, None

    var_by_name = {v.get("name"): v for v in variables}
    new_inputs: List[Dict[str, Any]] = []
    for name in parsed.get("inputs", [])[:3]:
        v = var_by_name.get(name)
        if v and v.get("causality") == "input":
            new_inputs.append(v)
    new_outputs: List[Dict[str, Any]] = []
    for name in parsed.get("outputs", [])[:5]:
        v = var_by_name.get(name)
        if v:
            new_outputs.append(v)
    narrative = parsed.get("narrative")
    if new_inputs:
        inputs = new_inputs
    if new_outputs:
        outputs = new_outputs
    return inputs, outputs, narrative


def process_single_fmu(args: Tuple[Path, argparse.Namespace]) -> Dict[str, Any]:
    fmu_path, ns = args
    t0 = time.time()
    semantic_path = fmu_path.with_suffix(".semantic.json")
    timeseries_path = fmu_path.with_suffix(".timeseries.csv.gz")
    report_path = fmu_path.with_suffix(".report.md")
    errors_path = fmu_path.with_suffix(".errors.json")

    if is_fmu_completed(fmu_path) and (ns.resume or not ns.overwrite):
        return {"file": str(fmu_path), "status": "SKIPPED", "reason": "artifacts exist"}

    meta = extract_metadata(fmu_path)
    variables = meta.get("variables", []) or []

    inputs = select_inputs(variables, ns.top_k_inputs)
    outputs, outputs_source = select_outputs(variables, ns.top_k_outputs)

    llm_guidance: Dict[str, Any] = {}
    narrative: Optional[str] = None
    if ns.llm_guidance and ns.llm_api_key:
        llm_guidance = call_llm_guidance(
            meta=meta,
            base_url=ns.llm_base_url,
            model=ns.llm_model,
            api_key=ns.llm_api_key,
            timeout=ns.llm_timeout,
        )
        inputs, outputs, narrative = apply_llm_selection(llm_guidance, variables, inputs, outputs)

    start, stop, dt = infer_sim_config(meta, ns.duration, ns.step_size)
    duration = stop - start
    t = np.arange(start, stop + dt * 0.5, dt, dtype=np.float64)

    fmi_type = infer_fmi_type(meta)
    observe_names = [v["name"] for v in outputs]

    scenarios = [
        ScenarioConfig(kind="step", start_time=start, stop_time=stop, step_size=dt, seed=ns.seed),
        ScenarioConfig(kind="ramp", start_time=start, stop_time=stop, step_size=dt, seed=ns.seed),
        ScenarioConfig(kind="sine", start_time=start, stop_time=stop, step_size=dt, seed=ns.seed),
    ]

    outcomes: Dict[str, ScenarioOutcome] = {}
    all_success = False
    for sc in scenarios:
        try:
            inp_data = build_input_data(inputs, t, sc.kind)
            sim_res = run_simulation(
                fmu_path=fmu_path,
                input_data=inp_data,
                start=sc.start_time,
                stop=sc.stop_time,
                dt=sc.step_size,
                observe=observe_names,
                fmi_type=fmi_type,
                timeout=ns.timeout,
            )
            df = pd.DataFrame(sim_res)
            df["scenario"] = sc.kind
            outcomes[sc.kind] = ScenarioOutcome(kind=sc.kind, success=True, timeseries=df)
            all_success = True
        except Exception as e:
            outcomes[sc.kind] = ScenarioOutcome(kind=sc.kind, success=False, error=str(e))

    if not all_success:
        err = {
            "file": str(fmu_path),
            "stage": "simulation",
            "errors": {k: v.error for k, v in outcomes.items()},
            "traceback": traceback.format_exc(),
            "config": {
                "start_time": start,
                "stop_time": stop,
                "step_size": dt,
                "timeout": ns.timeout,
                "selected_inputs": [v["name"] for v in inputs],
                "selected_outputs": observe_names,
            },
            "timestamp": _now_iso(),
        }
        errors_path.write_text(json.dumps(err, indent=2, ensure_ascii=False))
        return {"file": str(fmu_path), "status": "FAILED", "reason": "all scenarios failed"}

    # Build combined timeseries for save
    ts_frames = []
    for o in outcomes.values():
        if o.success and o.timeseries is not None:
            ts_frames.append(o.timeseries)
    ts_all = pd.concat(ts_frames, ignore_index=True)

    # keep only key vars
    keep_cols = ["time", "scenario"] + [v["name"] for v in inputs] + observe_names
    keep_cols = [c for c in keep_cols if c in ts_all.columns]
    ts_all = ts_all[keep_cols]
    if ns.max_points and len(ts_all) > ns.max_points:
        stride = int(np.ceil(len(ts_all) / ns.max_points))
        ts_all = ts_all.iloc[::stride].reset_index(drop=True)

    # gzip csv
    with gzip.open(timeseries_path, "wt", encoding="utf-8") as f:
        ts_all.to_csv(f, index=False)

    # Feature extraction
    features: Dict[str, Any] = {}
    per_var_labels: Dict[str, List[str]] = {}
    dom_freqs: List[float] = []

    # use step and sine scenarios primarily
    step_df = outcomes.get("step").timeseries if outcomes.get("step") else None
    sine_df = outcomes.get("sine").timeseries if outcomes.get("sine") else None
    ramp_df = outcomes.get("ramp").timeseries if outcomes.get("ramp") else None

    for var in outputs:
        name = var["name"]
        vmeta = var
        var_feat: Dict[str, Any] = {"variable_meta": {k: vmeta.get(k) for k in ["name", "causality", "variability", "type", "unit", "min", "max", "nominal", "start"]}}

        # gather trajectories
        y_step = step_df[name].to_numpy() if step_df is not None and name in step_df else None
        y_sine = sine_df[name].to_numpy() if sine_df is not None and name in sine_df else None
        y_ramp = ramp_df[name].to_numpy() if ramp_df is not None and name in ramp_df else None

        t_step = step_df["time"].to_numpy() if step_df is not None else t
        t_sine = sine_df["time"].to_numpy() if sine_df is not None else t
        t_ramp = ramp_df["time"].to_numpy() if ramp_df is not None else t

        if y_step is not None:
            b = basic_stats(y_step)
            sm = step_metrics(t_step, y_step)
            fl = stability_flags(y_step, vmeta)
        else:
            b, sm, fl = {}, {}, {"diverged": False, "saturated": False, "jump_count": 0}

        if y_sine is not None:
            sp = spectral_metrics(t_sine, y_sine)
        else:
            sp = {}

        if sp.get("dominant_frequency_hz"):
            dom_freqs.append(float(sp["dominant_frequency_hz"]))

        # lag/phase against first input if possible
        lag_info: Dict[str, Any] = {}
        if inputs and y_sine is not None and sine_df is not None:
            in_name = inputs[0]["name"]
            if in_name in sine_df:
                u = sine_df[in_name].to_numpy()
                lag_info = lag_phase(u, y_sine, t_sine, sp.get("dominant_frequency_hz"))

        labels = label_behavior(b, sm, sp, fl, duration)
        per_var_labels[name] = labels

        var_feat.update(
            {
                "basic_stats": b,
                "steady_state": steady_state(y_step) if y_step is not None else None,
                "step_metrics": sm,
                "spectral_metrics": sp,
                "lag_phase": lag_info,
                "stability_flags": fl,
                "behavior_labels": labels,
            }
        )

        # ramp stats (optional)
        if y_ramp is not None:
            var_feat["ramp_basic_stats"] = basic_stats(y_ramp)

        features[name] = var_feat

    # FMU-level summary
    all_labels = sorted({lab for labs in per_var_labels.values() for lab in labs})
    max_dom_freq = max(dom_freqs) if dom_freqs else None
    if max_dom_freq and max_dom_freq > 0:
        recommended_dt = 1.0 / (20.0 * max_dom_freq)
    else:
        recommended_dt = dt
    recommended_dt_range = [recommended_dt / 2.0, recommended_dt * 2.0]

    fmu_profile = {
        "num_inputs": len(inputs),
        "num_outputs_observed": len(outputs),
        "outputs_source": outputs_source,
        "continuous_ratio": float(
            np.mean([v.get("variability") == "continuous" for v in variables]) if variables else 0.0
        ),
        "recommended_step_size_range": recommended_dt_range,
        "typical_dynamic_labels": all_labels,
    }

    probe_config = {
        "start_time": start,
        "stop_time": stop,
        "step_size": dt,
        "scenarios": [asdict(sc) for sc in scenarios],
        "selected_inputs": [v["name"] for v in inputs],
        "selected_outputs": observe_names,
        "narrative": narrative or "Generic excitation on representative inputs (step/ramp/sine).",
    }

    log_summary = {
        "scenario_status": {k: ("ok" if v.success else "failed") for k, v in outcomes.items()},
        "scenario_errors": {k: v.error for k, v in outcomes.items() if v.error},
        "elapsed_sec": float(time.time() - t0),
    }

    semantic = {
        "version": "0.1.0",
        "timestamp": _now_iso(),
        "file": str(fmu_path),
        "metadata_summary": {
            "fmi": meta.get("fmi", {}),
            "implementation": meta.get("implementation", {}),
        },
        "variables": {
            "all": [
                {
                    **{k: v.get(k) for k in ["name", "causality", "variability", "type", "unit", "min", "max", "nominal", "start", "description"]},
                    "writable": v.get("causality") in {"input", "parameter", "structuralParameter"},
                }
                for v in variables
            ],
            "inputs": [v for v in inputs],
            "outputs_observed": [v for v in outputs],
        },
        "probe_config": probe_config,
        "features": features,
        "fmu_profile": fmu_profile,
        "llm_guidance": llm_guidance if ns.llm_guidance else {},
        "log_summary": log_summary,
    }

    semantic_path.write_text(json.dumps(semantic, indent=2, ensure_ascii=False))

    # Report
    lines = []
    fmi_info = meta.get("fmi", {})
    lines.append(f"# FMU Semantic Report: `{fmu_path.name}`")
    lines.append("")
    lines.append("## Model Info")
    lines.append(f"- modelName: `{fmi_info.get('modelName','')}`")
    lines.append(f"- fmiVersion: `{fmi_info.get('fmiVersion','')}`")
    lines.append(f"- fmiTypes: `{','.join(fmi_info.get('fmiTypes',[]) or [])}`")
    if fmi_info.get("generationTool"):
        lines.append(f"- generationTool: `{fmi_info.get('generationTool')}`")
    lines.append("")
    lines.append("## Selected Interface")
    lines.append(f"- inputs ({len(inputs)}): " + ", ".join(f"`{v['name']}`" for v in inputs) if inputs else "- inputs: (none)")
    lines.append(f"- outputs observed ({len(outputs)} from {outputs_source}): " + ", ".join(f"`{v['name']}`" for v in outputs) if outputs else "- outputs: (none)")
    lines.append("")
    lines.append("## Probe Scenario")
    lines.append(f"- start_time: `{start}`")
    lines.append(f"- stop_time: `{stop}`")
    lines.append(f"- step_size: `{dt}`")
    lines.append(f"- narrative: {probe_config['narrative']}")
    lines.append("")
    lines.append("## FMU Profile")
    lines.append(f"- typical_dynamic_labels: `{', '.join(all_labels)}`")
    lines.append(f"- recommended_step_size_range: `{recommended_dt_range[0]:.4g} .. {recommended_dt_range[1]:.4g}`")
    lines.append("")
    lines.append("## Variable Features (key)")
    for name, feat in features.items():
        b = feat.get("basic_stats", {})
        sm = feat.get("step_metrics", {})
        sp = feat.get("spectral_metrics", {})
        labs = feat.get("behavior_labels", [])
        lines.append(f"### `{name}`")
        if b:
            lines.append(f"- mean/std/ptp: `{b.get('mean',0):.4g}` / `{b.get('std',0):.4g}` / `{b.get('peak_to_peak',0):.4g}`")
        if sm.get("rise_time") is not None:
            lines.append(f"- rise/settling/overshoot: `{sm.get('rise_time')}` / `{sm.get('settling_time')}` / `{sm.get('overshoot_ratio'):.3g}`")
        if sp.get('dominant_frequency_hz') is not None:
            lines.append(f"- dominant_frequency_hz: `{sp.get('dominant_frequency_hz'):.4g}` (power ratio `{sp.get('dominant_power_ratio',0):.3g}`)")
        lines.append(f"- labels: `{', '.join(labs)}`")
        lines.append("")

    if log_summary["scenario_errors"]:
        lines.append("## Scenario Errors")
        for k, v in log_summary["scenario_errors"].items():
            lines.append(f"- {k}: `{v}`")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Cleanup old errors if present
    if errors_path.exists():
        try:
            errors_path.unlink()
        except Exception:
            pass

    return {"file": str(fmu_path), "status": "OK", "elapsed": log_summary["elapsed_sec"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch enhance FMU semantics")
    parser.add_argument("--root", type=Path, required=True, help="Root directory containing FMUs")
    parser.add_argument("--jobs", type=int, default=max(os.cpu_count() or 1, 1), help="Parallel jobs")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-scenario simulation timeout (sec)")
    parser.add_argument("--duration", type=float, default=None, help="Override stop-start duration (sec)")
    parser.add_argument("--step-size", type=float, default=None, help="Override output step size (sec)")
    parser.add_argument("--top-k-inputs", type=int, default=3, help="Max inputs to excite")
    parser.add_argument("--top-k-outputs", type=int, default=5, help="Max outputs to observe")
    parser.add_argument("--max-points", type=int, default=2000, help="Max rows stored in timeseries file")
    parser.add_argument("--seed", type=int, default=0, help="Seed for deterministic signals")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing semantic artifacts")
    parser.add_argument("--resume", action="store_true", help="Resume by skipping FMUs with completed artifacts")
    parser.add_argument("--retry-failed", action="store_true", help="When resuming, retry FMUs that have errors.json")
    parser.add_argument("--progress", action="store_true", help="Show progress bar")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    # LLM guidance
    parser.add_argument("--llm-guidance", action="store_true", help="Use LLM to suggest representative IO/scenario (optional)")
    parser.add_argument("--llm-api-key", default=os.getenv("GPTGOD_API_KEY"), help="LLM API key (or env GPTGOD_API_KEY)")
    parser.add_argument("--llm-base-url", default="https://api.gptgod.online/v1/chat/completions", help="LLM base url")
    parser.add_argument("--llm-model", default="gpt-5.1-all", help="LLM model name")
    parser.add_argument("--llm-timeout", type=float, default=20.0, help="LLM request timeout (sec)")

    ns = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, ns.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    root = ns.root.resolve()
    fmus = discover_fmus(root)
    if not fmus:
        logger.error("No FMU files found under %s", root)
        sys.exit(1)

    discovered_total = len(fmus)
    logger.info("Discovered %d FMUs", discovered_total)

    if ns.resume:
        completed: List[Path] = []
        pending: List[Path] = []
        for p in fmus:
            if is_fmu_completed(p):
                if ns.retry_failed and p.with_suffix(".errors.json").exists():
                    pending.append(p)
                else:
                    completed.append(p)
            else:
                pending.append(p)
        logger.info("Resume enabled: %d completed, %d pending", len(completed), len(pending))
        fmus = pending

    if not fmus:
        logger.info("Nothing to do. All FMUs already processed.")
        return

    args_list = [(p, ns) for p in fmus]
    results: List[Dict[str, Any]] = []

    with ProcessPoolExecutor(max_workers=ns.jobs) as ex:
        futs = [ex.submit(process_single_fmu, a) for a in args_list]
        ok_n = skip_n = fail_n = 0
        pbar = None
        if ns.progress and TQDM_AVAILABLE:
            pbar = tqdm(total=len(futs), desc="Enhancing FMUs", unit="fmu")

        for fut in as_completed(futs):
            try:
                r = fut.result()
                results.append(r)
                status = r.get("status")
                if status == "OK":
                    ok_n += 1
                    logger.info("OK %s (%.2fs)", r["file"], r.get("elapsed", 0))
                elif status == "SKIPPED":
                    skip_n += 1
                    logger.info("SKIP %s (%s)", r["file"], r.get("reason"))
                else:
                    fail_n += 1
                    logger.warning("FAIL %s (%s)", r.get("file"), r.get("reason"))
            except Exception as e:
                fail_n += 1
                logger.exception("Worker failed: %s", e)
            finally:
                if pbar is not None:
                    pbar.update(1)
                    pbar.set_postfix(ok=ok_n, skipped=skip_n, failed=fail_n)

        if pbar is not None:
            pbar.close()

    summary = {
        "timestamp": _now_iso(),
        "root": str(root),
        "discovered_total": discovered_total,
        "processed_total": len(fmus),
        "ok": sum(1 for r in results if r.get("status") == "OK"),
        "skipped": sum(1 for r in results if r.get("status") == "SKIPPED"),
        "failed": sum(1 for r in results if r.get("status") == "FAILED"),
    }
    logger.info("Summary: %s", summary)


if __name__ == "__main__":
    main()
