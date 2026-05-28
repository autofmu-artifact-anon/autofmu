package ControlledTemperature {
    // 属性定义
    attribute def TAmb: Real[1] { causality = parameter, variability = fixed, unit = K; }
    attribute def TDif: Real[1] { causality = parameter, variability = fixed, unit = K; }

    // 输出定义
    attribute def reference: Real[1] { causality = output, variability = continuous; }
    attribute def TempInput: Real[1] { causality = output, variability = continuous, unit = degC; }

    // 具体实现
    part def TemperatureController {
        attribute TAmb: TAmb;
        attribute TDif: TDif;
        attribute reference: reference;
        attribute TempInput: TempInput;
    }

    // 端口定义
    port def OutputPort {
        out attribute reference: Real;
        out attribute TempInput: Real;
    }

    // 系统内部结构 (IBD)
    part def ControlledTemperatureSystem {
        part controller: TemperatureController;

        // 外部端口
        port output: OutputPort;

        // 内部连接
        connect controller.reference to output.reference;
        connect controller.TempInput to output.TempInput;
    }
}
