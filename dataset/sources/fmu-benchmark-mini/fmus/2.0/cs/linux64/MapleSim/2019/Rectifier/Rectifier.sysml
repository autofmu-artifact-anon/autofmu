package RectifierModel {
    // 输入输出端口定义
    port def OutputPort {
        out attribute v: Real;
    }

    // 参数定义
    part def Rectifier {
        attribute minsamplestep: Real;
        attribute binfilename: String;
        part output: OutputPort;
    }

    // 特征定义
    feature def Outputs {
        part output: OutputPort;
    }

    // 场景定义
    scenario def StepScenario {
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }

    scenario def RampScenario {
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }

    scenario def SineScenario {
        start_time: 0.0;
        stop_time: 0.1;
        step_size: 1e-07;
        seed: 0;
    }
}
