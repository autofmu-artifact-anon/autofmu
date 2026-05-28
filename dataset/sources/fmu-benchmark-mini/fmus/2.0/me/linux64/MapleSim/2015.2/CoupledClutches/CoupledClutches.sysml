package CoupledClutches {
    // 输入定义
    port def InputPort {
        in attribute inputs: Real;
    }

    // 输出定义
    port def OutputPort {
        out attribute outputs1: Real;
        out attribute outputs2: Real;
        out attribute outputs3: Real;
        out attribute outputs4: Real;
    }

    // 参数定义
    part def CoupledClutchesModel {
        attribute CoupledClutches1_T2: Real;
        attribute CoupledClutches1_freqHz: Real;

        port input: InputPort;
        port output: OutputPort;
    }
}
