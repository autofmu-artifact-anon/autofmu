#!/usr/bin/env python3
"""
Generate CartPolePlant FMU (FMI 2.0 Co-Simulation)

Nonlinear cart-pole dynamics with:
- Actuator saturation + first-order lag
- Nonlinear friction (Coulomb + viscous, tanh smoothed)
- Soft track limits (nonlinear spring)
- Noisy sensors (angle noise, angular velocity bias + noise)
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "CartPolePlant"
GUID = "{a1b2c3d4-e5f6-7890-abcd-ef1234567890}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T01:30:00Z"
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
    <ScalarVariable name="force_cmd_N" valueReference="0" causality="input" variability="continuous">
      <Real unit="N" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="disturbance_force_N" valueReference="1" causality="input" variability="continuous">
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
    <ScalarVariable name="theta_dot_rps" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad/s"/>
    </ScalarVariable>
    <ScalarVariable name="theta_meas_rad" valueReference="14" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_meas_rps" valueReference="15" causality="output" variability="continuous" initial="calculated">
      <Real unit="rad/s"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="x_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_dot_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="theta_state" valueReference="22" causality="local" variability="continuous" initial="exact">
      <Real unit="rad" start="0.1"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_state" valueReference="23" causality="local" variability="continuous" initial="exact">
      <Real unit="rad/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="F_act_state" valueReference="24" causality="local" variability="continuous" initial="exact">
      <Real unit="N" start="0.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Physical -->
    <ScalarVariable name="m_cart_kg" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="kg" start="0.6"/>
    </ScalarVariable>
    <ScalarVariable name="m_pole_kg" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="kg" start="0.2"/>
    </ScalarVariable>
    <ScalarVariable name="l_com_m" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="m" start="0.25"/>
    </ScalarVariable>
    <ScalarVariable name="I_pole_kgm2" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="kg*m^2" start="0.006"/>
    </ScalarVariable>
    <ScalarVariable name="g_mps2" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="m/s^2" start="9.81"/>
    </ScalarVariable>
    
    <!-- Parameters - Actuator -->
    <ScalarVariable name="F_max_N" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="N" start="15.0"/>
    </ScalarVariable>
    <ScalarVariable name="actuator_tau_s" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="s" start="0.03"/>
    </ScalarVariable>
    
    <!-- Parameters - Friction -->
    <ScalarVariable name="cart_fric_coulomb_N" valueReference="107" causality="parameter" variability="fixed">
      <Real unit="N" start="1.2"/>
    </ScalarVariable>
    <ScalarVariable name="cart_fric_visc_Ns_per_m" valueReference="108" causality="parameter" variability="fixed">
      <Real unit="N*s/m" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="fric_smooth_v0_mps" valueReference="109" causality="parameter" variability="fixed">
      <Real unit="m/s" start="0.02"/>
    </ScalarVariable>
    
    <!-- Parameters - Soft Limits -->
    <ScalarVariable name="x_limit_m" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="m" start="0.5"/>
    </ScalarVariable>
    <ScalarVariable name="x_limit_k_N_per_m" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="N/m" start="120.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Sensor Noise -->
    <ScalarVariable name="theta_meas_sigma_rad" valueReference="112" causality="parameter" variability="fixed">
      <Real unit="rad" start="0.003"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_bias_rps" valueReference="113" causality="parameter" variability="fixed">
      <Real unit="rad/s" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="theta_dot_meas_sigma_rps" valueReference="114" causality="parameter" variability="fixed">
      <Real unit="rad/s" start="0.02"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
    </Outputs>
    <Derivatives>
      <Unknown index="9" dependencies=""/>
      <Unknown index="10" dependencies=""/>
      <Unknown index="11" dependencies=""/>
      <Unknown index="12" dependencies=""/>
      <Unknown index="13" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
      <Unknown index="7"/>
      <Unknown index="8"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
CartPolePlant FMU Model Implementation
FMI 2.0 Co-Simulation

Nonlinear cart-pole dynamics with:
- Actuator saturation + first-order lag
- Nonlinear friction (Coulomb + viscous, tanh smoothed)
- Soft track limits (nonlinear spring)
- Noisy sensors (angle noise, angular velocity bias + noise)

Angle convention: theta=0 is hanging down, theta=pi is upright.
"""

import math
import random


class CartPolePlant:
    """Cart-Pole Nonlinear Dynamics Model"""
    
    def __init__(self):
        # Physical parameters (defaults from spec)
        self.m_cart_kg = 0.6
        self.m_pole_kg = 0.2
        self.l_com_m = 0.25
        self.I_pole_kgm2 = 0.006
        self.g_mps2 = 9.81
        
        # Actuator parameters
        self.F_max_N = 15.0
        self.actuator_tau_s = 0.03
        
        # Friction parameters
        self.cart_fric_coulomb_N = 1.2
        self.cart_fric_visc_Ns_per_m = 0.8
        self.fric_smooth_v0_mps = 0.02
        
        # Soft limit parameters
        self.x_limit_m = 0.5
        self.x_limit_k_N_per_m = 120.0
        
        # Sensor noise parameters
        self.theta_meas_sigma_rad = 0.003
        self.theta_dot_bias_rps = 0.05
        self.theta_dot_meas_sigma_rps = 0.02
        
        # State variables
        self.x = 0.0           # cart position (m)
        self.x_dot = 0.0       # cart velocity (m/s)
        self.theta = 0.1       # pole angle (rad), 0=down, pi=up
        self.theta_dot = 0.0   # pole angular velocity (rad/s)
        self.F_act = 0.0       # actuator actual force (N)
        
        # Inputs
        self.force_cmd_N = 0.0
        self.disturbance_force_N = 0.0
        
        # Outputs
        self.x_m = 0.0
        self.x_dot_mps = 0.0
        self.theta_rad = 0.0
        self.theta_dot_rps = 0.0
        self.theta_meas_rad = 0.0
        self.theta_dot_meas_rps = 0.0
        
        # RNG for sensor noise
        self.rng = random.Random(42)  # Fixed seed for reproducibility
        
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
            elif v == 1: values.append(self.disturbance_force_N)
            # Outputs
            elif v == 10: values.append(self.x_m)
            elif v == 11: values.append(self.x_dot_mps)
            elif v == 12: values.append(self.theta_rad)
            elif v == 13: values.append(self.theta_dot_rps)
            elif v == 14: values.append(self.theta_meas_rad)
            elif v == 15: values.append(self.theta_dot_meas_rps)
            # States
            elif v == 20: values.append(self.x)
            elif v == 21: values.append(self.x_dot)
            elif v == 22: values.append(self.theta)
            elif v == 23: values.append(self.theta_dot)
            elif v == 24: values.append(self.F_act)
            # Parameters - Physical
            elif v == 100: values.append(self.m_cart_kg)
            elif v == 101: values.append(self.m_pole_kg)
            elif v == 102: values.append(self.l_com_m)
            elif v == 103: values.append(self.I_pole_kgm2)
            elif v == 104: values.append(self.g_mps2)
            # Parameters - Actuator
            elif v == 105: values.append(self.F_max_N)
            elif v == 106: values.append(self.actuator_tau_s)
            # Parameters - Friction
            elif v == 107: values.append(self.cart_fric_coulomb_N)
            elif v == 108: values.append(self.cart_fric_visc_Ns_per_m)
            elif v == 109: values.append(self.fric_smooth_v0_mps)
            # Parameters - Soft Limits
            elif v == 110: values.append(self.x_limit_m)
            elif v == 111: values.append(self.x_limit_k_N_per_m)
            # Parameters - Sensor Noise
            elif v == 112: values.append(self.theta_meas_sigma_rad)
            elif v == 113: values.append(self.theta_dot_bias_rps)
            elif v == 114: values.append(self.theta_dot_meas_sigma_rps)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.force_cmd_N = val
            elif v == 1: self.disturbance_force_N = val
            # States
            elif v == 20: self.x = val
            elif v == 21: self.x_dot = val
            elif v == 22: self.theta = val
            elif v == 23: self.theta_dot = val
            elif v == 24: self.F_act = val
            # Parameters - Physical
            elif v == 100: self.m_cart_kg = val
            elif v == 101: self.m_pole_kg = val
            elif v == 102: self.l_com_m = val
            elif v == 103: self.I_pole_kgm2 = val
            elif v == 104: self.g_mps2 = val
            # Parameters - Actuator
            elif v == 105: self.F_max_N = val
            elif v == 106: self.actuator_tau_s = val
            # Parameters - Friction
            elif v == 107: self.cart_fric_coulomb_N = val
            elif v == 108: self.cart_fric_visc_Ns_per_m = val
            elif v == 109: self.fric_smooth_v0_mps = val
            # Parameters - Soft Limits
            elif v == 110: self.x_limit_m = val
            elif v == 111: self.x_limit_k_N_per_m = val
            # Parameters - Sensor Noise
            elif v == 112: self.theta_meas_sigma_rad = val
            elif v == 113: self.theta_dot_bias_rps = val
            elif v == 114: self.theta_dot_meas_sigma_rps = val
    
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
    
    def _wrap_to_pi(self, a):
        """Wrap angle to (-pi, pi]"""
        while a <= -math.pi:
            a += 2.0 * math.pi
        while a > math.pi:
            a -= 2.0 * math.pi
        return a
    
    def _gaussian(self, sigma):
        """Generate Gaussian random number using Box-Muller"""
        u1 = self.rng.random()
        u2 = self.rng.random()
        # Avoid log(0)
        while u1 == 0:
            u1 = self.rng.random()
        return sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        # Direct outputs
        self.x_m = self.x
        self.x_dot_mps = self.x_dot
        self.theta_rad = self.theta
        self.theta_dot_rps = self.theta_dot
        
        # Sensor outputs with noise
        n_theta = self._gaussian(self.theta_meas_sigma_rad)
        n_thdot = self._gaussian(self.theta_dot_meas_sigma_rps)
        
        self.theta_meas_rad = self._wrap_to_pi(self.theta + n_theta)
        self.theta_dot_meas_rps = self.theta_dot + self.theta_dot_bias_rps + n_thdot
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step"""
        dt = communication_step_size
        
        # Local copies for readability
        M = self.m_cart_kg
        m = self.m_pole_kg
        l = self.l_com_m
        I = self.I_pole_kgm2
        g = self.g_mps2
        
        # Current state
        x = self.x
        x_dot = self.x_dot
        theta = self.theta
        theta_dot = self.theta_dot
        F_act = self.F_act
        
        # 1) Actuator dynamics with saturation
        F_cmd = self.force_cmd_N
        F_sat = self._clamp(F_cmd, -self.F_max_N, self.F_max_N)
        
        if self.actuator_tau_s > 0:
            dF_act = (F_sat - F_act) / self.actuator_tau_s
        else:
            dF_act = 0.0
            F_act = F_sat
        
        # Integrate actuator state
        F_act_new = F_act + dF_act * dt
        
        # 2) Friction force (nonlinear)
        F_fric = self.cart_fric_coulomb_N * math.tanh(x_dot / self.fric_smooth_v0_mps) \
                 + self.cart_fric_visc_Ns_per_m * x_dot
        
        # 3) Soft limit force
        if abs(x) > self.x_limit_m:
            F_lim = -self.x_limit_k_N_per_m * (abs(x) - self.x_limit_m) * self._sign(x)
        else:
            F_lim = 0.0
        
        # 4) Total effective force
        F_dist = self.disturbance_force_N
        F_eff = (F_act_new + F_dist) - F_fric + F_lim
        
        # 5) Cart-pole dynamics (solve 2x2 linear system)
        S = math.sin(theta)
        C = math.cos(theta)
        alpha = I + m * l * l
        
        # Mass matrix
        a11 = M + m
        a12 = m * l * C
        a21 = m * l * C
        a22 = alpha
        
        # Right-hand side
        b1 = F_eff + m * l * (theta_dot ** 2) * S
        b2 = m * g * l * S
        
        # Solve for accelerations
        det = a11 * a22 - a12 * a21
        if abs(det) < 1e-12:
            # Singularity - use small perturbation
            det = 1e-12 * self._sign(det) if det != 0 else 1e-12
        
        x_ddot = (b1 * a22 - a12 * b2) / det
        theta_ddot = (-b1 * a21 + a11 * b2) / det
        
        # 6) Integrate states (forward Euler)
        x_new = x + x_dot * dt
        x_dot_new = x_dot + x_ddot * dt
        theta_new = theta + theta_dot * dt
        theta_dot_new = theta_dot + theta_ddot * dt
        
        # Update state
        self.x = x_new
        self.x_dot = x_dot_new
        self.theta = theta_new
        self.theta_dot = theta_dot_new
        self.F_act = F_act_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = CartPolePlant()
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