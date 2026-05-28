package sb_Boocwen {
    // 输入输出端口定义
    port def OutputPort {
        out attribute SCSREAL_COP: Real;
    }

    // 参数定义
    part def FMU {
        attribute Ipar_1: Integer;
        attribute Ipar_2: Integer;
        attribute Ipar_3: Integer;
        attribute Ipar_4: Integer;
        attribute Ipar_5: Integer;
        attribute Ipar_6: Integer;
        attribute Ipar_7: Integer;
        attribute Ipar_8: Integer;
        attribute Ipar_9: Integer;
        attribute Ipar_10: Integer;
        attribute Ipar_11: Integer;
        attribute Ipar_12: Integer;
        attribute Ipar_13: Integer;
        attribute Ipar_14: Integer;
        attribute Ipar_15: Integer;
        attribute Ipar_16: Integer;
        attribute Ipar_17: Integer;
        attribute Ipar_18: Integer;
        attribute Ipar_19: Integer;
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
}
