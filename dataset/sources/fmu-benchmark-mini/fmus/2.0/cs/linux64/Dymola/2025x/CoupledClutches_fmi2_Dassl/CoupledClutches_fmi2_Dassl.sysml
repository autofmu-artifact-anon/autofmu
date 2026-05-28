package CoupledClutches_fmi2_Dassl {
    // 输入端口定义
    port def InputPort {
        in attribute step2: Real;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute J1_w: Real;
        out attribute J2_w: Real;
        out attribute J3_w: Real;
        out attribute J4_w: Real;
    }

    // 主要部件定义
    part def CoupledClutches {
        // 属性定义
        attribute f: Real;
        attribute T2: Real;
        attribute T3: Real;
        attribute J1_J: Real;
        attribute clutch1_mu_pos_1_1: Real;
        attribute clutch1_mu_pos_1_2: Real;
        attribute clutch1_peak: Real;
        attribute clutch1_cgeo: Real;
        attribute clutch1_fn_max: Real;
        attribute clutch1_w_small: Real;
        attribute step1_height: Real;
        attribute step1_offset: Real;
        attribute J2_J: Real;
        attribute clutch2_mu_pos_1_1: Real;
        attribute clutch2_mu_pos_1_2: Real;
        attribute clutch2_peak: Real;
        attribute clutch2_cgeo: Real;
        attribute clutch2_fn_max: Real;
        attribute clutch2_w_small: Real;
        attribute J3_J: Real;
        attribute clutch3_mu_pos_1_1: Real;
        attribute clutch3_mu_pos_1_2: Real;
        attribute clutch3_peak: Real;
        attribute clutch3_cgeo: Real;
        attribute clutch3_fn_max: Real;
        attribute clutch3_w_small: Real;
        attribute J4_J: Real;
        attribute sin2_amplitude: Real;
        attribute sin2_phase: Real;
        attribute sin2_offset: Real;

        // 连接输入输出端口
        connect InputPort.step2 to CoupledClutches.step2;
        connect CoupledClutches.J1_w to OutputPort.J1_w;
        connect CoupledClutches.J2_w to OutputPort.J2_w;
        connect CoupledClutches.J3_w to OutputPort.J3_w;
        connect CoupledClutches.J4_w to OutputPort.J4_w;
    }
}
