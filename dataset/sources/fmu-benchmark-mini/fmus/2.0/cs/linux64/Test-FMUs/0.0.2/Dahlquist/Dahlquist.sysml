package DahlquistModel {
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
    part def Dahlquist {
        part output :>> OutputPort;
        part parameter :>> ParameterPort;

        // 参数定义
        attribute k: Real;
    }
}
