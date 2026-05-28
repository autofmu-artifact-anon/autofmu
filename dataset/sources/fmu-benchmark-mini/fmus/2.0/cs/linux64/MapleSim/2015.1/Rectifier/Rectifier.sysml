package RectifierModel {
    // 输出定义
    attribute def outputs: Real;

    // 端口定义
    port def OutputPort {
        out attribute outputs: Real;
    }

    // 具体实现
    part def Rectifier {
        part outputPort: OutputPort;

        // 输出属性
        attribute outputs: outputs;
    }

    // 场景定义
    scenario def StepScenario {
        kind: step;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }

    scenario def RampScenario {
        kind: ramp;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }

    scenario def SineScenario {
        kind: sine;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }
}
