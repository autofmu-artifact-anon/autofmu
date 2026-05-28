package InvertedPendulumControlSystem {

    import ScalarValues::*;

    //-----------------------------
    // Basic value structures
    //-----------------------------

    attribute def PlantState {
        attribute x_m : Real;
        attribute x_dot_mps : Real;
        attribute theta_rad : Real;
        attribute theta_dot_radps : Real;
    }

    attribute def ControllerState {
        attribute int_x_err : Real;
        attribute int_theta_err : Real;
        attribute actuator_force_N : Real;
    }

    attribute def PlantParameters {
        attribute cart_mass_kg : Real;
        attribute pend_mass_kg : Real;
        attribute pend_length_m : Real;
        attribute gravity_mps2 : Real;
        attribute viscous_cart_Ns_per_m : Real;
        attribute viscous_joint_Nms_per_rad : Real;
    }

    attribute def ControllerParameters {
        attribute k_x : Real;
        attribute k_x_dot : Real;
        attribute k_theta : Real;
        attribute k_theta_dot : Real;
        attribute k_i_x : Real;
        attribute k_i_theta : Real;
        attribute anti_windup_gain : Real;
        attribute actuator_tau_s : Real;
        attribute force_limit_N : Real;
        attribute deadzone_N : Real;
    }

    //-----------------------------
    // Ports
    //-----------------------------

    port def ControllerReferencePort {
        in x_ref_m : Real;
        in theta_ref_rad : Real;
    }

    port def PlantMeasurementPort {
        out x_m : Real;
        out x_dot_mps : Real;
        out theta_rad : Real;
        out theta_dot_radps : Real;
    }

    port def ControlForcePort {
        out force_cmd_N : Real;
    }

    port def PlantForceInPort {
        in force_cmd_N : Real;
    }

    port def DisturbancePort {
        in disturbance_N : Real;
    }

    //-----------------------------
    // Interfaces
    //-----------------------------

    interface def MeasurementInterface {
        end plantSide : PlantMeasurementPort;
        end controllerSide : ~PlantMeasurementPort;

        flow plantSide.x_m to controllerSide.x_m;
        flow plantSide.x_dot_mps to controllerSide.x_dot_mps;
        flow plantSide.theta_rad to controllerSide.theta_rad;
        flow plantSide.theta_dot_radps to controllerSide.theta_dot_radps;
    }

    interface def ControlInterface {
        end controllerSide : ControlForcePort;
        end plantSide : PlantForceInPort;

        flow controllerSide.force_cmd_N to plantSide.force_cmd_N;
    }

    //-----------------------------
    // Utility calculations
    //-----------------------------

    calc def Saturate {
        in u : Real;
        in lower : Real;
        in upper : Real;
        return : Real =
            if u < lower then lower
            else if u > upper then upper
            else u;
    }

    calc def ApplyDeadzone {
        in u : Real;
        in dz : Real;
        return : Real =
            if u > dz then u - dz
            else if u < -dz then u + dz
            else 0.0;
    }

    calc def ControllerUnsatForce {
        in x_ref_m : Real;
        in theta_ref_rad : Real;
        in x_m : Real;
        in x_dot_mps : Real;
        in theta_rad : Real;
        in theta_dot_radps : Real;
        in int_x_err : Real;
        in int_theta_err : Real;
        in p : ControllerParameters;

        attribute x_err : Real = x_ref_m - x_m;
        attribute theta_err : Real = theta_ref_rad - theta_rad;

        return : Real =
            p.k_x * x_err +
            p.k_x_dot * (-x_dot_mps) +
            p.k_theta * theta_err +
            p.k_theta_dot * (-theta_dot_radps) +
            p.k_i_x * int_x_err +
            p.k_i_theta * int_theta_err;
    }

    calc def PendulumAngularAcc {
        in s : PlantState;
        in applied_force_N : Real;
        in disturbance_N : Real;
        in p : PlantParameters;

        attribute M : Real = p.cart_mass_kg;
        attribute m : Real = p.pend_mass_kg;
        attribute l : Real = p.pend_length_m;
        attribute g : Real = p.gravity_mps2;
        attribute b_c : Real = p.viscous_cart_Ns_per_m;
        attribute b_p : Real = p.viscous_joint_Nms_per_rad;

        attribute sin_t : Real = sin(s.theta_rad);
        attribute cos_t : Real = cos(s.theta_rad);
        attribute total_force : Real =
            applied_force_N + disturbance_N - b_c * s.x_dot_mps;
        attribute den : Real =
            l * (M + m - m * cos_t * cos_t);

        return : Real =
            (
                (M + m) * g * sin_t
                - cos_t * (total_force + m * l * s.theta_dot_radps * s.theta_dot_radps * sin_t)
                - ((M + m) / (m * l)) * b_p * s.theta_dot_radps
            ) / den;
    }

    calc def CartLinearAcc {
        in s : PlantState;
        in theta_ddot_radps2 : Real;
        in applied_force_N : Real;
        in disturbance_N : Real;
        in p : PlantParameters;

        attribute M : Real = p.cart_mass_kg;
        attribute m : Real = p.pend_mass_kg;
        attribute l : Real = p.pend_length_m;
        attribute b_c : Real = p.viscous_cart_Ns_per_m;

        attribute sin_t : Real = sin(s.theta_rad);
        attribute cos_t : Real = cos(s.theta_rad);
        attribute total_force : Real =
            applied_force_N + disturbance_N - b_c * s.x_dot_mps;

        return : Real =
            (
                total_force
                + m * l * s.theta_dot_radps * s.theta_dot_radps * sin_t
                - m * l * theta_ddot_radps2 * cos_t
            ) / (M + m);
    }

    //-----------------------------
    // Constraints
    //-----------------------------

    constraint def ModerateAngleValidity {
        in theta_rad : Real;
        abs(theta_rad) <= 0.7
    }

    constraint def ForceWithinLimit {
        in force_cmd_N : Real;
        in limit_N : Real;
        abs(force_cmd_N) <= limit_N
    }

    //-----------------------------
    // Controller
    //-----------------------------

    part def PendulumController {

        port refIn : ControllerReferencePort;
        port measIn : ~PlantMeasurementPort;
        port cmdOut : ControlForcePort;

        attribute params : ControllerParameters;

        attribute state : ControllerState {
            :>> int_x_err = 0.0;
            :>> int_theta_err = 0.0;
            :>> actuator_force_N = 0.0;
        }

        calc computeUnsatForce {
            in x_ref_m : Real = refIn.x_ref_m;
            in theta_ref_rad : Real = refIn.theta_ref_rad;
            in x_m : Real = measIn.x_m;
            in x_dot_mps : Real = measIn.x_dot_mps;
            in theta_rad : Real = measIn.theta_rad;
            in theta_dot_radps : Real = measIn.theta_dot_radps;
            in int_x_err : Real = state.int_x_err;
            in int_theta_err : Real = state.int_theta_err;
            in p : ControllerParameters = params;
            return : Real = ControllerUnsatForce(
                x_ref_m, theta_ref_rad,
                x_m, x_dot_mps,
                theta_rad, theta_dot_radps,
                int_x_err, int_theta_err, p
            );
        }

        calc limitedForce {
            in u : Real = computeUnsatForce;
            in lower : Real = -params.force_limit_N;
            in upper : Real = params.force_limit_N;
            return : Real = Saturate(u, lower, upper);
        }

        calc commandedForce {
            in u : Real = limitedForce;
            in dz : Real = params.deadzone_N;
            return : Real = ApplyDeadzone(u, dz);
        }

        bind cmdOut.force_cmd_N = state.actuator_force_N;

        action update {

            in dt_s : Real;

            attribute x_err : Real = refIn.x_ref_m - measIn.x_m;
            attribute theta_err : Real = refIn.theta_ref_rad - measIn.theta_rad;
            attribute u_unsat : Real = computeUnsatForce;
            attribute u_sat : Real = limitedForce;
            attribute u_cmd : Real = commandedForce;

            then assign state.int_x_err :=
                state.int_x_err + dt_s * (
                    x_err + params.anti_windup_gain * (u_sat - u_unsat)
                );

            then assign state.int_theta_err :=
                state.int_theta_err + dt_s * (
                    theta_err + params.anti_windup_gain * (u_sat - u_unsat)
                );

            then assign state.actuator_force_N :=
                state.actuator_force_N
                + (dt_s / params.actuator_tau_s) * (u_cmd - state.actuator_force_N);
        }

        assert constraint controller_force_limit : ForceWithinLimit {
            in force_cmd_N = state.actuator_force_N;
            in limit_N = params.force_limit_N;
        }
    }

    //-----------------------------
    // Plant
    //-----------------------------

    part def InvertedPendulumPlant {

        port forceIn : PlantForceInPort;
        port disturbanceIn : DisturbancePort;
        port measOut : PlantMeasurementPort;

        attribute params : PlantParameters;

        attribute state : PlantState {
            :>> x_m = 0.0;
            :>> x_dot_mps = 0.0;
            :>> theta_rad = 0.0;
            :>> theta_dot_radps = 0.0;
        }

        bind measOut.x_m = state.x_m;
        bind measOut.x_dot_mps = state.x_dot_mps;
        bind measOut.theta_rad = state.theta_rad;
        bind measOut.theta_dot_radps = state.theta_dot_radps;

        calc theta_ddot {
            in s : PlantState = state;
            in applied_force_N : Real = forceIn.force_cmd_N;
            in disturbance_N : Real = disturbanceIn.disturbance_N;
            in p : PlantParameters = params;
            return : Real = PendulumAngularAcc(s, applied_force_N, disturbance_N, p);
        }

        calc x_ddot {
            in s : PlantState = state;
            in theta_ddot_radps2 : Real = theta_ddot;
            in applied_force_N : Real = forceIn.force_cmd_N;
            in disturbance_N : Real = disturbanceIn.disturbance_N;
            in p : PlantParameters = params;
            return : Real = CartLinearAcc(s, theta_ddot_radps2, applied_force_N, disturbance_N, p);
        }

        action update {

            in dt_s : Real;

            then assign state.x_m :=
                state.x_m + dt_s * state.x_dot_mps;

            then assign state.x_dot_mps :=
                state.x_dot_mps + dt_s * x_ddot;

            then assign state.theta_rad :=
                state.theta_rad + dt_s * state.theta_dot_radps;

            then assign state.theta_dot_radps :=
                state.theta_dot_radps + dt_s * theta_ddot;
        }

        constraint operating_range_note : ModerateAngleValidity {
            in theta_rad = state.theta_rad;
        }
    }

    //-----------------------------
    // Integrated system
    //-----------------------------

    part def InvertedPendulumStabilizationSystem {

        port refIn : ControllerReferencePort;
        port disturbanceIn : DisturbancePort;

        part controller : PendulumController;
        part plant : InvertedPendulumPlant;

        bind controller.refIn.x_ref_m = refIn.x_ref_m;
        bind controller.refIn.theta_ref_rad = refIn.theta_ref_rad;

        bind plant.disturbanceIn.disturbance_N = disturbanceIn.disturbance_N;

        interface measurementLink : MeasurementInterface connect
            plantSide ::> plant.measOut
            to controllerSide ::> controller.measIn;

        interface controlLink : ControlInterface connect
            controllerSide ::> controller.cmdOut
            to plantSide ::> plant.forceIn;

        action step {
            in dt_s : Real;

            first controller.update {
                in dt_s = step::dt_s;
            }

            then plant.update {
                in dt_s = step::dt_s;
            }
        }
    }

    //-----------------------------
    // Example configuration
    //-----------------------------

    part pendulumControlSystem : InvertedPendulumStabilizationSystem {

        part redefines controller {
            attribute :>> params {
                :>> k_x = 25.0;
                :>> k_x_dot = 12.0;
                :>> k_theta = 180.0;
                :>> k_theta_dot = 24.0;
                :>> k_i_x = 4.0;
                :>> k_i_theta = 12.0;
                :>> anti_windup_gain = 0.5;
                :>> actuator_tau_s = 0.03;
                :>> force_limit_N = 30.0;
                :>> deadzone_N = 0.5;
            }
        }

        part redefines plant {
            attribute :>> params {
                :>> cart_mass_kg = 1.0;
                :>> pend_mass_kg = 0.2;
                :>> pend_length_m = 0.5;
                :>> gravity_mps2 = 9.81;
                :>> viscous_cart_Ns_per_m = 0.05;
                :>> viscous_joint_Nms_per_rad = 0.02;
            }
        }
    }
}