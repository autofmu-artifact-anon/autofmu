package RectifierModel {
    // 端口定义
    port def OutputPort {
        out attribute v: Real;
    }

    // 具体实现
    part def Rectifier {
        part output: OutputPort;

        // 输出属性定义
        attribute v: Real;
    }

    // 场景定义
    scenario def StepScenario {
        kind: step;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 0.001;
        seed: 0;
    }

    scenario def RampScenario {
        kind: ramp;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 0.001;
        seed: 0;
    }

    scenario def SineScenario {
        kind: sine;
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 0.001;
        seed: 0;
    }
}
