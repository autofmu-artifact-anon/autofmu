package ControlledTemperature {
    // 属性定义
    attribute def TAmb: Real[1] <<parameter, fixed, unit=K>>; // Ambient temperature
    attribute def TDif: Real[1] <<parameter, fixed, unit=K>>; // Temperature difference
    attribute def minsamplestep: Real[1] <<parameter, fixed, unit=s>>; // Minimum time step between samples
    attribute def binfilename: String[1] <<parameter, fixed>>; // Name of binary data file

    // 端口定义
    port def OutputPort {
        out attribute reference: Real; // onOffController.reference
        out attribute value: Real <<unit=degC>>; // TempInput.value
    }

    // 具体实现
    part def TemperatureController {
        part output: OutputPort;
    }

    // 特征定义
    feature def Outputs {
        part output: OutputPort;
    }

    // 场景定义
    scenario def StepScenario {
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }

    scenario def RampScenario {
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }

    scenario def SineScenario {
        start_time: 0.0;
        stop_time: 10.0;
        step_size: 0.001;
        seed: 0;
    }
}
