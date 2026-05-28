package RectifierModel {
    // 输入输出端口定义
    port def OutputPort {
        out attribute v: Real;
    }

    // 参数定义
    part def Rectifier {
        attribute minsamplestep: Real;
        attribute binfilename: String;

        // 输出端口
        port output: OutputPort;
    }
}
