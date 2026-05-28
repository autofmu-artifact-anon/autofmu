package ControlledTemperature {
    // 输入输出端口定义
    port def OutputPort {
        out attribute output1: Real;
        out attribute output2: Real;
    }

    // 参数定义
    part def ControlledTemperatureModel {
        attribute TAmb: Real; // Ambient Temperature
        attribute TDif: Real; // Error in Temperature
        attribute minsamplestep: Real; // Minimum time step between samples in binary data file
        attribute binfilename: String; // Name of binary data file

        port output: OutputPort;
    }

    // 特性定义
    feature def OutputFeature {
        part controlledTemperatureModel: ControlledTemperatureModel;
    }

    // 场景定义
    scenario def StepScenario {
        kind: step;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }

    scenario def RampScenario {
        kind: ramp;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }

    scenario def SineScenario {
        kind: sine;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }
}
