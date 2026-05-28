package VanDerPolOscillator {
    // 属性定义
    attribute def mu :> Real;

    // 端口定义
    port def OutputPort {
        out attribute x0: Real;
        out attribute x1: Real;
    }

    // 具体实现
    part def VanDerPol :> OutputPort {
        attribute mu :>> VanDerPolOscillator::mu;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.1;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.1;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 20.0;
        attribute step_size: Real = 0.1;
        attribute seed: Integer = 0;
    }
}
