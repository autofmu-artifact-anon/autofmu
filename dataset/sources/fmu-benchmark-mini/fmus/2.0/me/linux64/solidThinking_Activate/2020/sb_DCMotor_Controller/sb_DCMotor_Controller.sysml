package sb_DCMotor_Controller {
    part def DCMotor_Controller {
        // 输入端口定义
        port def InputPort {
            in attribute Reference_angle: Real;
        }

        // 输出端口定义
        port def OutputPort {
            out attribute DCMotor_angle: Real;
            out attribute DCMotot_speed: Real;
            out attribute controller_output: Real;
        }

        // 参数定义
        attribute Ipar_12_1: Integer;
        attribute Ipar_11_1: Integer;
        attribute Ipar_10_1: Integer;
        attribute Ipar_9_1: Integer;
        attribute Ipar_8_1: Integer;
        attribute Ipar_7_1: Integer;
        attribute Ipar_6_1: Integer;
        attribute Ipar_5_1: Integer;
        attribute Ipar_4_1: Integer;
        attribute Ipar_3_1: Integer;
        attribute Ipar_2_1: Integer;
        attribute Ipar_1_1: Integer;
        attribute VssVirtualSampleClock1_offset: Real;
        attribute VssVirtualSampleClock1_period: Real;
        attribute DiscrTransFunc_opar4: Real;
        attribute DiscrTransFunc_opar3_1_2: Real;
        attribute DiscrTransFunc_opar3_1_1: Real;
        attribute DiscrTransFunc_opar2_2_1: Real;
        attribute DiscrTransFunc_opar2_1_1: Real;
        attribute DiscrTransFunc_opar1_2_2: Real;
        attribute DiscrTransFunc_opar1_1_2: Real;
        attribute DiscrTransFunc_opar1_2_1: Real;
        attribute DiscrTransFunc_opar1_1_1: Real;
        attribute Gain_6_opar3: Integer;
        attribute Gain_6_opar2: Integer;
        attribute Gain_6_opar1: Real;
        attribute Gain_6_1_opar3: Integer;
        attribute Gain_6_1_opar2: Integer;
        attribute Gain_6_1_opar1: Real;
        attribute Gain_2_opar3: Integer;

        // 特征定义
        feature DCMotor_angle;
        feature DCMotot_speed;
        feature controller_output;

        // 场景定义
        scenario step_scenario {
            kind: step;
            start_time: 0.0;
            stop_time: 10.0;
            step_size: 0.001;
            seed: 0;
        }

        scenario ramp_scenario {
            kind: ramp;
            start_time: 0.0;
            stop_time: 10.0;
            step_size: 0.001;
            seed: 0;
        }

        scenario sine_scenario {
            kind: sine;
            start_time: 0.0;
            stop_time: 10.0;
            step_size: 0.001;
            seed: 0;
        }
    }
}
