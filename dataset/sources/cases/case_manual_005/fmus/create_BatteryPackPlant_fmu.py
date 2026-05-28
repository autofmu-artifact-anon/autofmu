#!/usr/bin/env python3
"""
Generate BatteryPackPlant FMU (FMI 2.0 Co-Simulation)

Battery pack electro-thermal coupled model with:
- 2 continuous states: SOC, T_cell
- Nonlinear OCV(SOC) polynomial
- Temperature/SOC-dependent internal resistance
- Heat generation with I^2R and polarization losses
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "BatteryPackPlant"
GUID = "{b1c2d3e4-f5a6-7890-bcde-f12345678901}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T09:04:00Z"
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
    <ScalarVariable name="i_load_A" valueReference="0" causality="input" variability="continuous">
      <Real unit="A" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_in_temp_C" valueReference="1" causality="input" variability="continuous">
      <Real unit="C" start="25.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="v_term_V" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="V"/>
    </ScalarVariable>
    <ScalarVariable name="soc" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="-"/>
    </ScalarVariable>
    <ScalarVariable name="temp_cell_C" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="C"/>
    </ScalarVariable>
    <ScalarVariable name="heat_gen_W" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="W"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="soc_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="-" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="temp_cell_C_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="C" start="25.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Cell configuration -->
    <ScalarVariable name="n_series" valueReference="100" causality="parameter" variability="fixed">
      <Integer start="96"/>
    </ScalarVariable>
    <ScalarVariable name="capacity_Ah" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="Ah" start="50.0"/>
    </ScalarVariable>
    <ScalarVariable name="coulombic_eff" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="-" start="0.995"/>
    </ScalarVariable>
    
    <!-- Parameters - SOC limits -->
    <ScalarVariable name="soc_min" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="-" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="soc_max" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="-" start="0.98"/>
    </ScalarVariable>
    
    <!-- Parameters - OCV polynomial coefficients -->
    <ScalarVariable name="ocv_a0_V" valueReference="120" causality="parameter" variability="fixed">
      <Real unit="V" start="3.20"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_a1_V" valueReference="121" causality="parameter" variability="fixed">
      <Real unit="V" start="0.90"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_a2_V" valueReference="122" causality="parameter" variability="fixed">
      <Real unit="V" start="-0.60"/>
    </ScalarVariable>
    <ScalarVariable name="ocv_a3_V" valueReference="123" causality="parameter" variability="fixed">
      <Real unit="V" start="0.35"/>
    </ScalarVariable>
    
    <!-- Parameters - Internal resistance -->
    <ScalarVariable name="r0_Ohm" valueReference="130" causality="parameter" variability="fixed">
      <Real unit="Ohm" start="0.0020"/>
    </ScalarVariable>
    <ScalarVariable name="r_soc_gain" valueReference="131" causality="parameter" variability="fixed">
      <Real unit="-" start="1.2"/>
    </ScalarVariable>
    <ScalarVariable name="r_temp_beta" valueReference="132" causality="parameter" variability="fixed">
      <Real unit="1/C" start="0.035"/>
    </ScalarVariable>
    
    <!-- Parameters - Polarization -->
    <ScalarVariable name="k_pol_V" valueReference="140" causality="parameter" variability="fixed">
      <Real unit="V" start="0.010"/>
    </ScalarVariable>
    
    <!-- Parameters - Thermal -->
    <ScalarVariable name="thermal_mass_JK" valueReference="150" causality="parameter" variability="fixed">
      <Real unit="J/K" start="65000.0"/>
    </ScalarVariable>
    <ScalarVariable name="h_cool_WK" valueReference="151" causality="parameter" variability="fixed">
      <Real unit="W/K" start="120.0"/>
    </ScalarVariable>
    <ScalarVariable name="temp_min_C" valueReference="152" causality="parameter" variability="fixed">
      <Real unit="C" start="-10.0"/>
    </ScalarVariable>
    <ScalarVariable name="temp_max_C" valueReference="153" causality="parameter" variability="fixed">
      <Real unit="C" start="80.0"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </Outputs>
    <Derivatives>
      <Unknown index="7" dependencies=""/>
      <Unknown index="8" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
BatteryPackPlant FMU Model Implementation
FMI 2.0 Co-Simulation

Battery pack electro-thermal coupled model with:
- 2 continuous states: SOC, T_cell
- Nonlinear OCV(SOC) polynomial
- Temperature/SOC-dependent internal resistance (Arrhenius-like)
- Heat generation with I^2R and polarization losses

Physics:
- OCV(SOC) = a0 + a1*z + a2*z^2 + a3*z^3
- R(T,SOC) = r0 * (1 + r_soc_gain*(1-z)^2) * exp(-beta*(T-25))
- dz/dt = -I / (3600 * C_Ah)
- dT/dt = (Q_gen - h_cool*(T - T_cool)) / C_th
"""

import math


def clip(x, lo, hi):
    """Clamp value between bounds"""
    return max(lo, min(hi, x))


class BatteryPackPlant:
    """Battery Pack Electro-Thermal Model"""
    
    def __init__(self):
        # Physical parameters (defaults from spec)
        # Cell configuration
        self.n_series = 96
        self.capacity_Ah = 50.0
        self.coulombic_eff = 0.995
        
        # SOC limits
        self.soc_min = 0.05
        self.soc_max = 0.98
        
        # OCV polynomial coefficients
        self.ocv_a0_V = 3.20
        self.ocv_a1_V = 0.90
        self.ocv_a2_V = -0.60
        self.ocv_a3_V = 0.35
        
        # Internal resistance parameters
        self.r0_Ohm = 0.0020
        self.r_soc_gain = 1.2
        self.r_temp_beta = 0.035
        
        # Polarization coefficient
        self.k_pol_V = 0.010
        
        # Thermal parameters
        self.thermal_mass_JK = 65000.0
        self.h_cool_WK = 120.0
        self.temp_min_C = -10.0
        self.temp_max_C = 80.0
        
        # State variables
        self.soc = 0.8           # SOC (0..1)
        self.temp_cell_C = 25.0  # Cell temperature (C)
        
        # Inputs
        self.i_load_A = 0.0
        self.coolant_in_temp_C = 25.0
        
        # Outputs
        self.v_term_V = 0.0
        self.heat_gen_W = 0.0
        
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
    
    def get_integer(self, vr):
        """Get integer values by value references"""
        values = []
        for v in vr:
            if v == 100: values.append(self.n_series)
            else: values.append(0)
        return values
    
    def set_integer(self, vr, values):
        """Set integer values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 100: self.n_series = val
    
    def get_real(self, vr):
        """Get real values by value references"""
        values = []
        for v in vr:
            # Inputs
            if v == 0: values.append(self.i_load_A)
            elif v == 1: values.append(self.coolant_in_temp_C)
            # Outputs
            elif v == 10: values.append(self.v_term_V)
            elif v == 11: values.append(self.soc)
            elif v == 12: values.append(self.temp_cell_C)
            elif v == 13: values.append(self.heat_gen_W)
            # States
            elif v == 20: values.append(self.soc)
            elif v == 21: values.append(self.temp_cell_C)
            # Parameters - Cell configuration
            elif v == 101: values.append(self.capacity_Ah)
            elif v == 102: values.append(self.coulombic_eff)
            # Parameters - SOC limits
            elif v == 110: values.append(self.soc_min)
            elif v == 111: values.append(self.soc_max)
            # Parameters - OCV polynomial
            elif v == 120: values.append(self.ocv_a0_V)
            elif v == 121: values.append(self.ocv_a1_V)
            elif v == 122: values.append(self.ocv_a2_V)
            elif v == 123: values.append(self.ocv_a3_V)
            # Parameters - Internal resistance
            elif v == 130: values.append(self.r0_Ohm)
            elif v == 131: values.append(self.r_soc_gain)
            elif v == 132: values.append(self.r_temp_beta)
            # Parameters - Polarization
            elif v == 140: values.append(self.k_pol_V)
            # Parameters - Thermal
            elif v == 150: values.append(self.thermal_mass_JK)
            elif v == 151: values.append(self.h_cool_WK)
            elif v == 152: values.append(self.temp_min_C)
            elif v == 153: values.append(self.temp_max_C)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.i_load_A = val
            elif v == 1: self.coolant_in_temp_C = val
            # States
            elif v == 20: self.soc = val
            elif v == 21: self.temp_cell_C = val
            # Parameters - Cell configuration
            elif v == 101: self.capacity_Ah = val
            elif v == 102: self.coulombic_eff = val
            # Parameters - SOC limits
            elif v == 110: self.soc_min = val
            elif v == 111: self.soc_max = val
            # Parameters - OCV polynomial
            elif v == 120: self.ocv_a0_V = val
            elif v == 121: self.ocv_a1_V = val
            elif v == 122: self.ocv_a2_V = val
            elif v == 123: self.ocv_a3_V = val
            # Parameters - Internal resistance
            elif v == 130: self.r0_Ohm = val
            elif v == 131: self.r_soc_gain = val
            elif v == 132: self.r_temp_beta = val
            # Parameters - Polarization
            elif v == 140: self.k_pol_V = val
            # Parameters - Thermal
            elif v == 150: self.thermal_mass_JK = val
            elif v == 151: self.h_cool_WK = val
            elif v == 152: self.temp_min_C = val
            elif v == 153: self.temp_max_C = val
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        # Clamped SOC for OCV calculation
        zt = clip(self.soc, self.soc_min, self.soc_max)
        
        # OCV(SOC) - 3rd order polynomial
        ocv = (self.ocv_a0_V + 
               self.ocv_a1_V * zt + 
               self.ocv_a2_V * zt**2 + 
               self.ocv_a3_V * zt**3)
        
        # Internal resistance R(T,SOC)
        R = self.r0_Ohm * (1.0 + self.r_soc_gain * (1.0 - zt)**2) * \
            math.exp(-self.r_temp_beta * (self.temp_cell_C - 25.0))
        
        # Cell voltage with IR drop and polarization
        I = self.i_load_A
        v_cell = ocv - I * R - self.k_pol_V * abs(I)
        
        # Pack voltage (series cells)
        self.v_term_V = self.n_series * max(0.0, v_cell)
        
        # Heat generation (I^2R + polarization)
        self.heat_gen_W = I**2 * R + abs(I) * self.k_pol_V * self.n_series
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Uses forward Euler integration.
        Implements electro-thermal battery dynamics.
        """
        dt = communication_step_size
        
        # Unpack state
        z = self.soc
        T = self.temp_cell_C
        
        # Unpack inputs
        I = self.i_load_A
        Tcool = self.coolant_in_temp_C
        
        # Clamped SOC for calculations
        zt = clip(z, self.soc_min, self.soc_max)
        
        # OCV(SOC) - 3rd order polynomial
        ocv = (self.ocv_a0_V + 
               self.ocv_a1_V * zt + 
               self.ocv_a2_V * zt**2 + 
               self.ocv_a3_V * zt**3)
        
        # Internal resistance R(T,SOC)
        R = self.r0_Ohm * (1.0 + self.r_soc_gain * (1.0 - zt)**2) * \
            math.exp(-self.r_temp_beta * (T - 25.0))
        
        # SOC dynamics: dz/dt = -I / (3600 * C_Ah)
        # Note: I > 0 means discharge (SOC decreases)
        #       I < 0 means charge (SOC increases, with coulombic efficiency)
        if I >= 0:
            # Discharge
            dz = -I / (3600.0 * self.capacity_Ah)
        else:
            # Charge with coulombic efficiency
            dz = -I * self.coulombic_eff / (3600.0 * self.capacity_Ah)
        
        z_new = clip(z + dz * dt, 0.0, 1.0)
        
        # Heat generation: I^2R + |I|*k_pol*n_series
        q_gen = I**2 * R + abs(I) * self.k_pol_V * self.n_series
        
        # Thermal dynamics: dT/dt = (Q_gen - h_cool*(T - T_cool)) / C_th
        dT = (q_gen - self.h_cool_WK * (T - Tcool)) / self.thermal_mass_JK
        T_new = clip(T + dT * dt, self.temp_min_C, self.temp_max_C)
        
        # Update state
        self.soc = z_new
        self.temp_cell_C = T_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = BatteryPackPlant()
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


def get_integer(fmi_instance, vr, nvr, value):
    values = fmi_instance.get_integer(vr[:nvr])
    for i, v in enumerate(values):
        value[i] = v
    return 0


def set_integer(fmi_instance, vr, nvr, value):
    fmi_instance.set_integer(vr[:nvr], list(value[:nvr]))
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
    'fmi2GetInteger': get_integer,
    'fmi2SetInteger': set_integer,
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