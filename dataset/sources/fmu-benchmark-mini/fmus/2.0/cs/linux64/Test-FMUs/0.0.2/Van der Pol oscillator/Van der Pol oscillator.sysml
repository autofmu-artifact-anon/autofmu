package VanDerPolOscillator {
    // 输入输出端口定义
    port def OutputPort {
        out attribute x0: Real;
        out attribute x1: Real;
    }

    // 参数定义
    attribute def mu: Real;

    // 主要部件定义
    part def VanDerPol {
        attribute mu: mu;
        part output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.01;
        attribute seed: Integer = 0;
    }
}
