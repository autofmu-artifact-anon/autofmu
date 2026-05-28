package CartPoleControlSystem {

    import ScalarValues::*;

    doc /* 
     * Cart-Pole swing-up and balance control subsystem.
     *
     * Angle convention:
     *   theta = 0      -> hanging down
     *   theta = pi     -> upright
     *
     * Main structure:
     *   - HybridController (swing-up + balance + integral action)
     *   - AngleEstimator (IMU fusion with bias estimation and filtering)
     *   - CartPolePlant (nonlinear dynamics with actuator saturation and friction)
     *
     * Notes:
     *   - This model is intentionally engineering-oriented.
     *   - Some mathematical/library functions may need adaptation to the exact
     *     function names supported by a specific SysML v2 tool or library.
     */

    //==================================================
    // Basic data types
    //==================================================

    attribute def Position_m        :> Real;
    attribute def Velocity_mps      :> Real;
    attribute def Angle_rad         :> Real;
    attribute def AngularRate_rps   :> Real;
    attribute def Force_N           :> Real;
    attribute def Mass_kg           :> Real;
    attribute def Length_m          :> Real;
    attribute def Damping_NsPerM    :> Real;
    attribute def Damping_NmPerRad  :> Real;
    attribute def Gain              :> Real;
    attribute def Time_s            :> Real;
    attribute def ModeIndex         :> Integer;
    attribute def NoiseStdDev       :> Real;
    attribute def BiasDriftRate     :> Real;
    attribute def Dimensionless     :> Real;

    enum def ControllerMode {
        enum disabled;
        enum swingUp;
        enum balance;
    }

    //==================================================
    // Signal items for directed ports
    //==================================================

    item def PositionSignal {
        attribute value : Position_m;
    }

    item def VelocitySignal {
        attribute value : Velocity_mps;
    }

    item def AngleSignal {
        attribute value : Angle_rad;
    }

    item def AngularRateSignal {
        attribute value : AngularRate_rps;
    }

    item def ForceSignal {
        attribute value : Force_N;
    }

    item def ModeSignal {
        attribute value : Integer;
    }

    item def BooleanSignal {
        attribute value : Boolean;
    }

    //==================================================
    // Port definitions
    //==================================================

    port def PositionOutPort {
        out item x_m : PositionSignal;
    }

    port def VelocityOutPort {
        out item x_dot_mps : VelocitySignal;
    }

    port def AngleOutPort {
        out item theta_rad : AngleSignal;
    }

    port def AngularRateOutPort {
        out item theta_dot_rps : AngularRateSignal;
    }

    port def ForceInPort {
        in item force_cmd_N : ForceSignal;
    }

    port def ForceOutPort {
        out item force_cmd_N : ForceSignal;
    }

    port def DisturbanceForceInPort {
        in item disturbance_force_N : ForceSignal;
    }

    port def PositionReferenceInPort {
        in item x_ref_m : PositionSignal;
    }

    port def EnableInPort {
        in item enable : BooleanSignal;
    }

    port def ResetInPort {
        in item reset : BooleanSignal;
    }

    port def ThetaMeasuredOutPort {
        out item theta_meas_rad : AngleSignal;
    }

    port def ThetaDotMeasuredOutPort {
        out item theta_dot_meas_rps : AngularRateSignal;
    }

    port def ThetaEstimatedOutPort {
        out item theta_hat_rad : AngleSignal;
    }

    port def ThetaDotEstimatedOutPort {
        out item theta_dot_hat_rps : AngularRateSignal;
    }

    port def BiasEstimatedOutPort {
        out item bias_hat_rps : AngularRateSignal;
    }

    port def ModeOutPort {
        out item mode : ModeSignal;
    }

    //==================================================
    // Interface definitions
    //==================================================

    interface def ForceCommandInterface {
        end controllerPort : ForceOutPort;
        end plantPort : ForceInPort;

        flow controllerPort.force_cmd_N to plantPort.force_cmd_N;
    }

    interface def PositionFeedbackInterface {
        end plantPort : PositionOutPort;
        end controllerPort : ~PositionOutPort;

        flow plantPort.x_m to controllerPort.x_m;
    }

    interface def VelocityFeedbackInterface {
        end plantPort : VelocityOutPort;
        end controllerPort : ~VelocityOutPort;

        flow plantPort.x_dot_mps to controllerPort.x_dot_mps;
    }

    interface def AngleMeasurementInterface {
        end plantPort : ThetaMeasuredOutPort;
        end estimatorPort : ~ThetaMeasuredOutPort;

        flow plantPort.theta_meas_rad to estimatorPort.theta_meas_rad;
    }

    interface def AngularRateMeasurementInterface {
        end plantPort : ThetaDotMeasuredOutPort;
        end estimatorPort : ~ThetaDotMeasuredOutPort;

        flow plantPort.theta_dot_meas_rps to estimatorPort.theta_dot_meas_rps;
    }

    interface def AngleEstimateInterface {
        end estimatorPort : ThetaEstimatedOutPort;
        end controllerPort : ~ThetaEstimatedOutPort;

        flow estimatorPort.theta_hat_rad to controllerPort.theta_hat_rad;
    }

    interface def AngularRateEstimateInterface {
        end estimatorPort : ThetaDotEstimatedOutPort;
        end controllerPort : ~ThetaDotEstimatedOutPort;

        flow estimatorPort.theta_dot_hat_rps to controllerPort.theta_dot_hat_rps;
    }

    //==================================================
    // Calculation definitions
    //==================================================

    calc def Clamp {
        in u : Real;
        in lower : Real;
        in upper : Real;
        return : Real =
            if u < lower then lower
            else if u > upper then upper
            else u
    }

    calc def SaturatedForce {
        in u : Force_N;
        in f_max : Force_N;
        return : Force_N = Clamp(u, -f_max, f_max)
    }

    calc def SoftSignFriction {
        in v : Real;
        in friction_level : Real;
        in v0 : Real;
        return : Real = friction_level * tanh(v / v0)
    }

    calc def WrapAngleToPi {
        in angle_in : Angle_rad;
        return : Angle_rad =
            angle_in - 2.0 * 3.141592653589793 * floor((angle_in + 3.141592653589793) / (2.0 * 3.141592653589793))
    }

    calc def UprightAngleError {
        in theta : Angle_rad;
        return : Angle_rad = WrapAngleToPi(theta - 3.141592653589793)
    }

    calc def SwingUpEnergy {
        in m_p : Mass_kg;
        in l : Length_m;
        in g : Real;
        in theta : Angle_rad;
        in theta_dot : AngularRate_rps;
        return : Real =
            0.5 * m_p * l * l * theta_dot * theta_dot + m_p * g * l * (1.0 - cos(theta))
    }

    calc def UprightEnergy {
        in m_p : Mass_kg;
        in l : Length_m;
        in g : Real;
        return : Real = 2.0 * m_p * g * l
    }

    calc def SwingUpForceLaw {
        in m_p : Mass_kg;
        in l : Length_m;
        in g : Real;
        in theta : Angle_rad;
        in theta_dot : AngularRate_rps;
        in k_e : Gain;
        in f_max : Force_N;
        return : Force_N =
            Clamp(
                k_e * (SwingUpEnergy(m_p, l, g, theta, theta_dot) - UprightEnergy(m_p, l, g))
                    * theta_dot * cos(theta),
                -f_max,
                f_max
            )
    }

    calc def BalanceForceLaw {
        in x : Position_m;
        in x_dot : Velocity_mps;
        in theta_hat : Angle_rad;
        in theta_dot_hat : AngularRate_rps;
        in x_ref : Position_m;
        in i_x : Real;
        in k_x : Gain;
        in k_xd : Gain;
        in k_th : Gain;
        in k_thd : Gain;
        in k_i : Gain;
        in f_max : Force_N;
        return : Force_N =
            Clamp(
                -(k_x * (x - x_ref)
                + k_xd * x_dot
                + k_th * UprightAngleError(theta_hat)
                + k_thd * theta_dot_hat
                + k_i * i_x),
                -f_max,
                f_max
            )
    }

    calc def EstimatorThetaPrediction {
        in theta_hat : Angle_rad;
        in theta_dot_meas : AngularRate_rps;
        in bias_hat : AngularRate_rps;
        in dt : Time_s;
        return : Angle_rad = theta_hat + dt * (theta_dot_meas - bias_hat)
    }

    calc def EstimatorThetaCorrection {
        in theta_pred : Angle_rad;
        in theta_meas : Angle_rad;
        in l_theta : Gain;
        return : Angle_rad =
            theta_pred + l_theta * WrapAngleToPi(theta_meas - theta_pred)
    }

    calc def EstimatorBiasCorrection {
        in bias_hat : AngularRate_rps;
        in theta_meas : Angle_rad;
        in theta_pred : Angle_rad;
        in l_bias : Gain;
        in dt : Time_s;
        return : AngularRate_rps =
            bias_hat - l_bias * WrapAngleToPi(theta_meas - theta_pred) * dt
    }

    calc def EstimatorRateCorrection {
        in theta_dot_meas : AngularRate_rps;
        in bias_hat : AngularRate_rps;
        in l_rate : Gain;
        in theta_meas : Angle_rad;
        in theta_pred : Angle_rad;
        return : AngularRate_rps =
            (theta_dot_meas - bias_hat) + l_rate * WrapAngleToPi(theta_meas - theta_pred)
    }

    //==================================================
    // Constraint definitions
    //==================================================

    constraint def ForceLimitConstraint {
        in force_cmd_N : Force_N;
        in f_max : Force_N;

        abs(force_cmd_N) <= f_max
    }

    constraint def CartSoftPositionLimitConstraint {
        in x_m : Position_m;
        in x_limit : Position_m;

        abs(x_m) <= x_limit
    }

    constraint def AngleConventionConstraint {
        in theta_down : Angle_rad;
        in theta_upright : Angle_rad;

        (theta_down == 0.0) and (theta_upright == 3.141592653589793)
    }

    //==================================================
    // Behavioral definitions
    //==================================================

    action def HybridControlComputation {
        in x_m : Position_m;
        in x_dot_mps : Velocity_mps;
        in theta_hat_rad : Angle_rad;
        in theta_dot_hat_rps : AngularRate_rps;
        in x_ref_m : Position_m;
        in enable : Boolean;

        in f_max : Force_N;
        in switch_angle_rad : Angle_rad;

        in k_e : Gain;
        in k_x : Gain;
        in k_xd : Gain;
        in k_th : Gain;
        in k_thd : Gain;
        in k_i : Gain;

        in m_p : Mass_kg;
        in l : Length_m;
        in g : Real;

        inout attribute integral_x_error : Real;

        out force_cmd_N : Force_N;
        out mode : Integer;

        if not enable {
            assign integral_x_error := 0.0;
            out force_cmd_N = 0.0;
            out mode = 0;
        }
        else {
            then if abs(UprightAngleError(theta_hat_rad)) < switch_angle_rad {
                assign integral_x_error := integral_x_error + (x_ref_m - x_m);

                out force_cmd_N =
                    BalanceForceLaw(
                        x_m,
                        x_dot_mps,
                        theta_hat_rad,
                        theta_dot_hat_rps,
                        x_ref_m,
                        integral_x_error,
                        k_x,
                        k_xd,
                        k_th,
                        k_thd,
                        k_i,
                        f_max
                    );

                out mode = 2;
            }
            else {
                assign integral_x_error := 0.0;

                out force_cmd_N =
                    SwingUpForceLaw(
                        m_p,
                        l,
                        g,
                        theta_hat_rad,
                        theta_dot_hat_rps,
                        k_e,
                        f_max
                    );

                out mode = 1;
            }
        }
    }

    action def AngleEstimatorComputation {
        in theta_meas_rad : Angle_rad;
        in theta_dot_meas_rps : AngularRate_rps;
        in reset : Boolean;

        in dt : Time_s;
        in l_theta : Gain;
        in l_bias : Gain;
        in l_rate : Gain;

        inout attribute theta_hat_state : Angle_rad;
        inout attribute bias_hat_state : AngularRate_rps;

        out theta_hat_rad : Angle_rad;
        out theta_dot_hat_rps : AngularRate_rps;
        out bias_hat_rps : AngularRate_rps;

        if reset {
            assign theta_hat_state := theta_meas_rad;
            assign bias_hat_state := 0.0;

            out theta_hat_rad = theta_hat_state;
            out theta_dot_hat_rps = theta_dot_meas_rps;
            out bias_hat_rps = bias_hat_state;
        }
        else {
            private attribute theta_pred : Angle_rad =
                EstimatorThetaPrediction(theta_hat_state, theta_dot_meas_rps, bias_hat_state, dt);

            assign theta_hat_state :=
                EstimatorThetaCorrection(theta_pred, theta_meas_rad, l_theta);

            assign bias_hat_state :=
                EstimatorBiasCorrection(bias_hat_state, theta_meas_rad, theta_pred, l_bias, dt);

            out theta_hat_rad = theta_hat_state;
            out theta_dot_hat_rps =
                EstimatorRateCorrection(theta_dot_meas_rps, bias_hat_state, l_rate, theta_meas_rad, theta_pred);
            out bias_hat_rps = bias_hat_state;
        }
    }

    //==================================================
    // Structural part definitions
    //==================================================

    part def HybridController {

        // External inputs
        port x_in : ~PositionOutPort;
        port x_dot_in : ~VelocityOutPort;
        port theta_hat_in : ~ThetaEstimatedOutPort;
        port theta_dot_hat_in : ~ThetaDotEstimatedOutPort;
        port x_ref_in : PositionReferenceInPort;
        port enable_in : EnableInPort;

        // External outputs
        port force_cmd_out : ForceOutPort;
        port mode_out : ModeOutPort;

        // Parameters
        attribute f_max : Force_N = 20.0;
        attribute switch_angle_rad : Angle_rad = 0.35;

        attribute k_e : Gain = 5.0;

        attribute k_x : Gain = 20.0;
        attribute k_xd : Gain = 8.0;
        attribute k_th : Gain = 80.0;
        attribute k_thd : Gain = 12.0;
        attribute k_i : Gain = 3.0;

        attribute m_p : Mass_kg = 0.2;
        attribute l : Length_m = 0.3;
        attribute g : Real = 9.81;

        // Internal control state
        attribute integral_x_error : Real := 0.0;

        perform action controller_step : HybridControlComputation {
            in x_m = x_in.x_m.value;
            in x_dot_mps = x_dot_in.x_dot_mps.value;
            in theta_hat_rad = theta_hat_in.theta_hat_rad.value;
            in theta_dot_hat_rps = theta_dot_hat_in.theta_dot_hat_rps.value;
            in x_ref_m = x_ref_in.x_ref_m.value;
            in enable = enable_in.enable.value;

            in f_max;
            in switch_angle_rad;

            in k_e;
            in k_x;
            in k_xd;
            in k_th;
            in k_thd;
            in k_i;

            in m_p;
            in l;
            in g;

            inout integral_x_error;
            out force_cmd_N;
            out mode;
        }

        bind force_cmd_out.force_cmd_N.value = controller_step.force_cmd_N;
        bind mode_out.mode.value = controller_step.mode;

        assert constraint force_limit_cmd : ForceLimitConstraint {
            in force_cmd_N = force_cmd_out.force_cmd_N.value;
            in f_max = f_max;
        }
    }

    part def AngleEstimator {

        // External inputs
        port theta_meas_in : ~ThetaMeasuredOutPort;
        port theta_dot_meas_in : ~ThetaDotMeasuredOutPort;
        port reset_in : ResetInPort;

        // External outputs
        port theta_hat_out : ThetaEstimatedOutPort;
        port theta_dot_hat_out : ThetaDotEstimatedOutPort;
        port bias_hat_out : BiasEstimatedOutPort;

        // Parameters
        attribute dt : Time_s = 0.01;
        attribute l_theta : Gain = 0.15;
        attribute l_bias : Gain = 0.01;
        attribute l_rate : Gain = 0.10;

        // Internal estimator states
        attribute theta_hat_state : Angle_rad := 0.0;
        attribute bias_hat_state : AngularRate_rps := 0.0;

        perform action estimator_step : AngleEstimatorComputation {
            in theta_meas_rad = theta_meas_in.theta_meas_rad.value;
            in theta_dot_meas_rps = theta_dot_meas_in.theta_dot_meas_rps.value;
            in reset = reset_in.reset.value;

            in dt;
            in l_theta;
            in l_bias;
            in l_rate;

            inout theta_hat_state;
            inout bias_hat_state;

            out theta_hat_rad;
            out theta_dot_hat_rps;
            out bias_hat_rps;
        }

        bind theta_hat_out.theta_hat_rad.value = estimator_step.theta_hat_rad;
        bind theta_dot_hat_out.theta_dot_hat_rps.value = estimator_step.theta_dot_hat_rps;
        bind bias_hat_out.bias_hat_rps.value = estimator_step.bias_hat_rps;
    }

    part def CartPolePlant {

        // External inputs
        port force_cmd_in : ForceInPort;
        port disturbance_in : DisturbanceForceInPort;

        // External outputs
        port x_out : PositionOutPort;
        port x_dot_out : VelocityOutPort;
        port theta_out : AngleOutPort;
        port theta_dot_out : AngularRateOutPort;
        port theta_meas_out : ThetaMeasuredOutPort;
        port theta_dot_meas_out : ThetaDotMeasuredOutPort;

        // Continuous states
        attribute x_m : Position_m := 0.0;
        attribute x_dot_mps : Velocity_mps := 0.0;
        attribute theta_rad : Angle_rad := 0.0;
        attribute theta_dot_rps : AngularRate_rps := 0.0;

        // Physical parameters
        attribute m_c : Mass_kg = 0.5;
        attribute m_p : Mass_kg = 0.2;
        attribute l : Length_m = 0.3;
        attribute g : Real = 9.81;

        attribute cart_viscous_b : Damping_NsPerM = 0.05;
        attribute pole_viscous_b : Damping_NmPerRad = 0.01;

        attribute coulomb_friction_N : Force_N = 0.8;
        attribute friction_v0_mps : Velocity_mps = 0.02;

        attribute motor_force_max : Force_N = 20.0;
        attribute x_limit : Position_m = 0.5;

        // Sensor and disturbance parameters
        attribute theta_sensor_bias_rad : Angle_rad := 0.0;
        attribute theta_dot_sensor_bias_rps : AngularRate_rps := 0.0;
        attribute theta_sensor_noise_std : NoiseStdDev = 0.01;
        attribute theta_dot_sensor_noise_std : NoiseStdDev = 0.02;
        attribute gyro_bias_drift_rate : BiasDriftRate = 0.0001;

        // Derived / bound outputs
        bind x_out.x_m.value = x_m;
        bind x_dot_out.x_dot_mps.value = x_dot_mps;
        bind theta_out.theta_rad.value = theta_rad;
        bind theta_dot_out.theta_dot_rps.value = theta_dot_rps;

        // Simple sensor model placeholders
        bind theta_meas_out.theta_meas_rad.value = theta_rad + theta_sensor_bias_rad;
        bind theta_dot_meas_out.theta_dot_meas_rps.value = theta_dot_rps + theta_dot_sensor_bias_rps;

        // Nonlinear dynamics documentation
        doc /*
         * Representative nonlinear plant equations:
         *
         *   F_act = clamp(force_cmd_in.force_cmd_N.value, -motor_force_max, motor_force_max)
         *   F_fric = coulomb_friction_N * tanh(x_dot_mps / friction_v0_mps) + cart_viscous_b * x_dot_mps
         *   F_net  = F_act + disturbance_in.disturbance_force_N.value - F_fric
         *
         *   Den = m_c + m_p * sin(theta_rad)^2
         *
         *   x_ddot =
         *      ( F_net
         *        + m_p * sin(theta_rad) * ( l * theta_dot_rps^2 + g * cos(theta_rad) )
         *      ) / Den
         *
         *   theta_ddot =
         *      ( -F_net * cos(theta_rad)
         *        - m_p * l * theta_dot_rps^2 * sin(theta_rad) * cos(theta_rad)
         *        - (m_c + m_p) * g * sin(theta_rad)
         *      ) / ( l * Den )
         *
         *   plus rotational damping contribution from pole_viscous_b.
         *
         * In a tool-specific execution environment, these equations would be
         * implemented using differential/state-space semantics.
         */

        assert constraint plant_force_limit : ForceLimitConstraint {
            in force_cmd_N = force_cmd_in.force_cmd_N.value;
            in f_max = motor_force_max;
        }

        constraint soft_cart_position_limit : CartSoftPositionLimitConstraint {
            in x_m = x_m;
            in x_limit = x_limit;
        }
    }

    //==================================================
    // Top-level subsystem
    //==================================================

    part def CartPoleSwingUpAndBalanceControlSubsystem {

        // Shared external inputs
        port x_ref_in : PositionReferenceInPort;
        port disturbance_in : DisturbanceForceInPort;
        port enable_in : EnableInPort;
        port reset_in : ResetInPort;

        // Optional external observation ports
        port x_out : PositionOutPort;
        port x_dot_out : VelocityOutPort;
        port theta_out : AngleOutPort;
        port theta_dot_out : AngularRateOutPort;
        port force_cmd_out : ForceOutPort;
        port mode_out : ModeOutPort;
        port theta_hat_out : ThetaEstimatedOutPort;
        port theta_dot_hat_out : ThetaDotEstimatedOutPort;
        port bias_hat_out : BiasEstimatedOutPort;

        // Subcomponents
        part controller : HybridController;
        part estimator : AngleEstimator;
        part plant : CartPolePlant;

        // Shared input bindings
        bind controller.x_ref_in.x_ref_m.value = x_ref_in.x_ref_m.value;
        bind controller.enable_in.enable.value = enable_in.enable.value;
        bind estimator.reset_in.reset.value = reset_in.reset.value;
        bind plant.disturbance_in.disturbance_force_N.value = disturbance_in.disturbance_force_N.value;

        // Required signal interconnections
        interface force_link : ForceCommandInterface connect
            controllerPort ::> controller.force_cmd_out
            to
            plantPort ::> plant.force_cmd_in;

        interface x_feedback : PositionFeedbackInterface connect
            plantPort ::> plant.x_out
            to
            controllerPort ::> controller.x_in;

        interface x_dot_feedback : VelocityFeedbackInterface connect
            plantPort ::> plant.x_dot_out
            to
            controllerPort ::> controller.x_dot_in;

        interface theta_meas_link : AngleMeasurementInterface connect
            plantPort ::> plant.theta_meas_out
            to
            estimatorPort ::> estimator.theta_meas_in;

        interface theta_dot_meas_link : AngularRateMeasurementInterface connect
            plantPort ::> plant.theta_dot_meas_out
            to
            estimatorPort ::> estimator.theta_dot_meas_in;

        interface theta_hat_link : AngleEstimateInterface connect
            estimatorPort ::> estimator.theta_hat_out
            to
            controllerPort ::> controller.theta_hat_in;

        interface theta_dot_hat_link : AngularRateEstimateInterface connect
            estimatorPort ::> estimator.theta_dot_hat_out
            to
            controllerPort ::> controller.theta_dot_hat_in;

        // Expose selected internal signals
        bind x_out.x_m.value = plant.x_out.x_m.value;
        bind x_dot_out.x_dot_mps.value = plant.x_dot_out.x_dot_mps.value;
        bind theta_out.theta_rad.value = plant.theta_out.theta_rad.value;
        bind theta_dot_out.theta_dot_rps.value = plant.theta_dot_out.theta_dot_rps.value;

        bind force_cmd_out.force_cmd_N.value = controller.force_cmd_out.force_cmd_N.value;
        bind mode_out.mode.value = controller.mode_out.mode.value;

        bind theta_hat_out.theta_hat_rad.value = estimator.theta_hat_out.theta_hat_rad.value;
        bind theta_dot_hat_out.theta_dot_hat_rps.value = estimator.theta_dot_hat_out.theta_dot_hat_rps.value;
        bind bias_hat_out.bias_hat_rps.value = estimator.bias_hat_out.bias_hat_rps.value;

        // System-level assertions
        assert constraint angle_convention_ok : AngleConventionConstraint {
            in theta_down = 0.0;
            in theta_upright = 3.141592653589793;
        }
    }

    //==================================================
    // Example usage instance
    //==================================================

    part cartPoleSubsystem : CartPoleSwingUpAndBalanceControlSubsystem {
        // Example initial external commands
        bind x_ref_in.x_ref_m.value = 0.0;
        bind enable_in.enable.value = true;
        bind reset_in.reset.value = false;
        bind disturbance_in.disturbance_force_N.value = 0.0;
    }
}