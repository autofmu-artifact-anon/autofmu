package HydraulicServoCylinderPositionControlModel {

    import ScalarValues::*;

    //==================================================
    // Value and helper definitions
    //==================================================

    attribute def PressureValue :> Real;
    attribute def ForceValue    :> Real;
    attribute def LengthValue   :> Real;
    attribute def SpeedValue    :> Real;
    attribute def AreaValue     :> Real;
    attribute def VolumeValue   :> Real;
    attribute def FlowValue     :> Real;
    attribute def RatioValue    :> Real;

    //==================================================
    // Constraint definitions
    //==================================================

    constraint def SpoolRangeConstraint {
        in spool_u : Real;
        spool_u >= -1.0 and spool_u <= 1.0
    }

    constraint def StrokeLimitConstraint {
        in x_m   : LengthValue;
        in x_min : LengthValue;
        in x_max : LengthValue;
        x_m >= x_min and x_m <= x_max
    }

    //==================================================
    // Calculation definitions
    //==================================================

    calc def Clamp {
        in x    : Real;
        in xmin : Real;
        in xmax : Real;
        return : Real = min(max(x, xmin), xmax);
    }

    calc def Signum {
        in x : Real;
        return : Real =
            if x > 0.0 ? 1.0
            else if x < 0.0 ? -1.0
            else 0.0;
    }

    calc def SoftDeadzone {
        in u     : Real;
        in width : Real;
        return : Real =
            if u > width ? (u - width)
            else if u < -width ? (u + width)
            else 0.0;
    }

    calc def Saturate {
        in u   : Real;
        in lim : Real;
        return : Real = Clamp(u, -lim, lim);
    }

    calc def ChamberVolumeA {
        in V0A    : VolumeValue;
        in areaA  : AreaValue;
        in x_m    : LengthValue;
        return : VolumeValue = V0A + areaA * x_m;
    }

    calc def ChamberVolumeB {
        in V0B    : VolumeValue;
        in areaB  : AreaValue;
        in stroke : LengthValue;
        in x_m    : LengthValue;
        return : VolumeValue = V0B + areaB * (stroke - x_m);
    }

    calc def OrificeFlow {
        in CdA      : Real;
        in spool_u  : Real;
        in dp_Pa    : PressureValue;
        return : FlowValue =
            CdA * spool_u * Signum(dp_Pa) * sqrt(abs(dp_Pa));
    }

    calc def FrictionForce {
        in v_mps      : SpeedValue;
        in Fc_N       : ForceValue;
        in Fs_N       : ForceValue;
        in vs_mps     : SpeedValue;
        in bv_Ns_pm   : Real;
        in alpha      : Real;
        return : ForceValue =
            (Fc_N + (Fs_N - Fc_N) * exp(-abs(v_mps / vs_mps) ^ alpha)) * tanh(v_mps / vs_mps)
            + bv_Ns_pm * v_mps;
    }

    //==================================================
    // Part definitions
    //==================================================

    part def PositionController {

        // Inputs
        in x_ref_m     : LengthValue;
        in x_meas_m    : LengthValue;
        in v_meas_mps  : SpeedValue;
        in enable      : Boolean;

        // Outputs
        out valve_cmd  : Real;
        out sat_flag   : Boolean;

        // Parameters
        attribute Kp                : Real = 8.0;
        attribute Ki                : Real = 40.0;
        attribute u_limit           : Real = 1.0;
        attribute kaw               : Real = 10.0;
        attribute use_velocity_ff   : Boolean = false;
        attribute Kvff              : Real = 0.0;

        // Internal state
        attribute integ_state       : Real = 0.0;
        attribute pos_err_m         : LengthValue;
        attribute u_unsat           : Real;
        attribute u_sat             : Real;
        attribute antiwindup_term   : Real;

        // Signal definitions
        attribute :>> pos_err_m = x_ref_m - x_meas_m;

        attribute :>> u_unsat =
            if enable then
                Kp * pos_err_m + integ_state - Kvff * v_meas_mps
            else
                0.0;

        attribute :>> u_sat = Saturate(u_unsat, u_limit);

        attribute :>> sat_flag = abs(u_unsat - u_sat) > 0.0;

        attribute :>> antiwindup_term = kaw * (u_sat - u_unsat);

        out :>> valve_cmd = u_sat;

        // Note:
        // integ_state is intended as the PI integrator state.
        // Its time evolution can be interpreted as:
        // d/dt(integ_state) = if enable then Ki * pos_err_m + antiwindup_term else 0.0;
    }

    part def SpoolValveActuator {

        // Input / output
        in valve_cmd   : Real;
        out spool_u    : Real;

        // Parameters
        attribute deadzone_width    : Real = 0.03;
        attribute tau_s             : Real = 0.01;
        attribute rate_limit_up     : Real = 100.0;
        attribute rate_limit_down   : Real = 100.0;
        attribute spool_limit       : Real = 1.0;

        // Internal state
        attribute spool_state       : Real = 0.0;
        attribute cmd_deadzone      : Real;
        attribute spool_target      : Real;
        attribute spool_error       : Real;

        attribute :>> cmd_deadzone = SoftDeadzone(valve_cmd, deadzone_width);
        attribute :>> spool_target = Saturate(cmd_deadzone, spool_limit);
        attribute :>> spool_error  = spool_target - spool_state;

        out :>> spool_u = Saturate(spool_state, spool_limit);

        assert constraint spool_range_ok : SpoolRangeConstraint {
            in spool_u = spool_u;
        }

        // Note:
        // spool_state is intended as the actuator continuous state.
        // One possible rate-limited first-order realization is:
        // d/dt(spool_state) = Clamp(spool_error / tau_s, -rate_limit_down, rate_limit_up);
    }

    part def HydraulicCylinderPlant {

        // Inputs
        in spool_u        : Real;
        in load_force_N   : ForceValue;

        // Outputs
        out x_m           : LengthValue;
        out v_mps         : SpeedValue;
        out pA_Pa         : PressureValue;
        out pB_Pa         : PressureValue;
        out rod_force_N   : ForceValue;

        // Parameters: supply / return pressures
        attribute pS_Pa               : PressureValue = 2.1e7;
        attribute pT_Pa               : PressureValue = 1.0e5;

        // Parameters: geometry
        attribute areaA_m2            : AreaValue = 3.14e-4;
        attribute areaB_m2            : AreaValue = 2.50e-4;
        attribute stroke_m            : LengthValue = 0.20;
        attribute x_min_m             : LengthValue = 0.0;
        attribute x_max_m             : LengthValue = 0.20;

        // Parameters: chamber volumes / fluid
        attribute V0A_m3              : VolumeValue = 4.0e-5;
        attribute V0B_m3              : VolumeValue = 4.0e-5;
        attribute beta_e_Pa           : PressureValue = 8.0e8;
        attribute leak_coeff          : Real = 1.0e-12;

        // Parameters: valve / flow
        attribute flow_coeff_A        : Real = 2.0e-5;
        attribute flow_coeff_B        : Real = 2.0e-5;

        // Parameters: mechanics
        attribute mass_kg             : Real = 30.0;
        attribute visc_damp_Ns_pm     : Real = 120.0;

        // Parameters: friction
        attribute Fc_N                : ForceValue = 120.0;
        attribute Fs_N                : ForceValue = 180.0;
        attribute vs_mps              : SpeedValue = 0.01;
        attribute stribeck_alpha      : Real = 2.0;

        // Continuous states
        attribute x_state_m           : LengthValue = 0.0;
        attribute v_state_mps         : SpeedValue = 0.0;
        attribute pA_state_Pa         : PressureValue = 1.0e5;
        attribute pB_state_Pa         : PressureValue = 1.0e5;

        // Intermediate variables
        attribute VA_m3               : VolumeValue;
        attribute VB_m3               : VolumeValue;
        attribute qA_m3ps             : FlowValue;
        attribute qB_m3ps             : FlowValue;
        attribute qLeak_m3ps          : FlowValue;
        attribute friction_N          : ForceValue;
        attribute hydraulic_force_N   : ForceValue;
        attribute x_clamped_m         : LengthValue;

        attribute :>> x_clamped_m = Clamp(x_state_m, x_min_m, x_max_m);

        attribute :>> VA_m3 = ChamberVolumeA(V0A_m3, areaA_m2, x_clamped_m);
        attribute :>> VB_m3 = ChamberVolumeB(V0B_m3, areaB_m2, stroke_m, x_clamped_m);

        // Simplified nonlinear valve flow mapping
        attribute :>> qA_m3ps =
            if spool_u >= 0.0 then
                OrificeFlow(flow_coeff_A, abs(spool_u), pS_Pa - pA_state_Pa)
            else
                -OrificeFlow(flow_coeff_A, abs(spool_u), pA_state_Pa - pT_Pa);

        attribute :>> qB_m3ps =
            if spool_u >= 0.0 then
                -OrificeFlow(flow_coeff_B, abs(spool_u), pB_state_Pa - pT_Pa)
            else
                OrificeFlow(flow_coeff_B, abs(spool_u), pS_Pa - pB_state_Pa);

        attribute :>> qLeak_m3ps = leak_coeff * (pA_state_Pa - pB_state_Pa);

        attribute :>> friction_N =
            FrictionForce(
                v_state_mps,
                Fc_N,
                Fs_N,
                vs_mps,
                visc_damp_Ns_pm,
                stribeck_alpha
            );

        attribute :>> hydraulic_force_N = areaA_m2 * pA_state_Pa - areaB_m2 * pB_state_Pa;
        out :>> rod_force_N = hydraulic_force_N;

        out :>> x_m    = x_clamped_m;
        out :>> v_mps  = v_state_mps;
        out :>> pA_Pa  = pA_state_Pa;
        out :>> pB_Pa  = pB_state_Pa;

        assert constraint stroke_limit_ok : StrokeLimitConstraint {
            in x_m   = x_m;
            in x_min = x_min_m;
            in x_max = x_max_m;
        }

        assert constraint spool_range_ok : SpoolRangeConstraint {
            in spool_u = spool_u;
        }

        // Note:
        // The intended continuous-time state equations are:
        //
        // d/dt(x_state_m)   = v_state_mps
        //
        // d/dt(v_state_mps) =
        //   (hydraulic_force_N - friction_N - load_force_N) / mass_kg
        //
        // d/dt(pA_state_Pa) =
        //   (beta_e_Pa / VA_m3) * (qA_m3ps - areaA_m2 * v_state_mps - qLeak_m3ps)
        //
        // d/dt(pB_state_Pa) =
        //   (beta_e_Pa / VB_m3) * (qB_m3ps + areaB_m2 * v_state_mps + qLeak_m3ps)
    }

    //==================================================
    // Top-level subsystem
    //==================================================

    part def HydraulicServoCylinderPositionControl {

        // Shared external inputs
        in x_ref_m        : LengthValue;
        in enable         : Boolean;
        in load_force_N   : ForceValue;

        // Top-level exposed outputs
        out x_m           : LengthValue;
        out v_mps         : SpeedValue;
        out pA_Pa         : PressureValue;
        out pB_Pa         : PressureValue;
        out rod_force_N   : ForceValue;
        out valve_cmd     : Real;
        out sat_flag      : Boolean;
        out spool_u       : Real;

        part controller : PositionController;
        part actuator   : SpoolValveActuator;
        part plant      : HydraulicCylinderPlant;

        // Shared inputs
        bind controller.x_ref_m      = x_ref_m;
        bind controller.enable       = enable;
        bind plant.load_force_N      = load_force_N;

        // Internal signal connections
        bind actuator.valve_cmd      = controller.valve_cmd;
        bind plant.spool_u           = actuator.spool_u;

        bind controller.x_meas_m     = plant.x_m;
        bind controller.v_meas_mps   = plant.v_mps;

        // Export selected internal signals
        bind x_m                     = plant.x_m;
        bind v_mps                   = plant.v_mps;
        bind pA_Pa                   = plant.pA_Pa;
        bind pB_Pa                   = plant.pB_Pa;
        bind rod_force_N             = plant.rod_force_N;

        bind valve_cmd               = controller.valve_cmd;
        bind sat_flag                = controller.sat_flag;
        bind spool_u                 = actuator.spool_u;
    }

    //==================================================
    // Example subsystem usage
    //==================================================

    part servoAxis : HydraulicServoCylinderPositionControl;

}