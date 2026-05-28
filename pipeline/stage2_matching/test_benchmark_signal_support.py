from __future__ import annotations

from pipeline.stage1_decomposition.grounding import ground_taskset_to_mbse, validate_grounded_taskset
from pipeline.stage2_matching.feasibility import check_signal_support
from pipeline.types import FMU, MBSEComponent, MBSEContext, MBSEPort, PortMeta, TaskSet, VerificationTask


def test_grounding_retains_requirement_signals_for_generic_benchmark_ports() -> None:
    mbse_context = MBSEContext(
        package_name="ControlledTemperature",
        system_name="ControlledTemperatureModel",
        components=[
            MBSEComponent(
                name="ControlledTemperatureModel",
                component_type="ControlledTemperatureModel",
                ports=[MBSEPort(component="ControlledTemperatureModel", name="output", direction="unknown")],
            )
        ],
    )
    raw_taskset = TaskSet(
        tasks=[
            VerificationTask(
                task_id="task-0",
                objective="verify outputs",
                required_signals=["outputs[1]", "outputs[2]"],
                grounded_components=["ControlledTemperatureModel"],
            )
        ]
    )

    grounded = ground_taskset_to_mbse(raw_taskset, mbse_context)
    report = validate_grounded_taskset(grounded, mbse_context)

    assert grounded.tasks[0].required_signals == ["outputs[1]", "outputs[2]"]
    assert grounded.tasks[0].diagnostics["retained_requirement_signals_without_exact_mbse_port"] is True
    assert report.valid is True


def test_signal_support_requires_exact_indexed_benchmark_outputs() -> None:
    task = VerificationTask(
        task_id="task-0",
        objective="verify outputs",
        required_signals=["outputs[1]", "outputs[2]"],
        grounded_components=["ControlledTemperatureModel"],
    )
    generic_output_fmu = FMU(
        uid="asset_bench_fmu-generic",
        name="GenericOutputModel",
        ports=[PortMeta(name="output", causality="output")],
        outputs=["output"],
    )
    exact_output_fmu = FMU(
        uid="asset_bench_fmu-exact",
        name="ExactOutputModel",
        ports=[
            PortMeta(name="outputs[1]", causality="output"),
            PortMeta(name="outputs[2]", causality="output"),
        ],
        outputs=["outputs[1]", "outputs[2]"],
    )

    assert check_signal_support(task, generic_output_fmu) is False
    assert check_signal_support(task, exact_output_fmu) is True
