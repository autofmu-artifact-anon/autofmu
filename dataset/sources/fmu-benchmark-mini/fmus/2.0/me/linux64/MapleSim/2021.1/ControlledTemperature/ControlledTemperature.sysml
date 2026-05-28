package ControlledTemperature {
    // 属性定义
    attribute def TAmb: Real; // Ambient Temperature
    attribute def TDif: Real; // Error in Temperature
    attribute def minsamplestep: Real; // Minimum time step between samples in binary data file
    attribute def binfilename: String; // Name of binary data file

    // 输出端口定义
    port def OutputPort {
        out attribute value: Real; // Input.value
        out attribute TempInput: Real; // TempInput.value
    }

    // 具体实现
    part def TemperatureController {
        part output: OutputPort;

        // 连接输出
        connect output.value to outputs[1];
        connect output.TempInput to outputs[2];
    }
}
