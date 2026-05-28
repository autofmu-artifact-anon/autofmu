#!/usr/bin/env python3
"""
Generate SpoolValveActuator FMU (FMI 2.0 Co-Simulation)

Spool valve actuator with:
- Deadzone nonlinearity
- First-order dynamics
- Rate limiting
- Saturation

1 continuous state: spool_state
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "SpoolValveActuator"
GUID = "{c3d4e5f6-a789-0123-cdef-345678901234}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T08:35:00Z"
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
    <ScalarVariable name="valve_cmd" valueReference="0" causality="input" variability="continuous">
      <Real unit="-" start="0.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="spool_u" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="-"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="spool_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="-" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="tau_s" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="s" start="0.03"/>
    </ScalarVariable>
    <ScalarVariable name="deadzone" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="-" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="rate_limit_per_s" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="1/s" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_min" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="-" start="-1.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_max" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="-" start="1.0"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="2"/>
    </Outputs>
    <Derivatives>
      <Unknown index="3" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="2"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
SpoolValveActuator FMU Model Implementation
FMI 2.0 Co-Simulation

Spool valve actuator with:
- Deadzone nonlinearity
- First-order dynamics
- Rate limiting
- Saturation

State equation:
  ds/dt = clip((u_eff - s) / tau, -rate_limit, +rate_limit)
  u_eff = deadzone_map(u_cmd, deadzone)
  output = clip(s, u_min, u_max)
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


def deadzone_map(u_cmd, d):
    """
    Deadzone mapping with normalization.
    
    Maps [-1, 1] -> [-1, 1] with deadzone [-d, d] -> 0.
    The mapping ensures full range after deadzone:
    - If |u_cmd| <= d: return 0
    - Otherwise: return (u_cmd - d*sign(u_cmd)) / (1 - d)
    
    This linearizes the deadzone effect so that:
    - u_cmd = d yields u_eff = 0
    - u_cmd = 1 yields u_eff = 1
    - u_cmd = -1 yields u_eff = -1
    """
    if abs(u_cmd) <= d:
        return 0.0
    return (u_cmd - d * sign(u_cmd)) / (1.0 - d)


class SpoolValveActuator:
    """Spool Valve Actuator with Deadzone, Dynamics, and Rate Limiting"""
    
    def __init__(self):
        # Actuator parameters (defaults from spec)
        self.tau_s = 0.03           # First-order time constant (s)
        self.deadzone = 0.05        # Command deadzone
        self.rate_limit_per_s = 25.0  # Maximum |d(spool_u)/dt|
        self.u_min = -1.0           # Minimum spool position
        self.u_max = 1.0            # Maximum spool position
        
        # State variable (internal spool position)
        self.spool_state = 0.0
        
        # Inputs
        self.valve_cmd = 0.0        # Normalized valve command
        
        # Outputs
        self.spool_u = 0.0          # Normalized spool opening
        
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
            if v == 0: values.append(self.valve_cmd)
            # Outputs
            elif v == 10: values.append(self.spool_u)
            # States
            elif v == 20: values.append(self.spool_state)
            # Parameters
            elif v == 100: values.append(self.tau_s)
            elif v == 101: values.append(self.deadzone)
            elif v == 102: values.append(self.rate_limit_per_s)
            elif v == 103: values.append(self.u_min)
            elif v == 104: values.append(self.u_max)
            else: values.append(0.0)
        return values
    
    def get_boolean(self, vr):
        """Get boolean values by value references"""
        values = []
        for v in vr:
            values.append(False)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.valve_cmd = val
            # States
            elif v == 20: self.spool_state = val
            # Parameters
            elif v == 100: self.tau_s = val
            elif v == 101: self.deadzone = val
            elif v == 102: self.rate_limit_per_s = val
            elif v == 103: self.u_min = val
            elif v == 104: self.u_max = val
    
    def set_boolean(self, vr, values):
        """Set boolean values by value references"""
        pass
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        # Output is clipped state
        self.spool_u = clip(self.spool_state, self.u_min, self.u_max)
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Uses explicit Euler integration.
        Implements:
        1. Input clipping
        2. Deadzone mapping
        3. First-order dynamics with rate limiting
        4. Output saturation
        """
        dt = communication_step_size
        
        # 1. Clip input command to valid range
        u_cmd = clip(self.valve_cmd, self.u_min, self.u_max)
        
        # 2. Apply deadzone mapping
        u_eff = deadzone_map(u_cmd, self.deadzone)
        
        # 3. First-order dynamics: ds/dt = (u_eff - s) / tau
        ds_dt = (u_eff - self.spool_state) / self.tau_s
        
        # 4. Apply rate limiting
        ds_dt = clip(ds_dt, -self.rate_limit_per_s, self.rate_limit_per_s)
        
        # 5. Update state (Euler integration)
        self.spool_state = self.spool_state + ds_dt * dt
        
        # 6. Compute output (saturated state)
        self.spool_u = clip(self.spool_state, self.u_min, self.u_max)
        
        self.time = current_time + dt
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = SpoolValveActuator()
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