package WaterTank {
    // 属性定义
    attribute def level: Real;
    attribute def valve: Real;
    attribute def maxlevel: Real;
    attribute def minlevel: Real;

    // 端口定义
    port def InputPort {
        in attribute level: Real;
    }

    port def OutputPort {
        out attribute valve: Real;
    }

    // 抽象部件定义
    part def Control {
        attribute level: Real;
        attribute valve: Real;
        attribute maxlevel: Real;
        attribute minlevel: Real;

        port input: InputPort;
        port output: OutputPort;
    }
}
