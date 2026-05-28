package ControlledTemperature {
    // 属性定义
    attribute def TAmb: Real[1] { causality = parameter, variability = fixed, unit = K; }
    attribute def TDif: Real[1] { causality = parameter, variability = fixed, unit = K; }

    // 输出定义
    attribute def reference: Real[1] { causality = output, variability = continuous; }
    attribute def TempInput: Real[1] { causality = output, variability = continuous, unit = degC; }

    // 端口定义
    port def OutputPort {
        out attribute reference: Real;
        out attribute TempInput: Real;
    }

    // 具体实现
    part def TemperatureController {
        part output: OutputPort;
    }
}
