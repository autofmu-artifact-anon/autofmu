package StairModel {
    // 输出定义
    attribute def counter: Integer;

    // 端口定义
    port def OutputPort {
        out attribute counter: Integer;
    }

    // 主要部件定义
    part def Stair {
        part output: OutputPort;
        attribute counter: counter;

        // 计时器逻辑
        action def CountSeconds {
            out attribute counter: Integer;
        }
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.05;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.05;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 10.0;
        attribute step_size: Real = 0.05;
        attribute seed: Integer = 0;
    }
}
