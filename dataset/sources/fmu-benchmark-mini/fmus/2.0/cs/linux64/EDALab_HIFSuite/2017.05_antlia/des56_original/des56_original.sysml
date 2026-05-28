package des56_original {
    // 输入端口定义
    port def InputPort {
        in attribute indata_0031: Integer;
        in attribute indata_3263: Integer;
        in attribute inkey_0031: Integer;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute outdata_0031: Integer;
        out attribute outdata_3263: Integer;
        out attribute c17_out_0031: Integer;
        out attribute c17_out_3263: Integer;
        out attribute b1_out: Integer;
    }

    // 主部件定义
    part def FMU {
        part input: InputPort;
        part output: OutputPort;
    }

    // 场景定义
    action def StepScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 5.0;
        attribute step_size: Real = 0.025;
        attribute seed: Integer = 0;
    }

    action def RampScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 5.0;
        attribute step_size: Real = 0.025;
        attribute seed: Integer = 0;
    }

    action def SineScenario {
        attribute start_time: Real = 0.0;
        attribute stop_time: Real = 5.0;
        attribute step_size: Real = 0.025;
        attribute seed: Integer = 0;
    }
}
