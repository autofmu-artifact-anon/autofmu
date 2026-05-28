package RectifierModel {
    // 输入输出端口定义
    port def OutputPort {
        out attribute v: Real;
    }

    // 参数定义
    part def Rectifier {
        attribute minsamplestep: Real;
        attribute binfilename: String;

        // 输出端口
        part output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.1;
        attribute step_size: Real = 0.001;
        attribute seed: Integer = 0;
    }
}
