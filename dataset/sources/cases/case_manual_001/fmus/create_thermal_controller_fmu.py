#!/usr/bin/env python3
"""
Generate ThermalController FMU (FMI 2.0 Co-Simulation)

Supervisory thermal controller for battery pack with:
- Mode switching with hysteresis (NORMAL/DERATE/SHUTDOWN)
- Current command with protection derating
- Cooling PI control with ambient feedforward
- Integral state for temperature error
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "ThermalController"
GUID = "{a1b2c3d4-e5f6-7890-abcd-ef1234567890}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T01:00:00Z"
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
    <ScalarVariable name="T_core_C" valueReference="0" causality="input" variability="continuous">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="soc" valueReference="1" causality="input" variability="continuous">
      <Real unit="1" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="voltage_V" valueReference="2" causality="input" variability="continuous">
      <Real unit="V" start="360.0"/>
    </ScalarVariable>
    <ScalarVariable name="driver_power_request_W" valueReference="3" causality="input" variability="continuous">
      <Real unit="W" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="ambient_temp_C" valueReference="4" causality="input" variability="continuous">
      <Real unit="degC" start="25.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="current_A" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="A"/>
    </ScalarVariable>
    <ScalarVariable name="pump_cmd" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="0..1"/>
    </ScalarVariable>
    <ScalarVariable name="fan_cmd" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="0..1"/>
    </ScalarVariable>
    <ScalarVariable name="mode" valueReference="13" causality="output" variability="discrete" initial="calculated">
      <Integer/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="integral_err" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="1" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="mode_state" valueReference="21" causality="local" variability="discrete" initial="exact">
      <Integer start="0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="T_set_C" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="degC" start="45.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_derate_on_C" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="degC" start="50.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_derate_off_C" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="degC" start="47.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_shutdown_on_C" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="degC" start="58.0"/>
    </ScalarVariable>
    <ScalarVariable name="T_shutdown_off_C" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="degC" start="52.0"/>
    </ScalarVariable>
    <ScalarVariable name="I_max_A" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="A" start="350.0"/>
    </ScalarVariable>
    <ScalarVariable name="I_min_A" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="A" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="soc_min" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="1" start="0.2"/>
    </ScalarVariable>
    <ScalarVariable name="V_min_V" valueReference="108" causality="parameter" variability="fixed">
      <Real unit="V" start="280.0"/>
    </ScalarVariable>
    <ScalarVariable name="kP_current" valueReference="109" causality="parameter" variability="fixed">
      <Real unit="A/W" start="0.9"/>
    </ScalarVariable>
    <ScalarVariable name="kP_cool" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="1/degC" start="0.06"/>
    </ScalarVariable>
    <ScalarVariable name="kI_cool" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="1/(degC*s)" start="0.0015"/>
    </ScalarVariable>
    <ScalarVariable name="int_clamp" valueReference="112" causality="parameter" variability="fixed">
      <Real unit="1" start="0.6"/>
    </ScalarVariable>
    <ScalarVariable name="ambient_ff_gain" valueReference="113" causality="parameter" variability="fixed">
      <Real unit="1/degC" start="0.01"/>
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
      <Unknown index="10" dependencies=""/>
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
ThermalController FMU Model Implementation
FMI 2.0 Co-Simulation

Supervisory thermal controller for battery pack:
- Mode switching with hysteresis (NORMAL/DERATE/SHUTDOWN)
- Current command with protection derating (SOC, voltage, temperature)
- Cooling PI control with ambient feedforward
- Integral state for temperature error
"""

import numpy as np


class ThermalController:
    """Thermal Controller Model"""
    
    def __init__(self):
        # Default parameters (will be overridden by FMU parameters)
        self.T_set_C = 45.0
        self.T_derate_on_C = 50.0
        self.T_derate_off_C = 47.0
        self.T_shutdown_on_C = 58.0
        self.T_shutdown_off_C = 52.0
        self.I_max_A = 350.0
        self.I_min_A = 0.0
        self.soc_min = 0.2
        self.V_min_V = 280.0
        self.kP_current = 0.9
        self.kP_cool = 0.06
        self.kI_cool = 0.0015
        self.int_clamp = 0.6
        self.ambient_ff_gain = 0.01
        
        # State variables
        self.integral_err = 0.0
        self.mode_state = 0  # 0=NORMAL, 1=DERATE, 2=SHUTDOWN
        
        # Inputs
        self.T_core_C = 25.0
        self.soc = 0.8
        self.voltage_V = 360.0
        self.driver_power_request_W = 0.0
        self.ambient_temp_C = 25.0
        
        # Outputs
        self.current_A = 0.0
        self.pump_cmd = 0.0
        self.fan_cmd = 0.0
        self.mode = 0
        
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
            if v == 0: values.append(self.T_core_C)
            elif v == 1: values.append(self.soc)
            elif v == 2: values.append(self.voltage_V)
            elif v == 3: values.append(self.driver_power_request_W)
            elif v == 4: values.append(self.ambient_temp_C)
            elif v == 10: values.append(self.current_A)
            elif v == 11: values.append(self.pump_cmd)
            elif v == 12: values.append(self.fan_cmd)
            elif v == 20: values.append(self.integral_err)
            # Parameters
            elif v == 100: values.append(self.T_set_C)
            elif v == 101: values.append(self.T_derate_on_C)
            elif v == 102: values.append(self.T_derate_off_C)
            elif v == 103: values.append(self.T_shutdown_on_C)
            elif v == 104: values.append(self.T_shutdown_off_C)
            elif v == 105: values.append(self.I_max_A)
            elif v == 106: values.append(self.I_min_A)
            elif v == 107: values.append(self.soc_min)
            elif v == 108: values.append(self.V_min_V)
            elif v == 109: values.append(self.kP_current)
            elif v == 110: values.append(self.kP_cool)
            elif v == 111: values.append(self.kI_cool)
            elif v == 112: values.append(self.int_clamp)
            elif v == 113: values.append(self.ambient_ff_gain)
            else: values.append(0.0)
        return values
    
    def get_integer(self, vr):
        """Get integer values by value references"""
        values = []
        for v in vr:
            if v == 13: values.append(self.mode)
            elif v == 21: values.append(self.mode_state)
            else: values.append(0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 0: self.T_core_C = val
            elif v == 1: self.soc = val
            elif v == 2: self.voltage_V = val
            elif v == 3: self.driver_power_request_W = val
            elif v == 4: self.ambient_temp_C = val
            elif v == 20: self.integral_err = val
            # Parameters
            elif v == 100: self.T_set_C = val
            elif v == 101: self.T_derate_on_C = val
            elif v == 102: self.T_derate_off_C = val
            elif v == 103: self.T_shutdown_on_C = val
            elif v == 104: self.T_shutdown_off_C = val
            elif v == 105: self.I_max_A = val
            elif v == 106: self.I_min_A = val
            elif v == 107: self.soc_min = val
            elif v == 108: self.V_min_V = val
            elif v == 109: self.kP_current = val
            elif v == 110: self.kP_cool = val
            elif v == 111: self.kI_cool = val
            elif v == 112: self.int_clamp = val
            elif v == 113: self.ambient_ff_gain = val
    
    def set_integer(self, vr, values):
        """Set integer values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 21: self.mode_state = val
    
    def _clip(self, x, lo, hi):
        """Clip value to range [lo, hi]"""
        return max(lo, min(hi, x))
    
    def _compute_outputs(self):
        """Compute output values from current state and inputs"""
        # Get parameters
        p = {
            'T_set_C': self.T_set_C,
            'T_derate_on_C': self.T_derate_on_C,
            'T_derate_off_C': self.T_derate_off_C,
            'T_shutdown_on_C': self.T_shutdown_on_C,
            'T_shutdown_off_C': self.T_shutdown_off_C,
            'I_max_A': self.I_max_A,
            'I_min_A': self.I_min_A,
            'soc_min': self.soc_min,
            'V_min_V': self.V_min_V,
            'kP_current': self.kP_current,
            'kP_cool': self.kP_cool,
            'kI_cool': self.kI_cool,
            'int_clamp': self.int_clamp,
            'ambient_ff_gain': self.ambient_ff_gain,
        }
        
        # Get inputs
        T = self.T_core_C
        soc = self.soc
        V = self.voltage_V
        P_req = max(0.0, self.driver_power_request_W)
        Tamb = self.ambient_temp_C
        
        I_e = self.integral_err
        mode = self.mode_state
        
        # 1) Mode switching with hysteresis
        if mode != 2 and T >= p['T_shutdown_on_C']:
            mode = 2
        elif mode == 2 and T <= p['T_shutdown_off_C']:
            mode = 1
        elif mode == 0 and T >= p['T_derate_on_C']:
            mode = 1
        elif mode == 1 and T <= p['T_derate_off_C']:
            mode = 0
        
        # SOC/Voltage protection
        if soc <= p['soc_min'] or V <= p['V_min_V']:
            mode = max(mode, 1)  # at least DERATE
        
        # 2) Cooling PI + feedforward
        e = T - p['T_set_C']
        u_cool = p['kP_cool'] * e + p['kI_cool'] * I_e + p['ambient_ff_gain'] * (Tamb - 25.0)
        u_cool = self._clip(u_cool, 0.0, 1.0)
        
        if mode == 2:
            pump_cmd = 1.0
            fan_cmd = 1.0
        else:
            pump_cmd = u_cool
            fan_cmd = self._clip(u_cool ** 1.4, 0.0, 1.0)
        
        # 3) Current command with derating
        I_base = p['kP_current'] * (P_req / max(V, p['V_min_V']))
        
        if mode == 0:
            alpha = 1.0
        elif mode == 1:
            alpha_T = self._clip(1.0 - (T - p['T_derate_on_C']) / (p['T_shutdown_on_C'] - p['T_derate_on_C']), 0.0, 1.0)
            alpha_soc = self._clip((soc - p['soc_min']) / 0.1, 0.0, 1.0)
            alpha = min(alpha_T, alpha_soc)
        else:
            alpha = 0.0
        
        I_cmd = self._clip(alpha * I_base, p['I_min_A'], p['I_max_A'])
        
        # Set outputs
        self.mode = mode
        self.pump_cmd = pump_cmd
        self.fan_cmd = fan_cmd
        self.current_A = I_cmd
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        # Get current inputs
        T = self.T_core_C
        soc = self.soc
        V = self.voltage_V
        
        # Temperature error integral
        e = T - self.T_set_C
        dI_e = e
        I_e_new = self._clip(self.integral_err + dI_e * dt, -self.int_clamp, self.int_clamp)
        
        # Update state
        self.integral_err = I_e_new
        self.time = current_time + dt
        
        # Compute outputs (mode switching happens here)
        self._compute_outputs()
        
        # Update mode state
        self.mode_state = self.mode
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = ThermalController()
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


def get_integer(fmi_instance, vr, nvr, value):
    values = fmi_instance.get_integer(vr[:nvr])
    for i, v in enumerate(values):
        value[i] = v
    return 0


def set_real(fmi_instance, vr, nvr, value):
    fmi_instance.set_real(vr[:nvr], list(value[:nvr]))
    return 0


def set_integer(fmi_instance, vr, nvr, value):
    fmi_instance.set_integer(vr[:nvr], list(value[:nvr]))
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
    'fmi2GetInteger': get_integer,
    'fmi2SetInteger': set_integer,
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