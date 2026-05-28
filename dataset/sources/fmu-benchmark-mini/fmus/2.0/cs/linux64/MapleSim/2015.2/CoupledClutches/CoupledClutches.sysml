package CoupledClutches {
    // 输入定义
    port def InputPort {
        in attribute inputs: Real;
    }

    // 输出定义
    port def OutputPort {
        out attribute outputs[1]: Real;
        out attribute outputs[2]: Real;
        out attribute outputs[3]: Real;
        out attribute outputs[4]: Real;
    }

    // 参数定义
    part def CoupledClutchesModel {
        attribute CoupledClutches1_T2: Real;
        attribute CoupledClutches1_freqHz: Real;

        // 端口连接
        port input: InputPort;
        port output: OutputPort;
    }
}
