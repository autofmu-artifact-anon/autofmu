package FeedthroughModel {
    // 输入端口定义
    port def InputPort {
        in attribute real_continuous_in: Real;
        in attribute real_discrete_in: Real;
        in attribute int_in: Integer;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute real_continuous_out: Real;
        out attribute real_discrete_out: Real;
        out attribute int_out: Integer;
        out attribute bool_out: Boolean;
    }

    // 参数定义
    part def Feedthrough {
        attribute real_fixed_param: Real;
        attribute real_tunable_param: Real;
        attribute string_param: String;
    }
}
