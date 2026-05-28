package FmuExportCrossCompile {
    // 输入输出端口定义
    port def OutputPort {
        out attribute der_h: Real;
        out attribute der_v: Real;
    }

    // 参数定义
    part def FmuModel {
        attribute e: Real;
        attribute g: Real;

        // 输出端口
        part output: OutputPort;

        // 特征定义
        feature def der_h;
        feature def der_v;
    }
}
