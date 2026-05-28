package CoupledClutches {
    // 输入定义
    port def InputPort {
        in attribute inputs: Real;
    }

    // 输出定义
    port def OutputPort {
        out attribute outputs1: Real;
        out attribute outputs2: Real;
        out attribute outputs3: Real;
        out attribute outputs4: Real;
    }

    // 参数定义
    part def CoupledClutchesModel {
        attribute CoupledClutches1_T2: Real;
        attribute CoupledClutches1_freqHz: Real;
        attribute minsamplestep: Real;
        attribute binfilename: String;

        port input: InputPort;
        port output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 1.5;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }
}
