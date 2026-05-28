package BouncingBall {
    // 输入输出端口定义
    port def OutputPort {
        out attribute h: Real;
        out attribute v: Real;
    }

    // 参数定义
    attribute def g: Real; // Gravity acting on the ball
    attribute def e: Real; // Coefficient of restitution

    // 主要部件定义
    part def BouncingBallModel {
        part output: OutputPort;
        attribute g: g;
        attribute e: e;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 3.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 3.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 3.0;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }
}
