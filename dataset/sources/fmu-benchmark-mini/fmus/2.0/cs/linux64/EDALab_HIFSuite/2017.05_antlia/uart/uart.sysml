package UARTModel {
    // 输入端口定义
    port def InputPort {
        in attribute paddr: Integer;
        in attribute pwdata: Integer;
        in attribute presetn: Boolean;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute prdata: Integer;
        out attribute stx: Boolean;
        out attribute dtrn: Boolean;
        out attribute rtsn: Boolean;
        out attribute out1n: Boolean;
    }

    // 主部件定义
    part def UART {
        port input: InputPort;
        port output: OutputPort;

        // 特征定义
        attribute prdata: Integer;
        attribute stx: Boolean;
        attribute dtrn: Boolean;
        attribute rtsn: Boolean;
        attribute out1n: Boolean;
    }
}
