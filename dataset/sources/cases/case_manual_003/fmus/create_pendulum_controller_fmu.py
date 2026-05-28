#!/usr/bin/env python3
"""
Generate PendulumController FMU (FMI 2.0 Co-Simulation)

PID-based inverted pendulum controller with:
- 3 continuous states: int_theta, int_x, force_act_N
- Dual-loop control (angle + position)
- Anti-windup back-calculation
- Actuator first-order lag
- Saturation and deadzone nonlinearities
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "PendulumController"
GUID = "{c3d4e5f6-a789-0123-cdef-345678901234}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T05:25:00Z"
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
    <ScalarVariable name="x_ref_m" valueReference="0" causality="input" variability="continuous">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_ref_rad" valueReference="1" causality="input" variability="continuous">
      <Real unit="rad" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_m" valueReference="2" causality="input" variability="continuous">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_dot_mps" valueReference="3" causality="input" variability="continuous">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_rad" valueReference="4" causality="input" variability="continuous">
      <Real unit="rad" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_radps" valueReference="5" causality="input" variability="continuous">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="force_cmd_N" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="N"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="int_theta" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real description="摆角误差积分" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="int_x" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real description="位置误差积分" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="force_act_N_state" valueReference="22" causality="local" variability="continuous" initial="exact">
      <Real unit="N" description="执行器输出力" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Angle control gains -->
    <ScalarVariable name="Kp_theta" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="N/rad" start="80.0"/>
    </ScalarVariable>
    <ScalarVariable name="Kd_theta" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="N/(rad/s)" start="12.0"/>
    </ScalarVariable>
    <ScalarVariable name="Ki_theta" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="N/(rad·s)" start="10.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Position control gains -->
    <ScalarVariable name="Kp_x" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="N/m" start="2.0"/>
    </ScalarVariable>
    <ScalarVariable name="Kd_x" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="N/(m/s)" start="2.5"/>
    </ScalarVariable>
    <ScalarVariable name="Ki_x" valueReference="112" causality="parameter" variability="fixed">
      <Real unit="N/(m·s)" start="0.5"/>
    </ScalarVariable>
    
    <!-- Parameters - Nonlinear elements -->
    <ScalarVariable name="u_max_N" valueReference="120" causality="parameter" variability="fixed">
      <Real unit="N" start="15.0"/>
    </ScalarVariable>
    <ScalarVariable name="deadzone_N" valueReference="121" causality="parameter" variability="fixed">
      <Real unit="N" start="0.3"/>
    </ScalarVariable>
    <ScalarVariable name="actuator_tau_s" valueReference="122" causality="parameter" variability="fixed">
      <Real unit="s" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="antiwindup_gain" valueReference="123" causality="parameter" variability="fixed">
      <Real unit="1/s" start="5.0"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="7"/>
    </Outputs>
    <Derivatives>
      <Unknown index="8" dependencies=""/>
      <Unknown index="9" dependencies=""/>
      <Unknown index="10" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="7"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
PendulumController FMU Model Implementation
FMI 2.0 Co-Simulation

PID-based inverted pendulum controller with:
- 3 continuous states: int_theta, int_x, force_act_N
- Dual-loop control (angle + position)
- Anti-windup back-calculation
- Actuator first-order lag
- Saturation and deadzone nonlinearities
"""


class PendulumController:
    """Inverted Pendulum Controller with Anti-Windup and Actuator Dynamics"""
    
    def __init__(self):
        # Angle control gains (defaults from spec)
        self.Kp_theta = 80.0      # N/rad
        self.Kd_theta = 12.0      # N/(rad/s)
        self.Ki_theta = 10.0      # N/(rad·s)
        
        # Position control gains
        self.Kp_x = 2.0           # N/m
        self.Kd_x = 2.5           # N/(m/s)
        self.Ki_x = 0.5           # N/(m·s)
        
        # Nonlinear elements
        self.u_max_N = 15.0       # Maximum force (saturation)
        self.deadzone_N = 0.3     # Dead zone threshold
        self.actuator_tau_s = 0.05    # Actuator time constant (s)
        self.antiwindup_gain = 5.0    # Anti-windup back-calculation gain (1/s)
        
        # State variables
        self.int_theta = 0.0      # Angle error integral
        self.int_x = 0.0          # Position error integral
        self.force_act_N = 0.0    # Actuator force (with lag)
        
        # Inputs
        self.x_ref_m = 0.0
        self.theta_ref_rad = 0.0
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_rad = 0.0
        self.theta_dot_radps = 0.0
        
        # Outputs
        self.force_cmd_N = 0.0
        
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
            elif v == 1: values.append(self.theta_ref_rad)
            elif v == 2: values.append(self.x_m)
            elif v == 3: values.append(self.x_dot_mps)
            elif v == 4: values.append(self.theta_rad)
            elif v == 5: values.append(self.theta_dot_radps)
            # Outputs
            elif v == 10: values.append(self.force_cmd_N)
            # States
            elif v == 20: values.append(self.int_theta)
            elif v == 21: values.append(self.int_x)
            elif v == 22: values.append(self.force_act_N)
            # Parameters - Angle gains
            elif v == 100: values.append(self.Kp_theta)
            elif v == 101: values.append(self.Kd_theta)
            elif v == 102: values.append(self.Ki_theta)
            # Parameters - Position gains
            elif v == 110: values.append(self.Kp_x)
            elif v == 111: values.append(self.Kd_x)
            elif v == 112: values.append(self.Ki_x)
            # Parameters - Nonlinear elements
            elif v == 120: values.append(self.u_max_N)
            elif v == 121: values.append(self.deadzone_N)
            elif v == 122: values.append(self.actuator_tau_s)
            elif v == 123: values.append(self.antiwindup_gain)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.x_ref_m = val
            elif v == 1: self.theta_ref_rad = val
            elif v == 2: self.x_m = val
            elif v == 3: self.x_dot_mps = val
            elif v == 4: self.theta_rad = val
            elif v == 5: self.theta_dot_radps = val
            # States
            elif v == 20: self.int_theta = val
            elif v == 21: self.int_x = val
            elif v == 22: self.force_act_N = val
            # Parameters - Angle gains
            elif v == 100: self.Kp_theta = val
            elif v == 101: self.Kd_theta = val
            elif v == 102: self.Ki_theta = val
            # Parameters - Position gains
            elif v == 110: self.Kp_x = val
            elif v == 111: self.Kd_x = val
            elif v == 112: self.Ki_x = val
            # Parameters - Nonlinear elements
            elif v == 120: self.u_max_N = val
            elif v == 121: self.deadzone_N = val
            elif v == 122: self.actuator_tau_s = val
            elif v == 123: self.antiwindup_gain = val
    
    def _clip(self, x, lo, hi):
        """Clamp value between bounds"""
        return max(lo, min(hi, x))
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        self.force_cmd_N = self.force_act_N
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Implements dual-loop PID control with:
        - Anti-windup back-calculation
        - Saturation and deadzone
        - Actuator first-order lag
        """
        dt = communication_step_size
        
        # Read inputs
        x_ref = self.x_ref_m
        th_ref = self.theta_ref_rad
        x = self.x_m
        xdot = self.x_dot_mps
        th = self.theta_rad
        thdot = self.theta_dot_radps
        
        # Current integrator states
        I_th = self.int_theta
        I_x = self.int_x
        F_a = self.force_act_N
        
        # Compute errors
        e_th = th_ref - th
        e_x = x_ref - x
        
        # Raw (unsaturated) control command
        u_raw = (
            self.Kp_theta * e_th
            - self.Kd_theta * thdot
            + self.Ki_theta * I_th
            + self.Kp_x * e_x
            - self.Kd_x * xdot
            + self.Ki_x * I_x
        )
        
        # Saturation
        u_sat = self._clip(u_raw, -self.u_max_N, self.u_max_N)
        
        # Deadzone (applied after saturation)
        if abs(u_sat) < self.deadzone_N:
            u_dz = 0.0
        else:
            u_dz = u_sat
        
        # Anti-windup back-calculation
        # Weight factors: prioritize angle control over position
        kaw = self.antiwindup_gain
        w_th = 1.0   # Angle gets full anti-windup correction
        w_x = 0.2    # Position gets reduced anti-windup correction
        
        # Update integrators with anti-windup
        dI_th = e_th + kaw * (u_sat - u_raw) * w_th
        dI_x = e_x + kaw * (u_sat - u_raw) * w_x
        
        # Actuator dynamics (first-order lag)
        tau = max(1e-4, self.actuator_tau_s)  # Prevent division by zero
        dF_a = (u_dz - F_a) / tau
        
        # Integrate states
        I_th_new = I_th + dI_th * dt
        I_x_new = I_x + dI_x * dt
        F_a_new = F_a + dF_a * dt
        
        # Update state
        self.int_theta = I_th_new
        self.int_x = I_x_new
        self.force_act_N = F_a_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = PendulumController()
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
    output_path = output_dir / "PendulumController.fmu"
    create_fmu(output_path)