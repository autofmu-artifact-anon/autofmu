#!/usr/bin/env python3
"""
Generate PoleAngleEstimator FMU (FMI 2.0 Co-Simulation)

State estimator for cart-pole angle and angular velocity:
- First-order low-pass filter for angle (with wrap-to-pi handling)
- Bias estimation for angular velocity measurement
- 2 continuous states: theta_hat and bias_hat
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "PoleAngleEstimator"
GUID = "{b2c3d4e5-f6a7-8901-bcde-f23456789012}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T02:15:00Z"
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
    <ScalarVariable name="theta_meas_rad" valueReference="0" causality="input" variability="continuous">
      <Real unit="rad" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_meas_rps" valueReference="1" causality="input" variability="continuous">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="reset" valueReference="2" causality="input" variability="discrete">
      <Boolean start="false"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="theta_hat_rad" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_hat_rps" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad/s"/>
    </ScalarVariable>
    <ScalarVariable name="bias_hat_rps" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad/s"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="theta_hat_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="rad" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="bias_hat_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="theta_lpf_tau_s" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="s" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="bias_adapt_rate" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="1/s" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="innovation_clip_rad" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="rad" start="0.3"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </Outputs>
    <Derivatives>
      <Unknown index="7" dependencies=""/>
      <Unknown index="8" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
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
PoleAngleEstimator FMU Model Implementation
FMI 2.0 Co-Simulation

State estimator for cart-pole:
- First-order low-pass filter for angle (with wrap-to-pi handling)
- Bias estimation for angular velocity measurement
- 2 continuous states: theta_hat and bias_hat

This demonstrates sensor processing and state estimation complexity.
"""

import math


class PoleAngleEstimator:
    """Pole Angle/Angular Velocity Estimator"""
    
    def __init__(self):
        # Parameters (defaults from spec)
        self.theta_lpf_tau_s = 0.05      # Angle LPF time constant (s)
        self.bias_adapt_rate = 0.8       # Bias adaptation rate (1/s)
        self.innovation_clip_rad = 0.3   # Innovation clip limit (rad)
        
        # State variables
        self.theta_hat = 0.0    # Estimated angle (rad)
        self.bias_hat = 0.0     # Estimated bias (rad/s)
        
        # Inputs
        self.theta_meas_rad = 0.0
        self.theta_dot_meas_rps = 0.0
        self.reset = False
        
        # Outputs
        self.theta_hat_rad = 0.0
        self.theta_dot_hat_rps = 0.0
        self.bias_hat_rps = 0.0
        
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
            if v == 0: values.append(self.theta_meas_rad)
            elif v == 1: values.append(self.theta_dot_meas_rps)
            # Outputs
            elif v == 10: values.append(self.theta_hat_rad)
            elif v == 11: values.append(self.theta_dot_hat_rps)
            elif v == 12: values.append(self.bias_hat_rps)
            # States
            elif v == 20: values.append(self.theta_hat)
            elif v == 21: values.append(self.bias_hat)
            # Parameters
            elif v == 100: values.append(self.theta_lpf_tau_s)
            elif v == 101: values.append(self.bias_adapt_rate)
            elif v == 102: values.append(self.innovation_clip_rad)
            else: values.append(0.0)
        return values
    
    def get_boolean(self, vr):
        """Get boolean values by value references"""
        values = []
        for v in vr:
            if v == 2: values.append(self.reset)
            else: values.append(False)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.theta_meas_rad = val
            elif v == 1: self.theta_dot_meas_rps = val
            # States
            elif v == 20: self.theta_hat = val
            elif v == 21: self.bias_hat = val
            # Parameters
            elif v == 100: self.theta_lpf_tau_s = val
            elif v == 101: self.bias_adapt_rate = val
            elif v == 102: self.innovation_clip_rad = val
    
    def set_boolean(self, vr, values):
        """Set boolean values by value references"""
        for i, v in enumerate(vr):
            if v == 2: self.reset = values[i]
    
    def _wrap_to_pi(self, a):
        """Wrap angle to (-pi, pi]"""
        while a <= -math.pi:
            a += 2.0 * math.pi
        while a > math.pi:
            a -= 2.0 * math.pi
        return a
    
    def _clip(self, x, lo, hi):
        """Clip value to range [lo, hi]"""
        return max(lo, min(hi, x))
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        self.theta_hat_rad = self.theta_hat
        self.bias_hat_rps = self.bias_hat
        self.theta_dot_hat_rps = self.theta_dot_meas_rps - self.bias_hat
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        if self.reset:
            # Reset to current measurement, bias = 0
            self.theta_hat = self.theta_meas_rad
            self.bias_hat = 0.0
            self._compute_outputs()
            return 0
        
        # Current state
        theta_hat = self.theta_hat
        bias_hat = self.bias_hat
        
        # Angle estimation: first-order LPF with wrap-to-pi
        e = self._wrap_to_pi(self.theta_meas_rad - theta_hat)
        d_theta_hat = e / self.theta_lpf_tau_s
        theta_hat_new = theta_hat + d_theta_hat * dt
        
        # Innovation for bias estimation (with wrap and clip)
        nu = self._clip(
            self._wrap_to_pi(self.theta_meas_rad - theta_hat_new),
            -self.innovation_clip_rad,
            self.innovation_clip_rad
        )
        
        # Bias adaptation
        d_bias = self.bias_adapt_rate * nu
        bias_hat_new = bias_hat + d_bias * dt
        
        # Update state
        self.theta_hat = theta_hat_new
        self.bias_hat = bias_hat_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = PoleAngleEstimator()
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
    output_path = output_dir / f"{MODEL_NAME}.fmu"
    create_fmu(output_path)