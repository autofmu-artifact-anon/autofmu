package ControlledTemperature {
    // 参数定义
    attribute def TAmb: Real { causality = parameter, variability = fixed, unit = K; }
    attribute def TDif: Real { causality = parameter, variability = fixed, unit = K; }

    // 输出定义
    attribute def reference: Real { causality = output, variability = continuous; }
    attribute def TempInput: Real { causality = output, variability = continuous, unit = degC; }

    // 主要部件定义
    part def TemperatureController {
        // 输出端口
        port def OutputPort {
            out attribute reference: Real;
            out attribute TempInput: Real;
        }
    }
}
