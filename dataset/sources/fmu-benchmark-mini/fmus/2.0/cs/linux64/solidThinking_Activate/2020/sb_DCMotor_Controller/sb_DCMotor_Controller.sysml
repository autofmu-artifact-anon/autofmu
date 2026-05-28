package sb_DCMotor_Controller {
    // 输入定义
    port def InputPort {
        in attribute Reference_angle: Real;
    }

    // 输出定义
    port def OutputPort {
        out attribute DCMotor_angle: Real;
        out attribute DCMotot_speed: Real;
        out attribute controller_output: Real;
    }

    // 参数定义
    part def Parameters {
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
        attribute VssVirtualSampleClock1_offset: Real;
        attribute VssVirtualSampleClock1_period: Real;
        attribute DiscrTransFunc_opar1_1_1: Real;
        attribute DiscrTransFunc_opar1_1_2: Real;
        attribute DiscrTransFunc_opar1_2_1: Real;
        attribute DiscrTransFunc_opar1_2_2: Real;
        attribute DiscrTransFunc_opar2_1_1: Real;
        attribute DiscrTransFunc_opar2_2_1: Real;
        attribute DiscrTransFunc_opar3_1_1: Real;
        attribute DiscrTransFunc_opar3_1_2: Real;
        attribute DiscrTransFunc_opar4: Real;
        attribute Gain_2_opar3: Integer;
        attribute Gain_6_opar1: Real;
        attribute Gain_6_opar2: Integer;
        attribute Gain_6_opar3: Integer;
        attribute Gain_6_1_opar1: Real;
        attribute Gain_6_1_opar2: Integer;
        attribute Gain_6_1_opar3: Integer;
    }

    // 控制器定义
    part def DCMotor_Controller {
        part input: InputPort;
        part output: OutputPort;
        part parameters: Parameters;
    }
}
