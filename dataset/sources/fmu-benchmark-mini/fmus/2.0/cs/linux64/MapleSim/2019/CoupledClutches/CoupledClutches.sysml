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
        attribute minsamplestep: Real;
        attribute binfilename: String;

        // 连接输入输出端口
        connect InputPort.inputs to CoupledClutchesModel.inputs;
        connect CoupledClutchesModel.outputs1 to OutputPort.outputs1;
        connect CoupledClutchesModel.outputs2 to OutputPort.outputs2;
        connect CoupledClutchesModel.outputs3 to OutputPort.outputs3;
        connect CoupledClutchesModel.outputs4 to OutputPort.outputs4;
    }
}
