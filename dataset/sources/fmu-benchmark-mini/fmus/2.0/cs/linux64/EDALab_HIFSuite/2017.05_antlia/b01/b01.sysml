package FMUModel {
    // 输入端口定义
    port def InputPort {
        in attribute line1: Boolean;
        in attribute line2: Boolean;
        in attribute reset: Boolean;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute out_stato: Integer;
        out attribute outp: Boolean;
        out attribute overflw: Boolean;
    }

    // FMU主部件定义
    part def FMU {
        part input: InputPort;
        part output: OutputPort;

        // 特征定义
        attribute out_stato: Integer;
        attribute outp: Boolean;
        attribute overflw: Boolean;
    }
}
