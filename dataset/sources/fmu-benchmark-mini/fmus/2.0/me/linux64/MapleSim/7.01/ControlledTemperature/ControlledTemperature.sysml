package ControlledTemperature {
    // 输入输出端口定义
    port def OutputPort {
        out attribute reference: Real;
        out attribute tempValue: Real;
    }

    // 参数定义
    part def ControlledTemperatureModel {
        attribute TAmb: Real;
        attribute TDif: Real;

        // 输出端口
        part outputPort: OutputPort;

        // 连接输出
        connect outputPort.reference to outputs[1];
        connect outputPort.tempValue to outputs[2];
    }

    // 特征定义
    part def Outputs {
        attribute output1: Real;
        attribute output2: Real;
    }

    // 场景定义
    action def StepScenario {
        // 具体步骤
    }

    action def RampScenario {
        // 具体步骤
    }

    action def SineScenario {
        // 具体步骤
    }
}
