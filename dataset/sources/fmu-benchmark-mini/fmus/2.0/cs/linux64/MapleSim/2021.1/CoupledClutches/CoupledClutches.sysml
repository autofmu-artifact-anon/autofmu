package CoupledClutches {
    // 输入定义
    port def InputPort {
        in attribute RI1: Real;
    }

    // 输出定义
    port def OutputPort {
        out attribute RO1: Real;
        out attribute RO2: Real;
        out attribute RO3: Real;
        out attribute RO4: Real;
    }

    // 参数定义
    part def CoupledClutchesModel {
        attribute T2: Real;
        attribute freqHz: Real;
        attribute minsamplestep: Real;
        attribute binfilename: String;

        port input: InputPort;
        port output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }
}
