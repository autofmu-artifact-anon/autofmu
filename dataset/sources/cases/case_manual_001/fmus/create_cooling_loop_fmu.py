#!/usr/bin/env python3
"""
Generate CoolingLoop FMU (FMI 2.0 Co-Simulation)

Simplified liquid cooling loop with pump + radiator + fan.
Produces coolant inlet temperature to battery and flow rate based on commands and heat load.
Includes nonlinear flow and UA characteristics plus actuator dynamics.
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "CoolingLoop"
GUID = "{2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T00:43:00Z"
  variableNamingConvention="structured">
  
  <ModelExchange modelIdentifier="{MODEL_NAME}"/>
  <CoSimulation modelIdentifier="{MODEL_NAME}">
    <SourceFiles>
      <File name="model.py"/>
    </SourceFiles>
  </CoSimulation>
  
  <LogCategories>
    <Category name="logAll"/>
    <Category name="logError"/>
    <Category name="logFmiCall"/>
    <Category name="logEvent"/>
  </LogCategories>
  
  <DefaultExperiment startTime="0" stopTime="3600" stepSize="0.1"/>
  
  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="pump_cmd" valueReference="0" causality="input" variability="continuous">
      <Real unit="1" start="0.5"/>
    </ScalarVariable>
    <ScalarVariable name="fan_cmd" valueReference="1" causality="input" variability="continuous">
      <Real unit="1" start="0.5"/>
    </ScalarVariable>
    <ScalarVariable name="ambient_temp_C" valueReference="2" causality="input" variability="continuous">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_batt_surface_C" valueReference="3" causality="input" variability="continuous">
      <Real unit="degC" start="30.0"/>
    </ScalarVariable>
    <ScalarVariable name="heat_load_W" valueReference="4" causality="input" variability="continuous">
      <Real unit="W" start="1000.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="coolant_in_temp_C" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="degC"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_flow_kgps" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="kg/s"/>
    </ScalarVariable>
    <ScalarVariable name="radiator_out_temp_C" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="degC"/>
    </ScalarVariable>
    <ScalarVariable name="pump_power_W" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="W"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="coolant_temp_C" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="degC" start="35.0"/>
    </ScalarVariable>
    <ScalarVariable name="flow_state_kgps" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="kg/s" start="0.1"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="coolant_mass_kg" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="kg" start="6.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_cp_JpkgK" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="J/(kg*K)" start="3800.0"/>
    </ScalarVariable>
    <ScalarVariable name="flow_max_kgps" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="kg/s" start="0.25"/>
    </ScalarVariable>
    <ScalarVariable name="pump_tau_s" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="s" start="1.5"/>
    </ScalarVariable>
    <ScalarVariable name="UA_base_WpK" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="W/K" start="250.0"/>
    </ScalarVariable>
    <ScalarVariable name="UA_fan_gain" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="W/K" start="600.0"/>
    </ScalarVariable>
    <ScalarVariable name="UA_max_WpK" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="W/K" start="1200.0"/>
    </ScalarVariable>
    <ScalarVariable name="pump_power_max_W" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="W" start="450.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_min_C" valueReference="108" causality="parameter" variability="fixed">
      <Real unit="degC" start="-20.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_max_C" valueReference="109" causality="parameter" variability="fixed">
      <Real unit="degC" start="120.0"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
      <Unknown index="9"/>
    </Outputs>
    <Derivatives>
      <Unknown index="11" dependencies=""/>
      <Unknown index="12" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
      <Unknown index="9"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
CoolingLoop FMU Model Implementation
FMI 2.0 Co-Simulation

Simplified liquid cooling loop with pump + radiator + fan.
Produces coolant inlet temperature to battery and flow rate based on commands and heat load.
Includes nonlinear flow and UA characteristics plus actuator dynamics.

Nonlinearities:
- Flow vs pump command: square relationship (m_dot_cmd = flow_max * u_p^2)
- Radiator UA vs fan command: power law (UA = UA_base + UA_fan_gain * u_f^0.7)
- Radiator effectiveness: exponential form (epsilon = 1 - exp(-UA/(m_dot * cp)))
- Pump power: cubic relationship (P = P_max * u_p^3)
"""

import math


class CoolingLoop:
    """Cooling Loop Model"""
    
    def __init__(self):
        # Default parameters (will be overridden by FMU parameters)
        self.coolant_mass_kg = 6.0
        self.coolant_cp_JpkgK = 3800.0
        self.flow_max_kgps = 0.25
        self.pump_tau_s = 1.5
        self.UA_base_WpK = 250.0
        self.UA_fan_gain = 600.0
        self.UA_max_WpK = 1200.0
        self.pump_power_max_W = 450.0
        self.T_min_C = -20.0
        self.T_max_C = 120.0
        
        # State variables
        self.coolant_temp_C = 35.0
        self.flow_state_kgps = 0.1
        
        # Inputs
        self.pump_cmd = 0.5
        self.fan_cmd = 0.5
        self.ambient_temp_C = 25.0
        self.T_batt_surface_C = 30.0
        self.heat_load_W = 1000.0
        
        # Outputs
        self.coolant_in_temp_C = 35.0
        self.coolant_flow_kgps = 0.1
        self.radiator_out_temp_C = 35.0
        self.pump_power_W = 0.0
        
        # Simulation time
        self.time = 0.0
    
    def set_debug_logging(self, categories, logging_on):
        """FMI function: Set debug logging"""
        pass
    
    def setup_experiment(self, start_time, stop_time=None, tolerance=None):
        """FMI function: Setup experiment"""
        self.time = start_time
    
    def enter_initialization_mode(self):
        """FMI function: Enter initialization mode"""
        pass
    
    def exit_initialization_mode(self):
        """FMI function: Exit initialization mode"""
        self._compute_outputs()
    
    def terminate(self):
        """FMI function: Terminate"""
        pass
    
    def reset(self):
        """FMI function: Reset"""
        self.__init__()
    
    def get_real(self, vr):
        """Get real values by value references"""
        values = []
        for v in vr:
            if v == 0: values.append(self.pump_cmd)
            elif v == 1: values.append(self.fan_cmd)
            elif v == 2: values.append(self.ambient_temp_C)
            elif v == 3: values.append(self.T_batt_surface_C)
            elif v == 4: values.append(self.heat_load_W)
            elif v == 10: values.append(self.coolant_in_temp_C)
            elif v == 11: values.append(self.coolant_flow_kgps)
            elif v == 12: values.append(self.radiator_out_temp_C)
            elif v == 13: values.append(self.pump_power_W)
            elif v == 20: values.append(self.coolant_temp_C)
            elif v == 21: values.append(self.flow_state_kgps)
            # Parameters
            elif v == 100: values.append(self.coolant_mass_kg)
            elif v == 101: values.append(self.coolant_cp_JpkgK)
            elif v == 102: values.append(self.flow_max_kgps)
            elif v == 103: values.append(self.pump_tau_s)
            elif v == 104: values.append(self.UA_base_WpK)
            elif v == 105: values.append(self.UA_fan_gain)
            elif v == 106: values.append(self.UA_max_WpK)
            elif v == 107: values.append(self.pump_power_max_W)
            elif v == 108: values.append(self.T_min_C)
            elif v == 109: values.append(self.T_max_C)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 0: self.pump_cmd = val
            elif v == 1: self.fan_cmd = val
            elif v == 2: self.ambient_temp_C = val
            elif v == 3: self.T_batt_surface_C = val
            elif v == 4: self.heat_load_W = val
            elif v == 20: self.coolant_temp_C = val
            elif v == 21: self.flow_state_kgps = val
            # Parameters
            elif v == 100: self.coolant_mass_kg = val
            elif v == 101: self.coolant_cp_JpkgK = val
            elif v == 102: self.flow_max_kgps = val
            elif v == 103: self.pump_tau_s = val
            elif v == 104: self.UA_base_WpK = val
            elif v == 105: self.UA_fan_gain = val
            elif v == 106: self.UA_max_WpK = val
            elif v == 107: self.pump_power_max_W = val
            elif v == 108: self.T_min_C = val
            elif v == 109: self.T_max_C = val
    
    def _clip(self, x, lo, hi):
        """Clip value to range [lo, hi]"""
        return max(lo, min(hi, x))
    
    def _compute_outputs(self):
        """Compute output values from current state and inputs"""
        # Get current state
        Tcool = self.coolant_temp_C
        mdot = max(0.0, self.flow_state_kgps)
        
        # Compute radiator outlet temperature
        eps_m = 1e-4
        UA = min(self.UA_base_WpK + self.UA_fan_gain * (self._clip(self.fan_cmd, 0.0, 1.0) ** 0.7), self.UA_max_WpK)
        
        if mdot > eps_m:
            eps = 1.0 - math.exp(-UA / (mdot * self.coolant_cp_JpkgK))
        else:
            eps = 1.0 - math.exp(-UA / (eps_m * self.coolant_cp_JpkgK))
        
        T_out = Tcool - eps * (Tcool - self.ambient_temp_C)
        
        # Update outputs
        self.coolant_in_temp_C = T_out
        self.coolant_flow_kgps = mdot
        self.radiator_out_temp_C = T_out
        
        # Pump power
        up = self._clip(self.pump_cmd, 0.0, 1.0)
        self.pump_power_W = self.pump_power_max_W * (up ** 3)
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        # Clip input commands to valid range
        up = self._clip(self.pump_cmd, 0.0, 1.0)
        uf = self._clip(self.fan_cmd, 0.0, 1.0)
        Tamb = self.ambient_temp_C
        Q_in = self.heat_load_W
        
        # State variables
        Tcool = self.coolant_temp_C
        mdot = max(0.0, self.flow_state_kgps)
        
        # 1) Flow actuator dynamics (nonlinear command mapping: square relationship)
        mdot_cmd = self.flow_max_kgps * (up ** 2)
        dmdot = (mdot_cmd - mdot) / self.pump_tau_s
        
        # 2) Radiator UA vs fan (power law: UA = UA_base + UA_fan_gain * u_f^0.7)
        UA = self.UA_base_WpK + self.UA_fan_gain * (uf ** 0.7)
        UA = min(UA, self.UA_max_WpK)
        
        # 3) Coolant thermal dynamics (lumped energy balance)
        C = self.coolant_mass_kg * self.coolant_cp_JpkgK  # Thermal capacitance
        Q_rad = UA * (Tcool - Tamb)  # Heat rejection to ambient
        dT = (Q_in - Q_rad) / C  # Rate of temperature change
        
        # Integrate (forward Euler)
        mdot_new = max(0.0, mdot + dmdot * dt)
        Tcool_new = Tcool + dT * dt
        Tcool_new = self._clip(Tcool_new, self.T_min_C, self.T_max_C)
        
        # 4) Radiator outlet temperature (effectiveness-NTU approximation)
        eps_m = 1e-4  # Small number to avoid division by zero
        eps = 1.0 - math.exp(-UA / (max(mdot_new, eps_m) * self.coolant_cp_JpkgK))
        T_out = Tcool_new - eps * (Tcool_new - Tamb)
        
        # 5) Pump power (cubic relationship)
        P_pump = self.pump_power_max_W * (up ** 3)
        
        # Update state
        self.coolant_temp_C = Tcool_new
        self.flow_state_kgps = mdot_new
        self.time = current_time + dt
        
        # Update outputs
        self.coolant_in_temp_C = T_out
        self.coolant_flow_kgps = mdot_new
        self.radiator_out_temp_C = T_out
        self.pump_power_W = P_pump
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = CoolingLoop()
    return _instance


def setup_experiment(fmi_instance, tolerance_defined, tolerance, start_time, stop_time_defined, stop_time):
    if stop_time_defined:
        fmi_instance.setup_experiment(start_time, stop_time, tolerance if tolerance_defined else None)
    else:
        fmi_instance.setup_experiment(start_time, None, tolerance if tolerance_defined else None)
    return 0


def enter_initialization_mode(fmi_instance):
    return fmi_instance.enter_initialization_mode()


def exit_initialization_mode(fmi_instance):
    return fmi_instance.exit_initialization_mode()


def terminate(fmi_instance):
    fmi_instance.terminate()
    return 0


def reset(fmi_instance):
    fmi_instance.reset()
    return 0


def get_real(fmi_instance, vr, nvr, value):
    values = fmi_instance.get_real(vr[:nvr])
    for i, v in enumerate(values):
        value[i] = v
    return 0


def set_real(fmi_instance, vr, nvr, value):
    fmi_instance.set_real(vr[:nvr], list(value[:nvr]))
    return 0


def do_step(fmi_instance, current_communication_point, communication_step_size, no_set_fmu_state_prior_to_current_point):
    return fmi_instance.do_step(current_communication_point, communication_step_size, no_set_fmu_state_prior_to_current_point)


def free_instance(fmi_instance):
    global _instance
    _instance = None


# FMI 2.0 function table for DLL/SO
FMI2_FUNCTIONS = {
    'fmi2Instantiate': instantiate,
    'fmi2SetupExperiment': setup_experiment,
    'fmi2EnterInitializationMode': enter_initialization_mode,
    'fmi2ExitInitializationMode': exit_initialization_mode,
    'fmi2Terminate': terminate,
    'fmi2Reset': reset,
    'fmi2GetReal': get_real,
    'fmi2SetReal': set_real,
    'fmi2DoStep': do_step,
    'fmi2FreeInstance': free_instance,
}
'''


def create_fmu(output_path):
    """Create FMU package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory structure
        model_dir = Path(tmpdir) / 'sources'
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Write modelDescription.xml
        model_desc_path = Path(tmpdir) / 'modelDescription.xml'
        with open(model_desc_path, 'w', encoding='utf-8') as f:
            f.write(MODEL_DESCRIPTION)
        
        # Write model.py
        model_py_path = model_dir / 'model.py'
        with open(model_py_path, 'w', encoding='utf-8') as f:
            f.write(MODEL_PY)
        
        # Create FMU (ZIP file)
        fmu_path = Path(output_path)
        fmu_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(fmu_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add modelDescription.xml at root
            zf.write(model_desc_path, 'modelDescription.xml')
            
            # Add model.py in sources/
            zf.write(model_py_path, 'sources/model.py')
        
        print(f"Created FMU: {fmu_path}")
        return str(fmu_path)


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    fmu_path = output_dir / f"{MODEL_NAME}.fmu"
    create_fmu(fmu_path)