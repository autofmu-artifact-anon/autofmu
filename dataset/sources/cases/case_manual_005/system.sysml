package BatteryPackThermalManagementClosedLoop {

    import ScalarValues::*;

    //==================================================
    // Utility calculations
    //==================================================

    calc def Clamp01 {
        in x : Real;
        return : Real =
            if x < 0.0 then 0.0
            else if x > 1.0 then 1.0
            else x
    }

    calc def NonNegative {
        in x : Real;
        return : Real =
            if x < 0.0 then 0.0 else x
    }

    calc def AbsValue {
        in x : Real;
        return : Real =
            if x < 0.0 then -x else x
    }

    calc def Saturation {
        in x : Real;
        in x_min : Real;
        in x_max : Real;
        return : Real =
            if x < x_min then x_min
            else if x > x_max then x_max
            else x
    }

    calc def SmoothClamp01 {
        in x : Real;
        in softness : Real;
        return : Real =
            if x <= 0.0 then 0.0
            else if x >= 1.0 then 1.0
            else x / (1.0 + softness * (1.0 - x) * x)
    }

    //==================================================
    // Battery nonlinear electrical / thermal calculations
    //==================================================

    calc def BatteryOCV {
        in soc : Real;
        return : Real;
        attribute s = Clamp01(soc);
        3.0 + 1.1 * s - 0.25 * s * s + 0.12 * s * s * s
    }

    calc def BatteryInternalResistance {
        in soc : Real;
        in temp_cell_C : Real;
        in r0_Ohm : Real;
        in alpha_soc : Real;
        in beta_temp_invC : Real;
        in t_ref_C : Real;
        return : Real;
        attribute s = Clamp01(soc);
        attribute soc_factor = 1.0 + alpha_soc * (1.0 - s);
        attribute temp_factor = exp(beta_temp_invC * (t_ref_C - temp_cell_C));
        r0_Ohm * soc_factor * temp_factor
    }

    calc def BatteryHeatGeneration {
        in i_load_A : Real;
        in resistance_Ohm : Real;
        in k_pol_W_per_A : Real;
        return : Real;
        attribute abs_i = AbsValue(i_load_A);
        i_load_A * i_load_A * resistance_Ohm + abs_i * k_pol_W_per_A
    }

    calc def BatteryTerminalVoltage {
        in ocv_V : Real;
        in i_load_A : Real;
        in resistance_Ohm : Real;
        return : Real =
            NonNegative(ocv_V - i_load_A * resistance_Ohm)
    }

    calc def SocDerivative {
        in i_load_A : Real;
        in capacity_Ah : Real;
        return : Real =
            -i_load_A / (3600.0 * capacity_Ah)
    }

    calc def BatteryTemperatureDerivative {
        in heat_gen_W : Real;
        in heat_removed_W : Real;
        in cth_J_per_K : Real;
        return : Real =
            (heat_gen_W - heat_removed_W) / cth_J_per_K
    }

    //==================================================
    // Coolant loop calculations
    //==================================================

    calc def UAFromPumpCommand {
        in pump_cmd : Real;
        in ua_min_W_per_K : Real;
        in ua_max_W_per_K : Real;
        in shape_gain : Real;
        return : Real;
        attribute u = Clamp01(pump_cmd);
        ua_min_W_per_K + (ua_max_W_per_K - ua_min_W_per_K) * (1.0 - exp(-shape_gain * sqrt(u)))
    }

    calc def HeatRemoved {
        in ua_W_per_K : Real;
        in temp_cell_C : Real;
        in coolant_temp_C : Real;
        return : Real =
            ua_W_per_K * (temp_cell_C - coolant_temp_C)
    }

    calc def CoolantTemperatureDerivative {
        in ambient_temp_C : Real;
        in coolant_temp_C : Real;
        in heat_in_W : Real;
        in pump_cmd_eff : Real;
        in cth_coolant_J_per_K : Real;
        in k_reject_W_per_K : Real;
        in k_pump_reject_W_per_K : Real;
        return : Real;
        attribute reject_W =
            (k_reject_W_per_K + k_pump_reject_W_per_K * Clamp01(pump_cmd_eff))
            * (coolant_temp_C - ambient_temp_C);
        (heat_in_W - reject_W) / cth_coolant_J_per_K
    }

    calc def FirstOrderLagDerivative {
        in command : Real;
        in state : Real;
        in tau_s : Real;
        return : Real =
            (command - state) / tau_s
    }

    //==================================================
    // Controller calculations
    //==================================================

    calc def HysteresisEnable {
        in error_C : Real;
        in band_C : Real;
        in previous_on : Real;
        return : Real =
            if previous_on >= 0.5 and error_C > -band_C then 1.0
            else if previous_on < 0.5 and error_C > band_C then 1.0
            else 0.0
    }

    calc def PIControlRaw {
        in kp : Real;
        in ki : Real;
        in error_C : Real;
        in integrator_state : Real;
        in ff_coolant_gain : Real;
        in temp_ref_C : Real;
        in coolant_temp_C : Real;
        return : Real =
            kp * error_C + ki * integrator_state
            + ff_coolant_gain * (temp_ref_C - coolant_temp_C)
    }

    calc def AntiWindupIntegratorDerivative {
        in enable_num : Real;
        in hysteresis_on : Real;
        in error_C : Real;
        in u_unsat : Real;
        in u_sat : Real;
        in kaw : Real;
        return : Real =
            enable_num * hysteresis_on * (error_C + kaw * (u_sat - u_unsat))
    }

    //==================================================
    // Constraints
    //==================================================

    constraint def PumpCommandRangeConstraint {
        in pump_cmd : Real;
        pump_cmd >= 0.0 and pump_cmd <= 1.0
    }

    constraint def SocRangeConstraint {
        in soc : Real;
        soc >= 0.0 and soc <= 1.0
    }

    constraint def NonNegativeVoltageConstraint {
        in v_term_V : Real;
        v_term_V >= 0.0
    }

    //==================================================
    // Port definitions
    //==================================================

    port def ThermalControllerPort {
        in enable : Boolean;
        in temp_ref_C : Real;
        in temp_cell_C : Real;
        in coolant_temp_C : Real;
        out pump_cmd : Real;
        out sat_flag : Boolean;
    }

    port def CoolantLoopPort {
        in pump_cmd : Real;
        in ambient_temp_C : Real;
        in heat_in_W : Real;
        out coolant_temp_C : Real;
        out heat_removed_W : Real;
    }

    port def BatteryPackPort {
        in i_load_A : Real;
        in coolant_in_temp_C : Real;
        out v_term_V : Real;
        out soc : Real;
        out temp_cell_C : Real;
        out heat_gen_W : Real;
    }

    //==================================================
    // Thermal controller
    //==================================================

    part def ThermalController {

        port io : ThermalControllerPort;

        // Parameters
        attribute kp : Real = 0.08;
        attribute ki : Real = 0.02;
        attribute hysteresis_band_C : Real = 0.5;
        attribute ff_coolant_gain : Real = 0.03;
        attribute kaw : Real = 0.5;
        attribute pump_min : Real = 0.0;
        attribute pump_max : Real = 1.0;

        // Continuous / memory states
        attribute integrator_state : Real = 0.0;
        attribute hysteresis_state : Real = 0.0;

        // Internal variables
        attribute enable_num : Real = if io.enable then 1.0 else 0.0;
        attribute error_C : Real = io.temp_cell_C - io.temp_ref_C;
        attribute hysteresis_on : Real =
            HysteresisEnable(error_C, hysteresis_band_C, hysteresis_state);

        attribute u_unsat : Real =
            PIControlRaw(kp, ki, error_C, integrator_state,
                         ff_coolant_gain, io.temp_ref_C, io.coolant_temp_C);

        attribute u_limited : Real =
            Saturation(enable_num * hysteresis_on * u_unsat, pump_min, pump_max);

        attribute sat_margin : Real = AbsValue(u_unsat - u_limited);
        attribute sat_flag_num : Real = if sat_margin > 1.0e-9 then 1.0 else 0.0;

        attribute integrator_dot : Real =
            AntiWindupIntegratorDerivative(enable_num, hysteresis_on, error_C,
                                           u_unsat, u_limited, kaw);

        // Outputs
        out attribute pump_cmd : Real = u_limited;
        out attribute sat_flag : Boolean = sat_flag_num >= 0.5;

        // Bind outputs to the port
        bind io.pump_cmd = pump_cmd;
        bind io.sat_flag = sat_flag;
    }

    //==================================================
    // Coolant loop plant
    //==================================================

    part def CoolantLoopPlant {

        port io : CoolantLoopPort;

        // Parameters
        attribute cth_coolant_J_per_K : Real = 4500.0;
        attribute tau_pump_s : Real = 1.2;
        attribute ua_min_W_per_K : Real = 5.0;
        attribute ua_max_W_per_K : Real = 180.0;
        attribute ua_shape_gain : Real = 3.0;
        attribute k_reject_W_per_K : Real = 22.0;
        attribute k_pump_reject_W_per_K : Real = 40.0;

        // States
        attribute coolant_temp_C_state : Real = 25.0;
        attribute pump_cmd_eff_state : Real = 0.0;

        // Internal variables
        attribute pump_cmd_limited : Real = Clamp01(io.pump_cmd);
        attribute pump_cmd_eff_dot : Real =
            FirstOrderLagDerivative(pump_cmd_limited, pump_cmd_eff_state, tau_pump_s);

        attribute ua_W_per_K : Real =
            UAFromPumpCommand(pump_cmd_eff_state,
                              ua_min_W_per_K, ua_max_W_per_K, ua_shape_gain);

        attribute coolant_temp_dot : Real =
            CoolantTemperatureDerivative(io.ambient_temp_C,
                                         coolant_temp_C_state,
                                         io.heat_in_W,
                                         pump_cmd_eff_state,
                                         cth_coolant_J_per_K,
                                         k_reject_W_per_K,
                                         k_pump_reject_W_per_K);

        // Outputs
        out attribute coolant_temp_C : Real = coolant_temp_C_state;
        out attribute heat_removed_W : Real = io.heat_in_W;

        bind io.coolant_temp_C = coolant_temp_C;
        bind io.heat_removed_W = heat_removed_W;
    }

    //==================================================
    // Battery pack electro-thermal plant
    //==================================================

    part def BatteryPackPlant {

        port io : BatteryPackPort;

        // Parameters
        attribute capacity_Ah : Real = 120.0;
        attribute cth_cell_J_per_K : Real = 18000.0;
        attribute r0_Ohm : Real = 0.012;
        attribute alpha_soc : Real = 0.6;
        attribute beta_temp_invC : Real = 0.035;
        attribute t_ref_C : Real = 25.0;
        attribute k_pol_W_per_A : Real = 0.08;

        // Thermal coupling to coolant
        attribute h_batt_to_coolant_W_per_K : Real = 28.0;

        // States
        attribute soc_state : Real = 0.85;
        attribute temp_cell_C_state : Real = 30.0;

        // Nonlinear electrical model
        attribute soc_soft : Real = SmoothClamp01(soc_state, 0.05);
        attribute ocv_V : Real = BatteryOCV(soc_soft);
        attribute resistance_Ohm : Real =
            BatteryInternalResistance(soc_soft, temp_cell_C_state,
                                      r0_Ohm, alpha_soc, beta_temp_invC, t_ref_C);

        attribute heat_gen_W_int : Real =
            BatteryHeatGeneration(io.i_load_A, resistance_Ohm, k_pol_W_per_A);

        attribute heat_removed_W_int : Real =
            HeatRemoved(h_batt_to_coolant_W_per_K,
                        temp_cell_C_state, io.coolant_in_temp_C);

        attribute soc_dot : Real =
            SocDerivative(io.i_load_A, capacity_Ah);

        attribute temp_cell_dot : Real =
            BatteryTemperatureDerivative(heat_gen_W_int,
                                         heat_removed_W_int,
                                         cth_cell_J_per_K);

        // Outputs
        out attribute v_term_V : Real =
            BatteryTerminalVoltage(ocv_V, io.i_load_A, resistance_Ohm);

        out attribute soc : Real = soc_soft;
        out attribute temp_cell_C : Real = temp_cell_C_state;
        out attribute heat_gen_W : Real = heat_gen_W_int;

        bind io.v_term_V = v_term_V;
        bind io.soc = soc;
        bind io.temp_cell_C = temp_cell_C;
        bind io.heat_gen_W = heat_gen_W;

        assert constraint soc_range : SocRangeConstraint {
            in soc = soc
        }

        assert constraint non_negative_voltage : NonNegativeVoltageConstraint {
            in v_term_V = v_term_V
        }
    }

    //==================================================
    // Closed-loop subsystem
    //==================================================

    part def BatteryPackThermalManagementClosedLoop {

        // Shared external inputs
        in attribute enable : Boolean;
        in attribute temp_ref_C : Real;
        in attribute i_load_A : Real;
        in attribute ambient_temp_C : Real;

        // Exposed outputs
        out attribute pump_cmd : Real;
        out attribute sat_flag : Boolean;
        out attribute v_term_V : Real;
        out attribute soc : Real;
        out attribute temp_cell_C : Real;
        out attribute coolant_temp_C : Real;
        out attribute heat_gen_W : Real;
        out attribute heat_removed_W : Real;

        // Internal parts
        part thermalController : ThermalController;
        part coolantLoopPlant : CoolantLoopPlant;
        part batteryPackPlant : BatteryPackPlant;

        // Shared inputs to parts
        bind thermalController.io.enable = enable;
        bind thermalController.io.temp_ref_C = temp_ref_C;

        bind batteryPackPlant.io.i_load_A = i_load_A;

        bind coolantLoopPlant.io.ambient_temp_C = ambient_temp_C;

        // Closed-loop signal wiring
        bind coolantLoopPlant.io.pump_cmd = thermalController.io.pump_cmd;
        bind coolantLoopPlant.io.heat_in_W = batteryPackPlant.io.heat_gen_W;
        bind batteryPackPlant.io.coolant_in_temp_C = coolantLoopPlant.io.coolant_temp_C;
        bind thermalController.io.temp_cell_C = batteryPackPlant.io.temp_cell_C;
        bind thermalController.io.coolant_temp_C = coolantLoopPlant.io.coolant_temp_C;

        // Exposed subsystem outputs
        bind pump_cmd = thermalController.io.pump_cmd;
        bind sat_flag = thermalController.io.sat_flag;

        bind v_term_V = batteryPackPlant.io.v_term_V;
        bind soc = batteryPackPlant.io.soc;
        bind temp_cell_C = batteryPackPlant.io.temp_cell_C;
        bind heat_gen_W = batteryPackPlant.io.heat_gen_W;

        bind coolant_temp_C = coolantLoopPlant.io.coolant_temp_C;
        bind heat_removed_W = coolantLoopPlant.io.heat_removed_W;

        // Top-level safety / range assertions
        assert constraint pump_range : PumpCommandRangeConstraint {
            in pump_cmd = pump_cmd
        }
    }
}