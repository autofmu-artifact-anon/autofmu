"""Pipeline execution entrypoints for evaluator and CLI use."""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path
from queue import Empty
from typing import Any, Dict, Iterable, List, Set

from pipeline.dataset_loader import LoadedCase
from pipeline.runtime_engine import run_execution_backend


def _split_endpoint(endpoint: Any) -> tuple[str, str]:
    text = str(endpoint or "").strip()
    if "." not in text:
        return "", ""
    asset_id, signal_name = text.split(".", 1)
    return asset_id.strip(), signal_name.strip()


def _selected_asset_ids(predicted_solution: Dict[str, Any]) -> List[str]:
    return [str(item) for item in predicted_solution.get("selected_asset_ids", []) if str(item).strip()]


def _known_port_names(fmu: Any) -> Set[str]:
    return {
        str(getattr(port, "name", "")).strip()
        for port in getattr(fmu, "ports", [])
        if str(getattr(port, "name", "")).strip()
    }


def _validate_simulation_package(*, loaded: LoadedCase, predicted_solution: Dict[str, Any], simulation_config: Any) -> List[str]:
    selected_asset_ids = _selected_asset_ids(predicted_solution)
    selected_fmus = list(getattr(simulation_config, "fmus", []) or [])
    fmu_by_id = {
        str(getattr(fmu, "uid", "")).strip(): fmu
        for fmu in selected_fmus
        if str(getattr(fmu, "uid", "")).strip()
    }
    errors: List[str] = []

    if not bool(loaded.evaluation_artifacts.get("supports_execution_metrics")):
        errors.append("case_does_not_support_execution_metrics")
    if not selected_asset_ids:
        errors.append("predicted_solution.selected_asset_ids is empty")

    for asset_id in selected_asset_ids:
        fmu = fmu_by_id.get(asset_id)
        if fmu is None:
            errors.append(f"selected asset missing from simulation_config.fmus: {asset_id}")
            continue
        fmu_path = Path(str(getattr(fmu, "path", "") or "")).expanduser()
        if not fmu_path.exists():
            errors.append(f"FMU path does not exist: {asset_id} -> {fmu_path}")

    for index, connection in enumerate(list(getattr(simulation_config, "connections", []) or [])):
        if not isinstance(connection, dict):
            errors.append(f"connection[{index}] is not a mapping")
            continue
        source_asset, source_signal = _split_endpoint(connection.get("source"))
        target_asset, target_signal = _split_endpoint(connection.get("target"))
        if not source_asset or not source_signal or not target_asset or not target_signal:
            errors.append(f"connection[{index}] has malformed endpoints")
            continue
        source_fmu = fmu_by_id.get(source_asset)
        target_fmu = fmu_by_id.get(target_asset)
        if source_fmu is None:
            errors.append(f"connection[{index}] references unknown source asset: {source_asset}")
            continue
        if target_fmu is None:
            errors.append(f"connection[{index}] references unknown target asset: {target_asset}")
            continue
        if source_signal not in _known_port_names(source_fmu):
            errors.append(f"connection[{index}] unknown source signal: {source_asset}.{source_signal}")
        if target_signal not in _known_port_names(target_fmu):
            errors.append(f"connection[{index}] unknown target signal: {target_asset}.{target_signal}")

    if float(getattr(simulation_config, "duration", 0.0) or 0.0) <= 0.0:
        errors.append("simulation_config.duration must be positive")
    if float(getattr(simulation_config, "step_size", 0.0) or 0.0) <= 0.0:
        errors.append("simulation_config.step_size must be positive")
    return errors


def execute_case(
    *,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    simulation_config: Any,
    artifact_root: Path,
    timeout_seconds: float | None = None,
) -> Dict[str, Any]:
    if timeout_seconds is None:
        return _execute_case_impl(
            loaded=loaded,
            predicted_solution=predicted_solution,
            simulation_config=simulation_config,
            artifact_root=artifact_root,
        )

    timeout_value = float(timeout_seconds)
    if timeout_value <= 0.0:
        raise ValueError("timeout_seconds must be positive when provided")

    context_name = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
    context = multiprocessing.get_context(context_name)
    result_queue: Any = context.Queue(maxsize=1)
    process = context.Process(
        target=_execute_case_worker,
        kwargs={
            "result_queue": result_queue,
            "loaded": loaded,
            "predicted_solution": predicted_solution,
            "simulation_config": simulation_config,
            "artifact_root": artifact_root,
        },
    )
    process.start()
    process.join(timeout_value)
    if process.is_alive():
        process.terminate()
        process.join()
        return _timeout_result(
            loaded=loaded,
            predicted_solution=predicted_solution,
            started=time.perf_counter() - timeout_value,
            timeout_seconds=timeout_value,
        )

    try:
        result = result_queue.get(timeout=1.0)
    except Empty:
        if process.exitcode and process.exitcode != 0:
            return _runtime_error_result(
                loaded=loaded,
                predicted_solution=predicted_solution,
                started=time.perf_counter(),
                error_text=f"ChildProcessError: execution worker exited with code {process.exitcode}",
            )
        return _runtime_error_result(
            loaded=loaded,
            predicted_solution=predicted_solution,
            started=time.perf_counter(),
            error_text="ChildProcessError: execution worker produced no result",
        )
    if isinstance(result, dict):
        return result
    return _runtime_error_result(
        loaded=loaded,
        predicted_solution=predicted_solution,
        started=time.perf_counter(),
        error_text=f"ChildProcessError: unexpected execution worker payload {type(result).__name__}",
    )


def _execute_case_worker(
    *,
    result_queue: Any,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    simulation_config: Any,
    artifact_root: Path,
) -> None:
    result_queue.put(
        _execute_case_impl(
            loaded=loaded,
            predicted_solution=predicted_solution,
            simulation_config=simulation_config,
            artifact_root=artifact_root,
        )
    )


def _execute_case_impl(
    *,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    simulation_config: Any,
    artifact_root: Path,
) -> Dict[str, Any]:
    started = time.perf_counter()
    cwd = Path.cwd()
    selected_asset_ids = _selected_asset_ids(predicted_solution)
    validation_errors = _validate_simulation_package(
        loaded=loaded,
        predicted_solution=predicted_solution,
        simulation_config=simulation_config,
    )
    observed_signals = [
        str(item.get("name") or item.get("signal") or "").strip()
        for item in predicted_solution.get("monitored_outputs", [])
        if isinstance(item, dict) and str(item.get("name") or item.get("signal") or "").strip()
    ]
    warnings: List[str] = []
    if validation_errors:
        return _base_result(
            loaded=loaded,
            predicted_solution=predicted_solution,
            started=started,
            success=False,
            backend="validation_only",
            runtime_mode="none",
            decision_evidence={},
            warnings=warnings,
            error_text="; ".join(validation_errors),
        )

    try:
        run = run_execution_backend(
            loaded=loaded,
            predicted_solution=predicted_solution,
            simulation_config=simulation_config,
            artifact_root=artifact_root,
        )
        sample_count = 0
        if run.path.exists():
            with run.path.open("r", encoding="utf-8", newline="") as handle:
                sample_count = max(sum(1 for _ in handle) - 1, 0)
        warnings.extend(run.warnings)
        return _base_result(
            loaded=loaded,
            predicted_solution=predicted_solution,
            started=started,
            success=True,
            backend=run.backend,
            runtime_mode=run.runtime_mode,
            generated_trajectory_path=run.path.as_posix(),
            generated_trajectory_sample_count=sample_count,
            time_column=run.time_column,
            signal_columns=list(run.signal_columns),
            decision_evidence=dict(run.decision_evidence),
            warnings=warnings,
            error_text=None,
        )
    except Exception as exc:  # noqa: BLE001
        return _runtime_error_result(
            loaded=loaded,
            predicted_solution=predicted_solution,
            started=started,
            error_text=f"{type(exc).__name__}: {exc}",
            warnings=warnings,
        )
    finally:
        try:
            os.chdir(cwd)
        except FileNotFoundError:
            pass


def _base_result(
    *,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    started: float,
    success: bool,
    backend: str,
    runtime_mode: str,
    generated_trajectory_path: str = "",
    generated_trajectory_sample_count: int = 0,
    time_column: str | None = None,
    signal_columns: List[str] | None = None,
    decision_evidence: Dict[str, Any] | None = None,
    warnings: Iterable[Any] = (),
    error_text: str | None = None,
    timeout_seconds: float | None = None,
) -> Dict[str, Any]:
    return {
        "schema": "PIPELINE_EXECUTION_RESULT_V2",
        "case_id": loaded.case_id,
        "selected_asset_ids": _selected_asset_ids(predicted_solution),
        "success": bool(success),
        "backend": backend,
        "runtime_mode": runtime_mode,
        "execution_time_seconds": time.perf_counter() - started,
        "generated_trajectory_path": generated_trajectory_path,
        "generated_trajectory_sample_count": int(generated_trajectory_sample_count),
        "supports_execution_metrics": bool(loaded.evaluation_artifacts.get("supports_execution_metrics")),
        "supports_numerical_fidelity": bool(loaded.evaluation_artifacts.get("supports_numerical_fidelity")),
        "supports_decision_accuracy": bool(loaded.evaluation_artifacts.get("supports_decision_accuracy")),
        "observed_signals": [
            str(item.get("name") or item.get("signal") or "").strip()
            for item in predicted_solution.get("monitored_outputs", [])
            if isinstance(item, dict) and str(item.get("name") or item.get("signal") or "").strip()
        ],
        "time_column": str(time_column or loaded.trajectory_manifest_payload.get("time_column") or ""),
        "signal_columns": signal_columns
        if signal_columns is not None
        else [str(item) for item in loaded.trajectory_manifest_payload.get("signal_columns", []) if str(item).strip()],
        "supported_metrics": {
            "execution": bool(loaded.evaluation_artifacts.get("supports_execution_metrics")),
            "numerical_fidelity": bool(loaded.evaluation_artifacts.get("supports_numerical_fidelity")),
            "decision_accuracy": bool(loaded.evaluation_artifacts.get("supports_decision_accuracy")),
        },
        "decision_evidence": dict(decision_evidence or {}),
        "warnings": _ordered_unique_text(warnings),
        "timed_out": backend == "timeout",
        "timeout_seconds": timeout_seconds,
        "error": error_text,
    }


def _runtime_error_result(
    *,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    started: float,
    error_text: str,
    warnings: Iterable[Any] = (),
) -> Dict[str, Any]:
    return _base_result(
        loaded=loaded,
        predicted_solution=predicted_solution,
        started=started,
        success=False,
        backend="runtime_error",
        runtime_mode="failed",
        decision_evidence={},
        warnings=warnings,
        error_text=error_text,
    )


def _timeout_result(
    *,
    loaded: LoadedCase,
    predicted_solution: Dict[str, Any],
    started: float,
    timeout_seconds: float,
) -> Dict[str, Any]:
    return _base_result(
        loaded=loaded,
        predicted_solution=predicted_solution,
        started=started,
        success=False,
        backend="timeout",
        runtime_mode="timed_out",
        decision_evidence={},
        warnings=[],
        error_text=f"TimeoutError: execution exceeded {timeout_seconds:.3f} seconds",
        timeout_seconds=timeout_seconds,
    )


def _ordered_unique_text(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
