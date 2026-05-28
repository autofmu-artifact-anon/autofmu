package sb_Boocwen {
    // 输入输出端口定义
    port def OutputPort {
        out attribute SCSREAL_COP: Real;
    }

    // 参数定义
    part def FMU {
        attribute Ipar1: Integer;
        attribute Ipar2: Integer;
        attribute Ipar3: Integer;
        attribute Ipar4: Integer;
        attribute Ipar5: Integer;
        attribute Ipar6: Integer;
        attribute Ipar7: Integer;
        attribute Ipar8: Integer;
        attribute Ipar9: Integer;
        attribute Ipar10: Integer;
        attribute Ipar11: Integer;
        attribute Ipar12: Integer;
        attribute Ipar13: Integer;
        attribute Ipar14: Integer;
        attribute Ipar15: Integer;
        attribute Ipar16: Integer;
        attribute Ipar17: Integer;
        attribute Ipar18: Integer;
        attribute Ipar19: Integer;
        attribute SineWaveGenerator_opar1: Real;
        attribute SineWaveGenerator_opar2: Real;
        attribute SineWaveGenerator_opar3: Real;
        attribute SineWaveGenerator_opar4: Real;
        attribute Gain_opar1: Real;
        attribute Gain_opar2: Integer;
        attribute Gain_opar3: Integer;
        attribute Gain_1_opar1: Real;
        attribute Gain_1_opar2: Integer;
        attribute Gain_1_opar3: Integer;
        attribute ContTransFunc_opar4: Real;
    }

    // 连接定义
    connect FMU.OutputPort to OutputPort;
}
