package RectifierModel {
    // 输出定义
    attribute def outputs :> Real {
        causality: output;
        variability: continuous;
        unit: V;
        desc: "Rectifier1.Capacitor1.v";
    }

    // 端口定义
    port def OutputPort {
        out attribute voltage: outputs;
    }

    // 主要部件定义
    part def Rectifier {
        part outputPort :>> OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }
}
