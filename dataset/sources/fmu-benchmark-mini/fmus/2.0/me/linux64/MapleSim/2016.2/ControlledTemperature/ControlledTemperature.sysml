package ControlledTemperature {
    // 属性定义
    attribute def TAmb: Real[1] { causality = parameter, variability = fixed, unit = K, desc = "TAmb" };
    attribute def TDif: Real[1] { causality = parameter, variability = fixed, unit = K, desc = "TDif" };
    attribute def minsamplestep: Real[1] { causality = parameter, variability = fixed, unit = s, desc = "Minimum time step between samples in binary data file" };
    attribute def binfilename: String[1] { causality = parameter, variability = fixed, desc = "Name of binary data file" };

    // 输出定义
    attribute def reference: Real[1] { causality = output, variability = continuous, desc = "onOffController.reference" };
    attribute def TempInput: Real[1] { causality = output, variability = continuous, unit = degC, desc = "TempInput.value" };

    // 主要部件定义
    part def TemperatureController {
        attribute reference: reference;
        attribute TempInput: TempInput;
    }
}
