package ControlledTemperature {
    // 参数定义
    attribute def TAmb: Real[1] {
        causality: parameter;
        variability: fixed;
        unit: K;
    }
    
    attribute def TDif: Real[1] {
        causality: parameter;
        variability: fixed;
        unit: K;
    }

    // 输出定义
    attribute def reference: Real[1] {
        causality: output;
        variability: continuous;
        desc: "onOffController.reference";
    }

    attribute def TempInput: Real[1] {
        causality: output;
        variability: continuous;
        unit: degC;
        desc: "TempInput.value";
    }

    // 主要部件定义
    part def TemperatureController {
        attribute reference: reference;
        attribute TempInput: TempInput;
    }

    // 场景定义
    scenario def StepScenario {
        kind: step;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.05;
        seed: 0;
    }

    scenario def RampScenario {
        kind: ramp;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.05;
        seed: 0;
    }

    scenario def SineScenario {
        kind: sine;
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.05;
        seed: 0;
    }
}
