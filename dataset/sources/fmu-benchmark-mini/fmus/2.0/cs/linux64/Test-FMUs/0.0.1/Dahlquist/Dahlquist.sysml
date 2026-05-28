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
    part def DahlquistModel {
        part output :>> OutputPort;
        part parameter :>> ParameterPort;

        // 属性赋值
        attribute k :> Real;
    }
}
