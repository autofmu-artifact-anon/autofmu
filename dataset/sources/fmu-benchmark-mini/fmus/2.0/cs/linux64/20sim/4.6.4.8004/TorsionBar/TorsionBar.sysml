package TorsionBarModel {
    // 输入输出端口定义
    port def OutputPort {
        out attribute LoadDiskRev: Real;
        out attribute MotorDiskRev: Real;
    }

    // 主部件定义
    part def TorsionBar {
        // 参数定义
        attribute Amplifier_VCC: Real;
        attribute Amplifier_DA_minimum: Real;
        attribute Amplifier_DA_maximum: Real;
        attribute Amplifier_DA_bits: Real;
        attribute Belt_i: Real; // gearbox ratio
        attribute BeltFriction_d: Real; // rotational damping
        attribute BeltFriction_Tc: Real; // coulomb (static) friction torque
        attribute BeltFriction_slope: Real; // steepness of coulomb friction curve
        attribute Controller_EncToRevLoadDisk_counts: Real;
        attribute Controller_EncToRevMotor_counts: Real;
        attribute Controller_PID_kp: Real; // Proportional gain
        attribute Controller_PID_tauD: Real; // Derivative time constant
        attribute Controller_PID_beta: Real; // Tameness constant
        attribute Controller_PID_tauI: Real; // Integral time constant
        attribute Controller_RevMotorToRevMotorDisk_i_belt: Real;
        attribute Controller_SP_stroke: Real;
        attribute Controller_SP_start_time: Real;
        attribute Controller_SP_stop_time: Real;
        attribute Controller_SP_return_time: Real;
        attribute Controller_SP_end_time: Real;
        attribute Controller_SP_period: Real;
        attribute EncoderLoad_counts: Real; // pulses per revolution
        attribute EncoderMotor_counts: Real; // pulses per revolution
        attribute FlexibleShaft_Gb: Real; // shear modulus of the bar (steel)
        attribute FlexibleShaft_lb: Real; // bar length
        attribute FlexibleShaft_db: Real; // bar diameter
        attribute FlexibleShaft_d: Real; // viscous damping of the bar
        attribute JLoadDisk_J: Real;
        attribute Jmotor_J: Real;
        attribute JMotorDisk_J: Real;

        // 端口连接
        part output: OutputPort;
    }
}
