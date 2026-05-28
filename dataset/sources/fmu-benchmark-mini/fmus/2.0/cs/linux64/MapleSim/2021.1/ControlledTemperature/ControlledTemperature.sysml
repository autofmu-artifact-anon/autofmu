package ControlledTemperature {
    // 输入输出端口定义
    port def OutputPort {
        out attribute value: Real;
        out attribute TempInput: Real;
    }

    // 参数定义
    part def ControlledTemperatureModel {
        attribute TAmb: Real; // Ambient Temperature
        attribute TDif: Real; // Error in Temperature
        attribute minsamplestep: Real; // Minimum time step between samples in binary data file
        attribute binfilename: String; // Name of binary data file

        // 输出端口
        port output: OutputPort;
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
