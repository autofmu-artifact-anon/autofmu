package sb_ActiveRC {
    // 输入端口定义
    port def InputPort {
        in attribute Signal_in: Real;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute V_in: Real;
        out attribute V_out: Real;
    }

    // 参数定义
    part def FMU {
        attribute Ipar_4_1: Integer;
        attribute Ipar_3_1: Integer;
        attribute Ipar_2_1: Integer;
        attribute Ipar_1_1: Integer;
        attribute FMU_sup_1_OT_1_2: Integer;
        attribute FMU_sup_1_OT_1_1: Integer;
        attribute FMU_sup_1_nout: Integer;
        attribute FMU_sup_1_fmuresources: String;
        attribute FMU_sup_1_fmutempdir: String;
        attribute FMU_sup_1_separator: String;
        attribute FMU_sup_1_fixedComStepsize: Real;
        attribute FMU_sup_1_simparams_1_18: Integer;
        attribute FMU_sup_1_simparams_1_17: Integer;
        attribute FMU_sup_1_simparams_1_16: Integer;
        attribute FMU_sup_1_simparams_1_15: Integer;
        attribute FMU_sup_1_simparams_1_14: Integer;
        attribute FMU_sup_1_simparams_1_13: Integer;
        attribute FMU_sup_1_simparams_1_12: Integer;
        attribute FMU_sup_1_simparams_1_11: Integer;
        attribute FMU_sup_1_simparams_1_10: Integer;
        attribute FMU_sup_1_simparams_1_9: Integer;
        attribute FMU_sup_1_simparams_1_8: Integer;
        attribute FMU_sup_1_simparams_1_7: Integer;
        attribute FMU_sup_1_simparams_1_6: Integer;
        attribute FMU_sup_1_simparams_1_5: Integer;
        attribute FMU_sup_1_simparams_1_4: Integer;
        attribute FMU_sup_1_simparams_1_3: Integer;
        attribute FMU_sup_1_simparams_1_2: Integer;
        attribute FMU_sup_1_simparams_1_1: Integer;
        attribute FMU_sup_1_fmuresfilename: String;
    }
}
