package FMICrossCheck {
    part def CoupledClutches {
        // 输入端口定义
        port def InputPort {
            in attribute f_normalized: Real;
        }

        // 输出端口定义
        port def OutputPort {
            out attribute J1_w: Real;
            out attribute J2_w: Real;
            out attribute J3_w: Real;
            out attribute J4_w: Real;
        }

        // 参数定义
        attribute def freqHz: Real;
        attribute def T2: Real;
        attribute def T3: Real;
        attribute def J1_J: Real;
        attribute def J1_stateSelect: Enumeration;
        attribute def clutch1_phi_nominal: Real;
        attribute def clutch1_stateSelect: Enumeration;
        attribute def clutch1_w_small: Real;
        attribute def clutch1_mue_pos_1_1: Real;
        attribute def clutch1_mue_pos_1_2: Real;
        attribute def clutch1_peak: Real;
        attribute def clutch1_cgeo: Real;
        attribute def clutch1_fn_max: Real;
        attribute def sin1_amplitude: Real;
        attribute def sin1_freqHz: Real;
        attribute def sin1_phase: Real;
        attribute def sin1_offset: Real;
        attribute def sin1_startTime: Real;
        attribute def step1_offset: Real;
        attribute def step1_height: Real;
        attribute def J2_J: Real;
        attribute def J2_stateSelect: Enumeration;
        attribute def clutch2_phi_nominal: Real;
        attribute def clutch2_stateSelect: Enumeration;
        attribute def clutch2_w_small: Real;
        attribute def clutch2_mue_pos_1_1: Real;
        attribute def clutch2_mue_pos_1_2: Real;
        attribute def clutch2_peak: Real;
        attribute def clutch2_cgeo: Real;
        attribute def clutch2_fn_max: Real;
    }
}
