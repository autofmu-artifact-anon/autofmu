#!/usr/bin/env python3
"""
Generate InvertedPendulumPlant FMU (FMI 2.0 Co-Simulation)

Nonlinear inverted pendulum on cart dynamics with:
- 4 continuous states: x, x_dot, theta, theta_dot
- Viscous cart friction and pendulum joint damping
- theta=0 is upright (inverted pendulum convention)
- Semi-implicit Euler integration for stability
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "InvertedPendulumPlant"
GUID = "{b2c3d4e5-f6a7-8901-bcde-f23456789012}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T03:18:00Z"
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
    <ScalarVariable name="force_cmd_N" valueReference="0" causality="input" variability="continuous">
      <Real unit="N" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="disturbance_N" valueReference="1" causality="input" variability="continuous">
      <Real unit="N" start="0.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="x_m" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="m"/>
    </ScalarVariable>
    <ScalarVariable name="x_dot_mps" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="m/s"/>
    </ScalarVariable>
    <ScalarVariable name="theta_rad" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_radps" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad/s"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="x_m_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_dot_mps_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_rad_state" valueReference="22" causality="local" variability="continuous" initial="exact">
      <Real unit="rad" start="0.1"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_radps_state" valueReference="23" causality="local" variability="continuous" initial="exact">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters -->
    <ScalarVariable name="m_cart_kg" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="kg" start="1.0"/>
    </ScalarVariable>
    <ScalarVariable name="m_pend_kg" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="kg" start="0.2"/>
    </ScalarVariable>
    <ScalarVariable name="length_m" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="m" start="0.5"/>
    </ScalarVariable>
    <ScalarVariable name="g_mps2" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="m/s^2" start="9.81"/>
    </ScalarVariable>
    <ScalarVariable name="cart_friction_Nspm" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="N*s/m" start="0.1"/>
    </ScalarVariable>
    <ScalarVariable name="pend_damping_Nms" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="N*m*s" start="0.02"/>
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
      <Unknown index="9" dependencies=""/>
      <Unknown index="10" dependencies=""/>
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
InvertedPendulumPlant FMU Model Implementation
FMI 2.0 Co-Simulation

Nonlinear inverted pendulum on cart dynamics with:
- 4 continuous states: x, x_dot, theta, theta_dot
- Viscous cart friction and pendulum joint damping
- theta=0 is upright (inverted pendulum convention)
- Semi-implicit Euler integration for stability

Angle convention: theta=0 is upright vertical, positive = clockwise from vertical.
"""

import math


class InvertedPendulumPlant:
    """Inverted Pendulum on Cart - Nonlinear Dynamics Model"""
    
    def __init__(self):
        # Physical parameters (defaults from spec)
        self.m_cart_kg = 1.0        # cart mass (kg)
        self.m_pend_kg = 0.2        # pendulum equivalent mass (kg)
        self.length_m = 0.5         # pivot to center of mass distance (m)
        self.g_mps2 = 9.81          # gravity (m/s^2)
        self.cart_friction_Nspm = 0.1   # cart viscous friction (N*s/m)
        self.pend_damping_Nms = 0.02    # pendulum joint damping (N*m*s)
        
        # State variables
        self.x = 0.0           # cart position (m)
        self.x_dot = 0.0       # cart velocity (m/s)
        self.theta = 0.1       # pendulum angle (rad), theta=0 is upright
        self.theta_dot = 0.0   # pendulum angular velocity (rad/s)
        
        # Inputs
        self.force_cmd_N = 0.0
        self.disturbance_N = 0.0
        
        # Outputs
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_rad = 0.0
        self.theta_dot_radps = 0.0
        
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
            if v == 0: values.append(self.force_cmd_N)
            elif v == 1: values.append(self.disturbance_N)
            # Outputs
            elif v == 10: values.append(self.x_m)
            elif v == 11: values.append(self.x_dot_mps)
            elif v == 12: values.append(self.theta_rad)
            elif v == 13: values.append(self.theta_dot_radps)
            # States
            elif v == 20: values.append(self.x)
            elif v == 21: values.append(self.x_dot)
            elif v == 22: values.append(self.theta)
            elif v == 23: values.append(self.theta_dot)
            # Parameters
            elif v == 100: values.append(self.m_cart_kg)
            elif v == 101: values.append(self.m_pend_kg)
            elif v == 102: values.append(self.length_m)
            elif v == 103: values.append(self.g_mps2)
            elif v == 104: values.append(self.cart_friction_Nspm)
            elif v == 105: values.append(self.pend_damping_Nms)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.force_cmd_N = val
            elif v == 1: self.disturbance_N = val
            # States
            elif v == 20: self.x = val
            elif v == 21: self.x_dot = val
            elif v == 22: self.theta = val
            elif v == 23: self.theta_dot = val
            # Parameters
            elif v == 100: self.m_cart_kg = val
            elif v == 101: self.m_pend_kg = val
            elif v == 102: self.length_m = val
            elif v == 103: self.g_mps2 = val
            elif v == 104: self.cart_friction_Nspm = val
            elif v == 105: self.pend_damping_Nms = val
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        self.x_m = self.x
        self.x_dot_mps = self.x_dot
        self.theta_rad = self.theta
        self.theta_dot_radps = self.theta_dot
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Uses semi-implicit Euler integration as specified in the model spec.
        Implements the nonlinear inverted pendulum dynamics with friction/damping.
        """
        dt = communication_step_size
        
        # Unpack state
        x = self.x
        xdot = self.x_dot
        th = self.theta
        thdot = self.theta_dot
        
        # Unpack inputs
        u = self.force_cmd_N
        d = self.disturbance_N
        
        # Unpack parameters
        M = self.m_cart_kg
        m = self.m_pend_kg
        l = self.length_m
        g = self.g_mps2
        b = self.cart_friction_Nspm
        c = self.pend_damping_Nms
        
        # Total horizontal force with viscous cart friction
        F = u + d - b * xdot
        
        # Trig terms
        s_th = math.sin(th)
        c_th = math.cos(th)
        
        # Denominator (avoid division by zero)
        Delta = M + m * (s_th ** 2)
        Delta = max(1e-6, Delta)
        
        # Protect against small l
        l_safe = max(1e-6, l)
        
        # Nonlinear accelerations from spec equations:
        # x_ddot = [F + m*sin(th)*(l*thdot^2 + g*cos(th)) - c*thdot*cos(th)/l] / Delta
        # th_ddot = [-F*cos(th) - m*l*thdot^2*cos(th)*sin(th) - (M+m)*g*sin(th) 
        #            + c*thdot*(M+m)/(m*l^2)] / (l*Delta)
        
        xdd = (F + m * s_th * (l * (thdot ** 2) + g * c_th) 
               - (c * thdot * c_th) / l_safe) / Delta
        
        thdd = (-F * c_th 
                - m * l * (thdot ** 2) * c_th * s_th 
                - (M + m) * g * s_th 
                + c * thdot * (M + m) / max(1e-6, (m * l * l))) / (l_safe * Delta)
        
        # Semi-implicit Euler integration (more stable than explicit Euler)
        # Update velocities first
        xdot_new = xdot + xdd * dt
        thdot_new = thdot + thdd * dt
        
        # Then update positions using new velocities
        x_new = x + xdot_new * dt
        th_new = th + thdot_new * dt
        
        # Update state
        self.x = x_new
        self.x_dot = xdot_new
        self.theta = th_new
        self.theta_dot = thdot_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = InvertedPendulumPlant()
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