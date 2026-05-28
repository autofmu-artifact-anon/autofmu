package SB_Arenstorf {
    // 输入输出端口定义
    port def OutputPort {
        out attribute x_coor: Real;
        out attribute y_coor: Real;
    }

    // 参数定义
    part def Parameters {
        attribute Ipar_31: Integer;
        attribute Ipar_30: Integer;
        attribute Ipar_29: Integer;
        attribute Ipar_28: Integer;
        attribute Ipar_27: Integer;
        attribute Ipar_26: Integer;
        attribute Ipar_25: Integer;
        attribute Ipar_24: Integer;
        attribute Ipar_23: Integer;
        attribute Ipar_22: Integer;
        attribute Ipar_21: Integer;
        attribute Ipar_20: Integer;
        attribute Ipar_19: Integer;
        attribute Ipar_18: Integer;
        attribute Ipar_17: Integer;
        attribute Ipar_16: Integer;
        attribute Ipar_15: Integer;
        attribute Ipar_14: Integer;
        attribute Ipar_13: Integer;
        attribute Ipar_12: Integer;
        attribute Ipar_11: Integer;
        attribute Ipar_10: Integer;
        attribute Ipar_9: Integer;
        attribute Ipar_8: Integer;
        attribute Ipar_7: Integer;
        attribute Ipar_6: Integer;
        attribute Ipar_5: Integer;
        attribute Ipar_4: Integer;
        attribute Ipar_3: Integer;
        attribute Ipar_2: Integer;
    }

    // 主要部件定义
    part def ArenstorfModel {
        part parameters: Parameters;
        port output: OutputPort;
    }
}
