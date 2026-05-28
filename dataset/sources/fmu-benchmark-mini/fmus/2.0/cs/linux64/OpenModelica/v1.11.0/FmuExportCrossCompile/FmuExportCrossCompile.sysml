package FmuExportCrossCompile {
    // 输入输出端口定义
    port def OutputPort {
        out attribute der_h: Real;
        out attribute der_v: Real;
    }

    // 参数定义
    part def FmuModel {
        attribute e: Real;
        attribute g: Real;

        // 端口连接
        part output: OutputPort;
    }

    // 特征定义
    feature def DerivativeFeatures {
        feature der_h;
        feature der_v;
    }

    // 场景定义
    scenario def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.45;
        attribute step_size: Real = 0.00225;
        attribute seed: Integer = 0;
    }

    scenario def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.45;
        attribute step_size: Real = 0.00225;
        attribute seed: Integer = 0;
    }

    scenario def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 0.45;
        attribute step_size: Real = 0.00225;
        attribute seed: Integer = 0;
    }
}
