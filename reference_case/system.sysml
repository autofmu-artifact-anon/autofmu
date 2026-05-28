package ShipPropulsionSystem {

    part def CruiseSpeedCommand {
        out attribute cruise_speed : Real;
    }

    part def SeaStateMonitor {
        out attribute sea_state : Real;
    }

    part def Controller {
        in attribute cruise_speed : Real;
        in attribute sea_state : Real;
        in attribute K_T : Real;
        in attribute RPM : Real;
        out attribute control_signal : Real;
        out attribute torque_c : Real;
    }

    part def CEWrapper {
        in attribute control_signal : Real;
        out attribute RPM_command : Real;
    }

    part def EngineModel {
        in attribute RPM_command : Real;
        out attribute K_T : Real;
        out attribute RPM : Real;
        out attribute engine_RPM : Real;
        out attribute engine_state_vector : Real[4];
    }

    part def Gearbox {
        in attribute engine_RPM : Real;
        out attribute shaft_RPM : Real;
    }

    part def ShaftLineModel {
        in attribute shaft_RPM_in : Real;
        in attribute resistance_torque : Real;
        out attribute shaft_RPM_out : Real;
        out attribute shaft_torsional_stress : Real;
    }

    part def PropellerDesign {
        in attribute shaft_RPM : Real;
        in attribute torque_c : Real;
        out attribute Thrust : Real;
        out attribute resistance_torque : Real;
    }

    part def FuelConsumptionModel {
        in attribute engine_power : Real;
        in attribute engine_RPM : Real;
        out attribute fuel_flow_rate : Real;
        out attribute SFOC : Real;
    }

    part def HullLoadEstimator {
        in attribute Thrust : Real;
        in attribute sea_state : Real;
        out attribute resistance_margin : Real;
    }

    part def CavitationProxy {
        in attribute Thrust : Real;
        in attribute RPM : Real;
        in attribute sea_state : Real;
        out attribute cavitation_margin : Real;
    }

    part def ExhaustThermalMonitor {
        in attribute fuel_flow_rate : Real;
        in attribute sea_state : Real;
        out attribute thermal_margin : Real;
    }

    part def PropulsionEfficiencyEstimator {
        in attribute Thrust : Real;
        in attribute fuel_flow_rate : Real;
        in attribute RPM : Real;
        out attribute propulsive_efficiency : Real;
    }

    part def ShaftBearingMonitor {
        in attribute shaft_RPM : Real;
        in attribute shaft_torsional_stress : Real;
        out attribute bearing_condition : Real;
    }

    part def SystemShipPropulsion {
        part cruise_speed_cmd : CruiseSpeedCommand;
        part sea_state_mon : SeaStateMonitor;
        part controller : Controller;
        part ce_wrapper : CEWrapper;
        part engine_model : EngineModel;
        part gearbox : Gearbox;
        part shaft_line_model : ShaftLineModel;
        part propeller_design : PropellerDesign;
        part fuel_consumption_model : FuelConsumptionModel;
        part hull_load_estimator : HullLoadEstimator;
        part cavitation_proxy : CavitationProxy;
        part exhaust_thermal_monitor : ExhaustThermalMonitor;
        part propulsion_efficiency : PropulsionEfficiencyEstimator;
        part shaft_bearing_monitor : ShaftBearingMonitor;

        connect cruise_speed_cmd.cruise_speed to controller.cruise_speed;
        connect sea_state_mon.sea_state to controller.sea_state;
        connect controller.control_signal to ce_wrapper.control_signal;
        connect ce_wrapper.RPM_command to engine_model.RPM_command;
        connect engine_model.K_T to controller.K_T;
        connect engine_model.RPM to controller.RPM;
        connect controller.torque_c to propeller_design.torque_c;
        connect engine_model.engine_RPM to gearbox.engine_RPM;
        connect gearbox.shaft_RPM to shaft_line_model.shaft_RPM_in;
        connect shaft_line_model.shaft_RPM_out to propeller_design.shaft_RPM;
        connect propeller_design.resistance_torque to shaft_line_model.resistance_torque;
        connect engine_model.engine_state_vector to fuel_consumption_model.engine_power;
        connect engine_model.engine_state_vector to fuel_consumption_model.engine_RPM;
        connect fuel_consumption_model.fuel_flow_rate to exhaust_thermal_monitor.fuel_flow_rate;
        connect propeller_design.Thrust to hull_load_estimator.Thrust;
        connect propeller_design.Thrust to cavitation_proxy.Thrust;
        connect engine_model.RPM to cavitation_proxy.RPM;
        connect sea_state_mon.sea_state to hull_load_estimator.sea_state;
        connect sea_state_mon.sea_state to exhaust_thermal_monitor.sea_state;
        connect sea_state_mon.sea_state to cavitation_proxy.sea_state;
        connect propeller_design.Thrust to propulsion_efficiency.Thrust;
        connect fuel_consumption_model.fuel_flow_rate to propulsion_efficiency.fuel_flow_rate;
        connect engine_model.RPM to propulsion_efficiency.RPM;
        connect shaft_line_model.shaft_RPM_out to shaft_bearing_monitor.shaft_RPM;
        connect shaft_line_model.shaft_torsional_stress to shaft_bearing_monitor.shaft_torsional_stress;
    }
}
