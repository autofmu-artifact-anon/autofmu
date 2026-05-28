package FMICrossCheck {
    // 属性定义
    attribute def TRes :> Real;

    // 参数定义
    attribute def TAmb :> Real;
    attribute def TDif :> Real;
    attribute def constantVoltage_V :> Real;
    attribute def heatCapacitor_C :> Real;
    attribute def heatingResistor_R_ref :> Real;
    attribute def heatingResistor_T_ref :> Real;
    attribute def heatingResistor_alpha :> Real;
    attribute def thermalConductor_G :> Real;
    attribute def idealSwitch_Ron :> Real;
    attribute def idealSwitch_Goff :> Real;
    attribute def idealSwitch_T :> Real;
    attribute def ramp_height :> Real;
    attribute def ramp_duration :> Real;
    attribute def ramp_offset :> Real;
    attribute def ramp_startTime :> Real;
    attribute def onOffController_pre_y_start :> Boolean;

    // 端口定义
    port def OutputPort {
        out attribute TRes: Real;
    }

    // 具体实现
    part def ControlledTemperature {
        part output: OutputPort;
    }
}
