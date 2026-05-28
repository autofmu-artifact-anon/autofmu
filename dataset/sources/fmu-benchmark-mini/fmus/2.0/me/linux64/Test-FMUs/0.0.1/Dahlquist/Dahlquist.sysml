package Dahlquist {
    // 属性定义
    attribute def x :> Real;

    // 端口定义
    port def OutputPort {
        out attribute x: Real;
    }

    port def ParameterPort {
        in attribute k: Real;
    }

    // 具体实现
    part def FMU {
        part output :>> OutputPort;
        part parameter :>> ParameterPort;

        // 固定参数
        attribute k: Real;
    }
}
