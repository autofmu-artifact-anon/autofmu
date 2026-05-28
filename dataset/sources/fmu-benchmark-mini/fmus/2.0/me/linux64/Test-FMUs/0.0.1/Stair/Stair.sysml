package StairModel {
    // 输出定义
    attribute def counter: Integer;

    // 端口定义
    port def OutputPort {
        out attribute counter: Integer;
    }

    // 具体实现
    part def Stair {
        attribute counter: counter;

        // 端口连接
        part outputPort: OutputPort;
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
