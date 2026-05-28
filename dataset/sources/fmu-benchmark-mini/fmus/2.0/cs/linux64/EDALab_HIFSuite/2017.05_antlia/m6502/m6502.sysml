package FMUModel {
    // 输入端口定义
    port def InputPort {
        in attribute datai: Integer;
        in attribute irq_n: Boolean;
        in attribute nmi_n: Boolean;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute addr: Integer;
        out attribute datao: Integer;
        out attribute vpab: Boolean;
        out attribute sync: Boolean;
        out attribute we_n: Boolean;
    }

    // FMU模型定义
    part def m6502 {
        part input: InputPort;
        part output: OutputPort;
    }
}
