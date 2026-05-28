#!/usr/bin/env python3
"""
Generate PositionController FMU (FMI 2.0 Co-Simulation)

Hydraulic axis position controller with:
- PI control with deadband
- Velocity feedback damping
- Saturation with anti-windup (back-calculation)
- 1 continuous state: integrator state
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "PositionController"
GUID = "{b2c3d4e5-f6a7-8901-bcde-f23456789012}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T07:35:00Z"
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
  
  <DefaultExperiment startTime="0" stopTime="10" stepSize="0.001"/>
  
  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="x_ref_m" valueReference="0" causality="input" variability="continuous">
      <Real unit="m" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="x_meas_m" valueReference="1" causality="input" variability="continuous">
      <Real unit="m" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="v_meas_mps" valueReference="2" causality="input" variability="continuous">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="enable" valueReference="3" causality="input" variability="continuous">
      <Boolean start="true"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="valve_cmd" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="-"/>
    </ScalarVariable>
    <ScalarVariable name="sat_flag" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Boolean/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="i_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="-" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="Kp" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="1/s" start="18.0"/>
    </ScalarVariable>
    <ScalarVariable name="Ki" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="1/s^2" start="35.0"/>
    </ScalarVariable>
    <ScalarVariable name="Kv" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="s/m" start="3.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_min" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="-" start="-1.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_max" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="-" start="1.0"/>
    </ScalarVariable>
    <ScalarVariable name="integrator_limit" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="-" start="0.5"/>
    </ScalarVariable>
    <ScalarVariable name="aw_gain" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="1/s" start="8.0"/>
    </ScalarVariable>
    <ScalarVariable name="deadband_m" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="m" start="0.0002"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </Outputs>
    <Derivatives>
      <Unknown index="7" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
PositionController FMU Model Implementation
FMI 2.0 Co-Simulation

Hydraulic axis position controller with:
- PI control with deadband
- Velocity feedback damping
- Saturation with anti-windup (back-calculation)
- 1 continuous state: integrator state

Control law:
  e = x_ref - x_meas
  e_db = deadband(e, d)
  u_raw = Kp * e_db + Ki * i - Kv * v_meas
  u = clip(u_raw, u_min, u_max)
  di/dt = e_db + aw_gain * (u - u_raw)  (anti-windup)
"""

import math


def clip(x, lo, hi):
    """Clamp value between bounds"""
    return max(lo, min(hi, x))


def sign(x):
    """Sign function with zero case"""
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0


def deadband(e, d):
    """Apply deadband to error to reduce chatter"""
    if abs(e) <= d:
        return 0.0
    return e - d * sign(e)


class PositionController:
    """PI Position Controller with Velocity Damping and Anti-Windup"""
    
    def __init__(self):
        # Controller parameters (defaults from spec)
        self.Kp = 18.0            # Proportional gain
        self.Ki = 35.0            # Integral gain
        self.Kv = 3.0             # Velocity feedback gain (damping)
        self.u_min = -1.0         # Minimum command
        self.u_max = 1.0          # Maximum command
        self.integrator_limit = 0.5  # Integrator clamp
        self.aw_gain = 8.0        # Anti-windup gain
        self.deadband_m = 0.0002  # Error deadband
        
        # State variable (integrator)
        self.i_state = 0.0
        
        # Inputs
        self.x_ref_m = 0.05       # Position reference
        self.x_meas_m = 0.05      # Measured position
        self.v_meas_mps = 0.0     # Measured velocity
        self.enable = True        # Enable control
        
        # Outputs
        self.valve_cmd = 0.0
        self.sat_flag = False
        
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
            # Inputs
            if v == 0: values.append(self.x_ref_m)
            elif v == 1: values.append(self.x_meas_m)
            elif v == 2: values.append(self.v_meas_mps)
            # Outputs
            elif v == 10: values.append(self.valve_cmd)
            # States
            elif v == 20: values.append(self.i_state)
            # Parameters
            elif v == 100: values.append(self.Kp)
            elif v == 101: values.append(self.Ki)
            elif v == 102: values.append(self.Kv)
            elif v == 103: values.append(self.u_min)
            elif v == 104: values.append(self.u_max)
            elif v == 105: values.append(self.integrator_limit)
            elif v == 106: values.append(self.aw_gain)
            elif v == 107: values.append(self.deadband_m)
            else: values.append(0.0)
        return values
    
    def get_boolean(self, vr):
        """Get boolean values by value references"""
        values = []
        for v in vr:
            if v == 3: values.append(self.enable)
            elif v == 11: values.append(self.sat_flag)
            else: values.append(False)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.x_ref_m = val
            elif v == 1: self.x_meas_m = val
            elif v == 2: self.v_meas_mps = val
            # States
            elif v == 20: self.i_state = val
            # Parameters
            elif v == 100: self.Kp = val
            elif v == 101: self.Ki = val
            elif v == 102: self.Kv = val
            elif v == 103: self.u_min = val
            elif v == 104: self.u_max = val
            elif v == 105: self.integrator_limit = val
            elif v == 106: self.aw_gain = val
            elif v == 107: self.deadband_m = val
    
    def set_boolean(self, vr, values):
        """Set boolean values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            if v == 3: self.enable = val
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        if not self.enable:
            self.valve_cmd = 0.0
            self.sat_flag = False
            return
        
        # Error with deadband
        e = self.x_ref_m - self.x_meas_m
        e_db = deadband(e, self.deadband_m)
        
        # Control law
        u_raw = self.Kp * e_db + self.Ki * self.i_state - self.Kv * self.v_meas_mps
        
        # Saturation
        u = clip(u_raw, self.u_min, self.u_max)
        
        # Saturation flag
        self.sat_flag = (abs(u - u_raw) > 1e-12)
        self.valve_cmd = u
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Uses explicit Euler integration for integrator state.
        Implements PI control with anti-windup.
        """
        dt = communication_step_size
        
        if not self.enable:
            # Disabled: zero output, drain integrator
            self.valve_cmd = 0.0
            self.sat_flag = False
            # Drain integrator back to zero
            di = -2.0 * self.i_state
            self.i_state = clip(self.i_state + di * dt, -self.integrator_limit, self.integrator_limit)
            self.time = current_time + dt
            return 0
        
        # Error with deadband
        e = self.x_ref_m - self.x_meas_m
        e_db = deadband(e, self.deadband_m)
        
        # Control law (raw)
        u_raw = self.Kp * e_db + self.Ki * self.i_state - self.Kv * self.v_meas_mps
        
        # Saturation
        u = clip(u_raw, self.u_min, self.u_max)
        
        # Anti-windup: integrator derivative includes back-calculation
        di = e_db + self.aw_gain * (u - u_raw)
        
        # Update integrator state with clamp
        self.i_state = clip(self.i_state + di * dt, -self.integrator_limit, self.integrator_limit)
        
        # Outputs
        self.valve_cmd = u
        self.sat_flag = (abs(u - u_raw) > 1e-12)
        
        self.time = current_time + dt
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = PositionController()
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


def get_boolean(fmi_instance, vr, nvr, value):
    values = fmi_instance.get_boolean(vr[:nvr])
    for i, v in enumerate(values):
        value[i] = v
    return 0


def set_boolean(fmi_instance, vr, nvr, value):
    fmi_instance.set_boolean(vr[:nvr], list(value[:nvr]))
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
    'fmi2GetBoolean': get_boolean,
    'fmi2SetBoolean': set_boolean,
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