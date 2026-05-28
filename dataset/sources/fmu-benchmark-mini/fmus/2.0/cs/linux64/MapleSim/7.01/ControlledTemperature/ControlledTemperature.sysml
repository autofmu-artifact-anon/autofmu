package ControlledTemperature {
    // 参数定义
    attribute def TAmb :> Real; // Main.TAmb
    attribute def TDif :> Real; // Main.TDif

    // 输出定义
    attribute def reference :> Real; // Main.onOffController.reference(t)
    attribute def TempInput :> Real; // Main.TempInput.value(t)

    // 端口定义
    port def OutputPort {
        out attribute reference: Real;
        out attribute TempInput: Real;
    }

    // 主要部件定义
    part def TemperatureController {
        attribute TAmb: TAmb;
        attribute TDif: TDif;
        part output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }
}
