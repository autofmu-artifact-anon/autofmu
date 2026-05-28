#!/usr/bin/env python3
"""
Generate BatteryPackElectroThermal FMU (FMI 2.0 Co-Simulation)
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "BatteryPackElectroThermal"
GUID = "{8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T00:00:00Z"
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
    <ScalarVariable name="current_A" valueReference="0" causality="input" variability="continuous">
      <Real unit="A" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_in_temp_C" valueReference="1" causality="input" variability="continuous">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_flow_kgps" valueReference="2" causality="input" variability="continuous">
      <Real unit="kg/s" start="0.12"/>
    </ScalarVariable>
    <ScalarVariable name="ambient_temp_C" valueReference="3" causality="input" variability="continuous">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="voltage_V" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="V"/>
    </ScalarVariable>
    <ScalarVariable name="soc" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="1"/>
    </ScalarVariable>
    <ScalarVariable name="T_core_C" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="degC"/>
    </ScalarVariable>
    <ScalarVariable name="T_surface_C" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="degC"/>
    </ScalarVariable>
    <ScalarVariable name="heat_W" valueReference="14" causality="output" variability="continuous" initial="calculated">
      <Real unit="W"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="soc_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="1" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="T_core_C_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_surface_C_state" valueReference="22" causality="local" variability="continuous" initial="exact">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="capacity_Ah" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="Ah" start="60.0"/>
    </ScalarVariable>
    <ScalarVariable name="V_nom_V" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="V" start="360.0"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_poly_coeff_a0" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="V" start="320.0"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_poly_coeff_a1" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="V" start="120.0"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_poly_coeff_a2" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="V" start="-80.0"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_poly_coeff_a3" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="V" start="40.0"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_poly_coeff_a4" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="V" start="-10.0"/>
    </ScalarVariable>
    <ScalarVariable name="R0_ohm" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="ohm" start="0.06"/>
    </ScalarVariable>
    <ScalarVariable name="R_soc_gain" valueReference="108" causality="parameter" variability="fixed">
      <Real unit="1" start="0.35"/>
    </ScalarVariable>
    <ScalarVariable name="R_temp_coeff_perC" valueReference="109" causality="parameter" variability="fixed">
      <Real unit="1/degC" start="-0.01"/>
    </ScalarVariable>
    <ScalarVariable name="T_ref_C" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="I_max_discharge_A" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="A" start="350.0"/>
    </ScalarVariable>
    <ScalarVariable name="I_max_charge_A" valueReference="112" causality="parameter" variability="fixed">
      <Real unit="A" start="200.0"/>
    </ScalarVariable>
    <ScalarVariable name="m_core_kg" valueReference="113" causality="parameter" variability="fixed">
      <Real unit="kg" start="120.0"/>
    </ScalarVariable>
    <ScalarVariable name="cp_core_JpkgK" valueReference="114" causality="parameter" variability="fixed">
      <Real unit="J/(kg*K)" start="950.0"/>
    </ScalarVariable>
    <ScalarVariable name="m_surface_kg" valueReference="115" causality="parameter" variability="fixed">
      <Real unit="kg" start="30.0"/>
    </ScalarVariable>
    <ScalarVariable name="cp_surface_JpkgK" valueReference="116" causality="parameter" variability="fixed">
      <Real unit="J/(kg*K)" start="900.0"/>
    </ScalarVariable>
    <ScalarVariable name="R_core_to_surface_KpW" valueReference="117" causality="parameter" variability="fixed">
      <Real unit="K/W" start="0.08"/>
    </ScalarVariable>
    <ScalarVariable name="hA_ambient_WpK" valueReference="118" causality="parameter" variability="fixed">
      <Real unit="W/K" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_cp_JpkgK" valueReference="119" causality="parameter" variability="fixed">
      <Real unit="J/(kg*K)" start="3800.0"/>
    </ScalarVariable>
    <ScalarVariable name="hA_coolant_base_WpK" valueReference="120" causality="parameter" variability="fixed">
      <Real unit="W/K" start="60.0"/>
    </ScalarVariable>
    <ScalarVariable name="flow_nom_kgps" valueReference="121" causality="parameter" variability="fixed">
      <Real unit="kg/s" start="0.12"/>
    </ScalarVariable>
    <ScalarVariable name="dUdT_VpK" valueReference="122" causality="parameter" variability="fixed">
      <Real unit="V/K" start="0.06"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
      <Unknown index="9"/>
      <Unknown index="10"/>
    </Outputs>
    <Derivatives>
      <Unknown index="11" dependencies=""/>
      <Unknown index="12" dependencies=""/>
      <Unknown index="13" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
      <Unknown index="9"/>
      <Unknown index="10"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
BatteryPackElectroThermal FMU Model Implementation
FMI 2.0 Co-Simulation

Electro-thermal coupled battery pack model with:
- Nonlinear OCV(SOC) polynomial
- Temperature and SOC dependent internal resistance
- Two-node thermal model (core/surface)
- Flow-dependent cooling conductance
- Current saturation and SOC clamping
"""

import numpy as np


class BatteryPackElectroThermal:
    """Battery Pack Electro-Thermal Model"""
    
    def __init__(self):
        # Default parameters (will be overridden by FMU parameters)
        self.capacity_Ah = 60.0
        self.V_nom_V = 360.0
        self.ocv_poly_coeff = [320.0, 120.0, -80.0, 40.0, -10.0]
        self.R0_ohm = 0.06
        self.R_soc_gain = 0.35
        self.R_temp_coeff_perC = -0.01
        self.T_ref_C = 25.0
        self.I_max_discharge_A = 350.0
        self.I_max_charge_A = 200.0
        self.m_core_kg = 120.0
        self.cp_core_JpkgK = 950.0
        self.m_surface_kg = 30.0
        self.cp_surface_JpkgK = 900.0
        self.R_core_to_surface_KpW = 0.08
        self.hA_ambient_WpK = 25.0
        self.coolant_cp_JpkgK = 3800.0
        self.hA_coolant_base_WpK = 60.0
        self.flow_nom_kgps = 0.12
        self.dUdT_VpK = 0.06
        
        # State variables
        self.soc = 0.8
        self.T_core_C = 25.0
        self.T_surface_C = 25.0
        
        # Inputs
        self.current_A = 0.0
        self.coolant_in_temp_C = 25.0
        self.coolant_flow_kgps = 0.12
        self.ambient_temp_C = 25.0
        
        # Outputs
        self.voltage_V = 0.0
        self.heat_W = 0.0
        
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
            if v == 0: values.append(self.current_A)
            elif v == 1: values.append(self.coolant_in_temp_C)
            elif v == 2: values.append(self.coolant_flow_kgps)
            elif v == 3: values.append(self.ambient_temp_C)
            elif v == 10: values.append(self.voltage_V)
            elif v == 11: values.append(self.soc)
            elif v == 12: values.append(self.T_core_C)
            elif v == 13: values.append(self.T_surface_C)
            elif v == 14: values.append(self.heat_W)
            elif v == 20: values.append(self.soc)
            elif v == 21: values.append(self.T_core_C)
            elif v == 22: values.append(self.T_surface_C)
            # Parameters
            elif v == 100: values.append(self.capacity_Ah)
            elif v == 101: values.append(self.V_nom_V)
            elif v == 102: values.append(self.ocv_poly_coeff[0])
            elif v == 103: values.append(self.ocv_poly_coeff[1])
            elif v == 104: values.append(self.ocv_poly_coeff[2])
            elif v == 105: values.append(self.ocv_poly_coeff[3])
            elif v == 106: values.append(self.ocv_poly_coeff[4])
            elif v == 107: values.append(self.R0_ohm)
            elif v == 108: values.append(self.R_soc_gain)
            elif v == 109: values.append(self.R_temp_coeff_perC)
            elif v == 110: values.append(self.T_ref_C)
            elif v == 111: values.append(self.I_max_discharge_A)
            elif v == 112: values.append(self.I_max_charge_A)
            elif v == 113: values.append(self.m_core_kg)
            elif v == 114: values.append(self.cp_core_JpkgK)
            elif v == 115: values.append(self.m_surface_kg)
            elif v == 116: values.append(self.cp_surface_JpkgK)
            elif v == 117: values.append(self.R_core_to_surface_KpW)
            elif v == 118: values.append(self.hA_ambient_WpK)
            elif v == 119: values.append(self.coolant_cp_JpkgK)
            elif v == 120: values.append(self.hA_coolant_base_WpK)
            elif v == 121: values.append(self.flow_nom_kgps)
            elif v == 122: values.append(self.dUdT_VpK)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 0: self.current_A = val
            elif v == 1: self.coolant_in_temp_C = val
            elif v == 2: self.coolant_flow_kgps = val
            elif v == 3: self.ambient_temp_C = val
            elif v == 20: self.soc = val
            elif v == 21: self.T_core_C = val
            elif v == 22: self.T_surface_C = val
            # Parameters
            elif v == 100: self.capacity_Ah = val
            elif v == 101: self.V_nom_V = val
            elif v == 102: self.ocv_poly_coeff[0] = val
            elif v == 103: self.ocv_poly_coeff[1] = val
            elif v == 104: self.ocv_poly_coeff[2] = val
            elif v == 105: self.ocv_poly_coeff[3] = val
            elif v == 106: self.ocv_poly_coeff[4] = val
            elif v == 107: self.R0_ohm = val
            elif v == 108: self.R_soc_gain = val
            elif v == 109: self.R_temp_coeff_perC = val
            elif v == 110: self.T_ref_C = val
            elif v == 111: self.I_max_discharge_A = val
            elif v == 112: self.I_max_charge_A = val
            elif v == 113: self.m_core_kg = val
            elif v == 114: self.cp_core_JpkgK = val
            elif v == 115: self.m_surface_kg = val
            elif v == 116: self.cp_surface_JpkgK = val
            elif v == 117: self.R_core_to_surface_KpW = val
            elif v == 118: self.hA_ambient_WpK = val
            elif v == 119: self.coolant_cp_JpkgK = val
            elif v == 120: self.hA_coolant_base_WpK = val
            elif v == 121: self.flow_nom_kgps = val
            elif v == 122: self.dUdT_VpK = val
    
    def _clip(self, x, lo, hi):
        """Clip value to range [lo, hi]"""
        return max(lo, min(hi, x))
    
    def _poly_ocv(self, z, coeffs):
        """Compute OCV from SOC using polynomial"""
        return coeffs[0] + coeffs[1]*z + coeffs[2]*z**2 + coeffs[3]*z**3 + coeffs[4]*z**4
    
    def _compute_outputs(self):
        """Compute output values from current state and inputs"""
        # Current saturation
        I = self._clip(self.current_A, -self.I_max_charge_A, self.I_max_discharge_A)
        
        # Nonlinear electrical model
        OCV = self._poly_ocv(self.soc, self.ocv_poly_coeff)
        R = self.R0_ohm * (1.0 + self.R_soc_gain * (1.0 - self.soc)**2) * \
            (1.0 + self.R_temp_coeff_perC * (self.T_core_C - self.T_ref_C))
        R = max(R, 0.005)  # Minimum resistance
        
        # Terminal voltage
        self.voltage_V = OCV - I * R
        
        # Heat generation (Joule + entropic)
        Q_joule = (I**2) * R
        Q_entropic = I * self.dUdT_VpK * (self.T_core_C + 273.15)
        self.heat_W = Q_joule + Q_entropic
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        # Get current inputs
        I_cmd = self.current_A
        Tcool = self.coolant_in_temp_C
        mdot = max(0.0, self.coolant_flow_kgps)
        Tamb = self.ambient_temp_C
        
        # State variables
        z = self.soc
        Tcore = self.T_core_C
        Tsurf = self.T_surface_C
        
        # 1) Current saturation
        I = self._clip(I_cmd, -self.I_max_charge_A, self.I_max_discharge_A)
        
        # 2) Nonlinear electrical model
        OCV = self._poly_ocv(z, self.ocv_poly_coeff)
        R = self.R0_ohm * (1.0 + self.R_soc_gain * (1.0 - z)**2) * \
            (1.0 + self.R_temp_coeff_perC * (Tcore - self.T_ref_C))
        R = max(R, 0.005)  # Minimum resistance
        
        V = OCV - I * R
        
        # 3) Heat generation
        Q_joule = (I**2) * R
        Q_entropic = I * self.dUdT_VpK * (Tcore + 273.15)
        Q = Q_joule + Q_entropic
        
        # 4) Cooling conductance vs flow (nonlinear)
        gamma = 0.6
        if mdot > 0 and self.flow_nom_kgps > 0:
            hA = self.hA_coolant_base_WpK * (mdot / self.flow_nom_kgps)**gamma
        else:
            hA = 0.0
        hA = min(hA, 400.0)  # Upper limit
        
        # 5) Thermal network
        Cc = self.m_core_kg * self.cp_core_JpkgK
        Cs = self.m_surface_kg * self.cp_surface_JpkgK
        
        Q_c_to_s = (Tcore - Tsurf) / self.R_core_to_surface_KpW
        Q_s_to_amb = self.hA_ambient_WpK * (Tsurf - Tamb)
        Q_s_to_cool = hA * (Tsurf - Tcool)
        
        dTcore = (Q - Q_c_to_s) / Cc
        dTsurf = (Q_c_to_s - Q_s_to_amb - Q_s_to_cool) / Cs
        
        # 6) SOC dynamics
        if self.capacity_Ah > 0:
            dz = -I / (3600.0 * self.capacity_Ah)
        else:
            dz = 0.0
        
        # Integrate (forward Euler)
        z_new = self._clip(z + dz*dt, 0.0, 1.0)
        Tcore_new = Tcore + dTcore*dt
        Tsurf_new = Tsurf + dTsurf*dt
        
        # Update state
        self.soc = z_new
        self.T_core_C = Tcore_new
        self.T_surface_C = Tsurf_new
        self.time = current_time + dt
        
        # Update outputs
        self.voltage_V = V
        self.heat_W = Q
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = BatteryPackElectroThermal()
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