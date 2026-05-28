package CoupledClutches {
    // 输入端口定义
    port def InputPort {
        in attribute inputs: Real;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute outputs[1]: Real;
        out attribute outputs[2]: Real;
        out attribute outputs[3]: Real;
        out attribute outputs[4]: Real;
    }

    // 参数定义
    part def CoupledClutchesModel {
        attribute T2: Real;
        attribute freqHz: Real;
        attribute minsamplestep: Real;
        attribute binfilename: String;

        // 端口连接
        port input: InputPort;
        port output: OutputPort;
    }
}
