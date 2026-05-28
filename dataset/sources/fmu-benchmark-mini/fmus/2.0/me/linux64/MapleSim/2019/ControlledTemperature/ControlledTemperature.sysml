package ControlledTemperature {
    // 属性定义
    attribute def TAmb :> Real; // Ambient Temperature
    attribute def TDif :> Real; // Error in Temperature
    attribute def minsamplestep :> Real; // Minimum time step between samples in binary data file
    attribute def binfilename :> String; // Name of binary data file

    // 输出定义
    port def OutputPort {
        out attribute reference: Real; // onOffController.reference
        out attribute value: Real; // TempInput.value
    }

    // 具体实现
    part def TemperatureController {
        attribute TAmb :>> ControlledTemperature::TAmb;
        attribute TDif :>> ControlledTemperature::TDif;
        attribute minsamplestep :>> ControlledTemperature::minsamplestep;
        attribute binfilename :>> ControlledTemperature::binfilename;
        part output :>> OutputPort;
    }
}
