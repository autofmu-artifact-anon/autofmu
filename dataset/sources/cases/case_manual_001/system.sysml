package EVBatteryThermalManagementAndPowerLimitingSystem {

    import ScalarValues::*;

    //-----------------------------
    // Constraints and calculations
    //-----------------------------

    constraint def SocRangeConstraint {
        in soc : Real;
        soc >= 0.0 and soc <= 1.0
    }

    constraint def UnitIntervalConstraint {
        in x : Real;
        x >= 0.0 and x <= 1.0
    }

    constraint def NonNegativeConstraint {
        in x : Real;
        x >= 0.0
    }

    calc def Clamp01 {
        in x : Real;
        return : Real =
            if x < 0.0 ? 0.0
            else if x > 1.0 ? 1.0
            else x
    }

    calc def Clamp {
        in x : Real;
        in minVal : Real;
        in maxVal : Real;
        return : Real =
            if x < minVal ? minVal
            else if x > maxVal ? maxVal
            else x
    }

    calc def DriverPowerToCurrent {
        in driverPowerRequest_W : Real;
        in voltage_V : Real;
        return : Real =
            if voltage_V <= 1.0 ? 0.0
            else driverPowerRequest_W / voltage_V
    }

    calc def OverheatDerateFactor {
        in coreTemperature_C : Real;
        in derateStartTemp_C : Real;
        in shutdownTemp_C : Real;
        return : Real =
            if coreTemperature_C <= derateStartTemp_C ? 1.0
            else if coreTemperature_C >= shutdownTemp_C ? 0.0
            else 1.0 - (coreTemperature_C - derateStartTemp_C) / (shutdownTemp_C - derateStartTemp_C)
    }

    calc def PumpCommandLaw {
        in coreTemperature_C : Real;
        in ambientTemperature_C : Real;
        return : Real =
            Clamp01((coreTemperature_C - ambientTemperature_C - 5.0) / 25.0)
    }

    calc def FanCommandLaw {
        in coreTemperature_C : Real;
        in ambientTemperature_C : Real;
        return : Real =
            Clamp01((coreTemperature_C - ambientTemperature_C - 8.0) / 20.0)
    }

    calc def CoolantFlowFromPump {
        in pumpCommand : Real;
        in maxCoolantFlow_kgps : Real;
        return : Real =
            maxCoolantFlow_kgps * pumpCommand * pumpCommand
    }

    calc def UAFromFan {
        in fanCommand : Real;
        in uaMin_WpK : Real;
        in uaMax_WpK : Real;
        return : Real =
            uaMin_WpK + (uaMax_WpK - uaMin_WpK) * fanCommand
    }

    calc def CoolantInletTemperature {
        in ambientTemperature_C : Real;
        in batterySurfaceTemperature_C : Real;
        in heatLoad_W : Real;
        in ua_WpK : Real;
        return : Real =
            if ua_WpK <= 1.0 ? batterySurfaceTemperature_C
            else ambientTemperature_C + heatLoad_W / ua_WpK
    }

    calc def RadiatorOutletTemperature {
        in coolantInletTemperature_C : Real;
        in ambientTemperature_C : Real;
        in fanCommand : Real;
        return : Real =
            ambientTemperature_C + (coolantInletTemperature_C - ambientTemperature_C) * (1.0 - 0.7 * Clamp01(fanCommand))
    }

    calc def PumpPower {
        in pumpCommand : Real;
        in pumpPowerMax_W : Real;
        return : Real =
            pumpPowerMax_W * pumpCommand * pumpCommand * pumpCommand
    }

    calc def OpenCircuitVoltage {
        in soc : Real;
        return : Real =
            280.0 + 120.0 * soc
    }

    calc def InternalResistance {
        in soc : Real;
        in coreTemperature_C : Real;
        return : Real =
            0.010 + 0.020 * (1.0 - soc) + 0.0001 * (25.0 - coreTemperature_C)
    }

    calc def BatteryVoltage {
        in soc : Real;
        in current_A : Real;
        in coreTemperature_C : Real;
        return : Real =
            OpenCircuitVoltage(soc) - current_A * InternalResistance(soc, coreTemperature_C)
    }

    calc def HeatGeneration {
        in current_A : Real;
        in soc : Real;
        in coreTemperature_C : Real;
        return : Real =
            current_A * current_A * InternalResistance(soc, coreTemperature_C)
    }

    //-----------------------------
    // Port definitions
    //-----------------------------

    port def ThermalControllerPort {
        in coreTemperature_C : Real;
        in soc : Real;
        in voltage_V : Real;
        in driverPowerRequest_W : Real;
        in ambientTemperature_C : Real;

        out current_A : Real;
        out pumpCommand : Real;
        out fanCommand : Real;
    }

    port def BatteryPackPort {
        in current_A : Real;
        in coolantInletTemperature_C : Real;
        in coolantFlow_kgps : Real;
        in ambientTemperature_C : Real;

        out voltage_V : Real;
        out soc : Real;
        out coreTemperature_C : Real;
        out surfaceTemperature_C : Real;
        out heatGeneration_W : Real;
    }

    port def CoolingLoopPort {
        in pumpCommand : Real;
        in fanCommand : Real;
        in ambientTemperature_C : Real;
        in batterySurfaceTemperature_C : Real;
        in heatLoad_W : Real;

        out coolantInletTemperature_C : Real;
        out coolantFlow_kgps : Real;
        out radiatorOutletTemperature_C : Real;
        out pumpPower_W : Real;
    }

    //-----------------------------
    // Interface definitions
    //-----------------------------

    interface def ControllerBatteryInterface {
        end controllerEnd : ThermalControllerPort;
        end batteryEnd : BatteryPackPort;

        flow controllerEnd.current_A to batteryEnd.current_A;
        flow batteryEnd.voltage_V to controllerEnd.voltage_V;
        flow batteryEnd.soc to controllerEnd.soc;
        flow batteryEnd.coreTemperature_C to controllerEnd.coreTemperature_C;
    }

    interface def ControllerCoolingInterface {
        end controllerEnd : ThermalControllerPort;
        end coolingEnd : CoolingLoopPort;

        flow controllerEnd.pumpCommand to coolingEnd.pumpCommand;
        flow controllerEnd.fanCommand to coolingEnd.fanCommand;
    }

    interface def BatteryCoolingInterface {
        end batteryEnd : BatteryPackPort;
        end coolingEnd : CoolingLoopPort;

        flow batteryEnd.surfaceTemperature_C to coolingEnd.batterySurfaceTemperature_C;
        flow batteryEnd.heatGeneration_W to coolingEnd.heatLoad_W;
        flow coolingEnd.coolantInletTemperature_C to batteryEnd.coolantInletTemperature_C;
        flow coolingEnd.coolantFlow_kgps to batteryEnd.coolantFlow_kgps;
    }

    //-----------------------------
    // Part definitions
    //-----------------------------

    part def ThermalManagementController {
        port controllerPort : ThermalControllerPort;

        attribute derateStartTemp_C : Real = 45.0;
        attribute shutdownTemp_C : Real = 60.0;
        attribute currentLimit_A : Real = 500.0;

        attribute requestedCurrent_A : Real;
        attribute derateFactor : Real;

        attribute requestedCurrent_A =
            DriverPowerToCurrent(
                controllerPort.driverPowerRequest_W,
                controllerPort.voltage_V
            );

        attribute derateFactor =
            OverheatDerateFactor(
                controllerPort.coreTemperature_C,
                derateStartTemp_C,
                shutdownTemp_C
            );

        out attribute commandedCurrent_A : Real =
            Clamp(
                requestedCurrent_A * derateFactor,
                -currentLimit_A,
                currentLimit_A
            );

        out attribute commandedPump : Real =
            PumpCommandLaw(
                controllerPort.coreTemperature_C,
                controllerPort.ambientTemperature_C
            );

        out attribute commandedFan : Real =
            FanCommandLaw(
                controllerPort.coreTemperature_C,
                controllerPort.ambientTemperature_C
            );

        bind controllerPort.current_A = commandedCurrent_A;
        bind controllerPort.pumpCommand = commandedPump;
        bind controllerPort.fanCommand = commandedFan;

        assert constraint currentCmdNonNegative : NonNegativeConstraint {
            in x = currentLimit_A;
        }

        assert constraint pumpCmdRange : UnitIntervalConstraint {
            in x = controllerPort.pumpCommand;
        }

        assert constraint fanCmdRange : UnitIntervalConstraint {
            in x = controllerPort.fanCommand;
        }
    }

    part def BatteryPackElectroThermal {
        port batteryPort : BatteryPackPort;

        attribute capacity_C : Real = 180000.0;
        attribute thermalCapacity_JpK : Real = 250000.0;
        attribute coreSurfaceConductance_WpK : Real = 120.0;
        attribute surfaceAmbientLeak_WpK : Real = 15.0;

        attribute socState : Real = 0.80;
        attribute coreTemperatureState_C : Real = 30.0;
        attribute surfaceTemperatureState_C : Real = 29.0;

        out attribute packVoltage_V : Real =
            BatteryVoltage(
                socState,
                batteryPort.current_A,
                coreTemperatureState_C
            );

        out attribute generatedHeat_W : Real =
            HeatGeneration(
                batteryPort.current_A,
                socState,
                coreTemperatureState_C
            );

        out attribute reportedSoc : Real = socState;
        out attribute reportedCoreTemperature_C : Real = coreTemperatureState_C;
        out attribute reportedSurfaceTemperature_C : Real = surfaceTemperatureState_C;

        bind batteryPort.voltage_V = packVoltage_V;
        bind batteryPort.soc = reportedSoc;
        bind batteryPort.coreTemperature_C = reportedCoreTemperature_C;
        bind batteryPort.surfaceTemperature_C = reportedSurfaceTemperature_C;
        bind batteryPort.heatGeneration_W = generatedHeat_W;

        assert constraint socRange : SocRangeConstraint {
            in soc = batteryPort.soc;
        }
    }

    part def CoolingLoop {
        port coolingPort : CoolingLoopPort;

        attribute maxCoolantFlow_kgps : Real = 0.50;
        attribute uaMin_WpK : Real = 50.0;
        attribute uaMax_WpK : Real = 400.0;
        attribute pumpPowerMax_W : Real = 300.0;

        out attribute coolantFlowCommanded_kgps : Real =
            CoolantFlowFromPump(
                coolingPort.pumpCommand,
                maxCoolantFlow_kgps
            );

        out attribute effectiveUA_WpK : Real =
            UAFromFan(
                coolingPort.fanCommand,
                uaMin_WpK,
                uaMax_WpK
            );

        out attribute coolantInletTemperatureComputed_C : Real =
            CoolantInletTemperature(
                coolingPort.ambientTemperature_C,
                coolingPort.batterySurfaceTemperature_C,
                coolingPort.heatLoad_W,
                effectiveUA_WpK
            );

        out attribute radiatorOutletTemperatureComputed_C : Real =
            RadiatorOutletTemperature(
                coolantInletTemperatureComputed_C,
                coolingPort.ambientTemperature_C,
                coolingPort.fanCommand
            );

        out attribute pumpElectricalPower_W : Real =
            PumpPower(
                coolingPort.pumpCommand,
                pumpPowerMax_W
            );

        bind coolingPort.coolantFlow_kgps = coolantFlowCommanded_kgps;
        bind coolingPort.coolantInletTemperature_C = coolantInletTemperatureComputed_C;
        bind coolingPort.radiatorOutletTemperature_C = radiatorOutletTemperatureComputed_C;
        bind coolingPort.pumpPower_W = pumpElectricalPower_W;

        assert constraint pumpCmdRange : UnitIntervalConstraint {
            in x = coolingPort.pumpCommand;
        }

        assert constraint fanCmdRange : UnitIntervalConstraint {
            in x = coolingPort.fanCommand;
        }
    }

    //-----------------------------
    // System definition
    //-----------------------------

    part def EVBatteryThermalManagementSubsystem {
        part controller : ThermalManagementController;
        part battery : BatteryPackElectroThermal;
        part coolingLoop : CoolingLoop;

        attribute ambientTemperature_C : Real;
        attribute driverPowerRequest_W : Real;

        bind controller.controllerPort.ambientTemperature_C = ambientTemperature_C;
        bind battery.batteryPort.ambientTemperature_C = ambientTemperature_C;
        bind coolingLoop.coolingPort.ambientTemperature_C = ambientTemperature_C;

        bind controller.controllerPort.driverPowerRequest_W = driverPowerRequest_W;

        interface connect controllerToBattery : ControllerBatteryInterface
            connect controller.controllerPort to battery.batteryPort;

        interface connect controllerToCooling : ControllerCoolingInterface
            connect controller.controllerPort to coolingLoop.coolingPort;

        interface connect batteryToCooling : BatteryCoolingInterface
            connect battery.batteryPort to coolingLoop.coolingPort;

        assert constraint socValid : SocRangeConstraint {
            in soc = battery.batteryPort.soc;
        }

        assert constraint controllerPumpRange : UnitIntervalConstraint {
            in x = controller.controllerPort.pumpCommand;
        }

        assert constraint controllerFanRange : UnitIntervalConstraint {
            in x = controller.controllerPort.fanCommand;
        }
    }

    //-----------------------------
    // Example usage
    //-----------------------------

    part vehicleThermalSubsystem : EVBatteryThermalManagementSubsystem {
        attribute ambientTemperature_C = 35.0;
        attribute driverPowerRequest_W = 80000.0;
    }
}