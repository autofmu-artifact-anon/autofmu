package ControlledTemperature {
    // 属性定义
    attribute def TAmb :> Real; // Ambient Temperature
    attribute def TDif :> Real; // Error in Temperature
    attribute def minsamplestep :> Real; // Minimum time step between samples in binary data file
    attribute def binfilename :> String; // Name of binary data file

    // 输出定义
    attribute def reference :> Real; // onOffController.reference
    attribute def TempInput_value :> Real; // TempInput.value

    // 端口定义
    port def OutputPort {
        out attribute reference: Real;
        out attribute TempInput_value: Real;
    }

    // 具体实现
    part def TemperatureController {
        attribute TAmb: TAmb;
        attribute TDif: TDif;
        attribute minsamplestep: minsamplestep;
        attribute binfilename: binfilename;
        part output: OutputPort;
    }
}
