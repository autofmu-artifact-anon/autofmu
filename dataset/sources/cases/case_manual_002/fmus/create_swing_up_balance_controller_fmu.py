#!/usr/bin/env python3
"""
Generate SwingUpBalanceController FMU (FMI 2.0 Co-Simulation)

Hybrid controller for inverted pendulum:
- Energy shaping swing-up mode
- Linear feedback balance mode (LQR-like)
- Mode switching with hysteresis
- Output saturation with anti-windup
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "SwingUpBalanceController"
GUID = "{c3d4e5f6-a7b8-9012-cdef-345678901234}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T02:20:00Z"
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
  
  <DefaultExperiment startTime="0" stopTime="20" stepSize="0.001"/>
  
  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="x_m" valueReference="0" causality="input" variability="continuous">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_dot_mps" valueReference="1" causality="input" variability="continuous">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_hat_rad" valueReference="2" causality="input" variability="continuous">
      <Real unit="rad" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_hat_rps" valueReference="3" causality="input" variability="continuous">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_ref_m" valueReference="4" causality="input" variability="continuous">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="enable" valueReference="5" causality="input" variability="discrete">
      <Boolean start="true"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="force_cmd_N" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="N"/>
    </ScalarVariable>
    <ScalarVariable name="mode" valueReference="11" causality="output" variability="discrete" initial="calculated">
      <Integer/>
    </ScalarVariable>
    
    <!-- States -->
    <ScalarVariable name="x_err_int" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="m*s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="mode_state" valueReference="21" causality="local" variability="discrete" initial="exact">
      <Integer start="0"/>
    </ScalarVariable>
    
    <!-- Parameters - Saturation -->
    <ScalarVariable name="F_max_N" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="N" start="15.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Mode Switching -->
    <ScalarVariable name="theta_balance_thresh_rad" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="rad" start="0.25"/>
    </ScalarVariable>
    <ScalarVariable name="theta_fallback_thresh_rad" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="rad" start="0.5"/>
    </ScalarVariable>
    
    <!-- Parameters - Swing-Up -->
    <ScalarVariable name="swingup_energy_gain" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="N" start="20.0"/>
    </ScalarVariable>
    <ScalarVariable name="swingup_damping" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="N*s" start="2.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Balance -->
    <ScalarVariable name="balance_kx" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="N/m" start="40.0"/>
    </ScalarVariable>
    <ScalarVariable name="balance_kxd" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="N/(m/s)" start="8.0"/>
    </ScalarVariable>
    <ScalarVariable name="balance_kth" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="N/rad" start="120.0"/>
    </ScalarVariable>
    <ScalarVariable name="balance_kthd" valueReference="108" causality="parameter" variability="fixed">
      <Real unit="N/(rad/s)" start="15.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Integrator -->
    <ScalarVariable name="x_int_ki" valueReference="109" causality="parameter" variability="fixed">
      <Real unit="N/(m*s)" start="8.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_int_limit" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="m*s" start="0.25"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="7"/>
      <Unknown index="8"/>
    </Outputs>
    <InitialUnknowns>
      <Unknown index="7"/>
      <Unknown index="8"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
SwingUpBalanceController FMU Model Implementation
FMI 2.0 Co-Simulation

Hybrid controller for inverted pendulum:
- Energy shaping swing-up mode (mode=0)
- Linear feedback balance mode (mode=1)
- Mode switching with hysteresis
- Output saturation with anti-windup
- Position error integrator for steady-state tracking
"""

import math


class SwingUpBalanceController:
    """Swing-Up + Balance Controller for Inverted Pendulum"""
    
    def __init__(self):
        # Saturation parameter
        self.F_max_N = 15.0
        
        # Mode switching thresholds
        self.theta_balance_thresh_rad = 0.25
        self.theta_fallback_thresh_rad = 0.5
        
        # Swing-up parameters
        self.swingup_energy_gain = 20.0
        self.swingup_damping = 2.0
        
        # Balance gains
        self.balance_kx = 40.0
        self.balance_kxd = 8.0
        self.balance_kth = 120.0
        self.balance_kthd = 15.0
        
        # Integrator parameters
        self.x_int_ki = 8.0
        self.x_int_limit = 0.25
        
        # State variables
        self.x_err_int = 0.0       # Position error integral
        self.mode_state = 0        # 0=SwingUp, 1=Balance
        
        # Inputs
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_hat_rad = 0.0
        self.theta_dot_hat_rps = 0.0
        self.x_ref_m = 0.0
        self.enable = True
        
        # Outputs
        self.force_cmd_N = 0.0
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
            # Inputs
            if v == 0: values.append(self.x_m)
            elif v == 1: values.append(self.x_dot_mps)
            elif v == 2: values.append(self.theta_hat_rad)
            elif v == 3: values.append(self.theta_dot_hat_rps)
            elif v == 4: values.append(self.x_ref_m)
            # Outputs
            elif v == 10: values.append(self.force_cmd_N)
            # States
            elif v == 20: values.append(self.x_err_int)
            # Parameters
            elif v == 100: values.append(self.F_max_N)
            elif v == 101: values.append(self.theta_balance_thresh_rad)
            elif v == 102: values.append(self.theta_fallback_thresh_rad)
            elif v == 103: values.append(self.swingup_energy_gain)
            elif v == 104: values.append(self.swingup_damping)
            elif v == 105: values.append(self.balance_kx)
            elif v == 106: values.append(self.balance_kxd)
            elif v == 107: values.append(self.balance_kth)
            elif v == 108: values.append(self.balance_kthd)
            elif v == 109: values.append(self.x_int_ki)
            elif v == 110: values.append(self.x_int_limit)
            else: values.append(0.0)
        return values
    
    def get_integer(self, vr):
        """Get integer values by value references"""
        values = []
        for v in vr:
            if v == 11: values.append(self.mode)
            elif v == 21: values.append(self.mode_state)
            else: values.append(0)
        return values
    
    def get_boolean(self, vr):
        """Get boolean values by value references"""
        values = []
        for v in vr:
            if v == 5: values.append(self.enable)
            else: values.append(False)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.x_m = val
            elif v == 1: self.x_dot_mps = val
            elif v == 2: self.theta_hat_rad = val
            elif v == 3: self.theta_dot_hat_rps = val
            elif v == 4: self.x_ref_m = val
            # States
            elif v == 20: self.x_err_int = val
            # Parameters
            elif v == 100: self.F_max_N = val
            elif v == 101: self.theta_balance_thresh_rad = val
            elif v == 102: self.theta_fallback_thresh_rad = val
            elif v == 103: self.swingup_energy_gain = val
            elif v == 104: self.swingup_damping = val
            elif v == 105: self.balance_kx = val
            elif v == 106: self.balance_kxd = val
            elif v == 107: self.balance_kth = val
            elif v == 108: self.balance_kthd = val
            elif v == 109: self.x_int_ki = val
            elif v == 110: self.x_int_limit = val
    
    def set_integer(self, vr, values):
        """Set integer values by value references"""
        for i, v in enumerate(vr):
            if v == 21: self.mode_state = values[i]
    
    def set_boolean(self, vr, values):
        """Set boolean values by value references"""
        for i, v in enumerate(vr):
            if v == 5: self.enable = values[i]
    
    def _wrap_to_pi(self, a):
        """Wrap angle to (-pi, pi]"""
        while a <= -math.pi:
            a += 2.0 * math.pi
        while a > math.pi:
            a -= 2.0 * math.pi
        return a
    
    def _clamp(self, x, lo, hi):
        """Clamp value to range [lo, hi]"""
        return max(lo, min(hi, x))
    
    def _sign(self, x):
        """Sign function"""
        if x > 0:
            return 1.0
        elif x < 0:
            return -1.0
        else:
            return 0.0
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        self.mode = self.mode_state
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        # If disabled, freeze integrator and output zero
        if not self.enable:
            self.force_cmd_N = 0.0
            self.mode = self.mode_state
            return 0
        
        # Get current inputs
        x = self.x_m
        xd = self.x_dot_mps
        th = self.theta_hat_rad
        thd = self.theta_dot_hat_rps
        xref = self.x_ref_m
        
        # Compute angle relative to upright (theta_tilde = 0 at upright)
        th_tilde = self._wrap_to_pi(th - math.pi)
        
        # Mode switching with hysteresis
        mode = self.mode_state
        if mode == 0:
            # Swing-up -> Balance transition
            if abs(th_tilde) < self.theta_balance_thresh_rad:
                mode = 1
        else:
            # Balance -> Swing-up transition
            if abs(th_tilde) > self.theta_fallback_thresh_rad:
                mode = 0
        
        # Integrator update (only in balance mode)
        I = self.x_err_int
        if mode == 1:
            # Position error
            e = xref - x
            # Clip instantaneous error before integrating
            e_clip = self._clamp(e, -0.5, 0.5)
            I_candidate = self._clamp(I + e_clip * dt, -self.x_int_limit, self.x_int_limit)
        else:
            I_candidate = I
        
        # Control law
        if mode == 0:
            # Swing-up mode: energy shaping
            # Energy (normalized, E=2 at upright)
            E = 0.5 * (thd ** 2) + (1.0 - math.cos(th))
            E_star = 2.0
            eE = E - E_star
            
            # Energy injection direction
            inject_dir = self._sign(thd * math.cos(th))
            
            # Swing-up force
            F = -self.swingup_energy_gain * eE * inject_dir - self.swingup_damping * xd
        else:
            # Balance mode: linear feedback + integral
            F = (
                -self.balance_kx * (x - xref)
                -self.balance_kxd * xd
                -self.balance_kth * th_tilde
                -self.balance_kthd * thd
                + self.x_int_ki * I_candidate
            )
        
        # Output saturation
        F_sat = self._clamp(F, -self.F_max_N, self.F_max_N)
        
        # Anti-windup: freeze integrator when saturated in balance mode
        if mode == 1 and F != F_sat:
            I_next = I  # Keep previous integral
        else:
            I_next = I_candidate
        
        # Update state
        self.x_err_int = I_next
        self.mode_state = mode
        self.force_cmd_N = F_sat
        self.mode = mode
        self.time = current_time + dt
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = SwingUpBalanceController()
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


def get_integer(fmi_instance, vr, nvr, value):
    values = fmi_instance.get_integer(vr[:nvr])
    for i, v in enumerate(values):
        value[i] = v
    return 0


def set_integer(fmi_instance, vr, nvr, value):
    fmi_instance.set_integer(vr[:nvr], list(value[:nvr]))
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
    'fmi2GetInteger': get_integer,
    'fmi2SetInteger': set_integer,
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
    output_path = output_dir / f"{MODEL_NAME}.fmu"
    create_fmu(output_path)