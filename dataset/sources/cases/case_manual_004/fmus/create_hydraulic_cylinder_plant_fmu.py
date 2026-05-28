#!/usr/bin/env python3
"""
Generate HydraulicCylinderPlant FMU (FMI 2.0 Co-Simulation)

Double-acting hydraulic cylinder + moving table with:
- 4 continuous states: x, v, pA, pB
- Nonlinear orifice flows, pressure dynamics, friction
- Semi-implicit Euler integration for stability
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# Model parameters from spec
MODEL_NAME = "HydraulicCylinderPlant"
GUID = "{a1b2c3d4-e5f6-7890-abcd-ef1234567890}"

# Create modelDescription.xml for FMI 2.0 Co-Simulation
MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T06:30:00Z"
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
  
  <DefaultExperiment startTime="0" stopTime="10" stepSize="0.0001"/>
  
  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="spool_u" valueReference="0" causality="input" variability="continuous">
      <Real unit="-" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="load_force_N" valueReference="1" causality="input" variability="continuous">
      <Real unit="N" start="0.0"/>
    </ScalarVariable>
    
    <!-- Outputs -->
    <ScalarVariable name="x_m" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="m"/>
    </ScalarVariable>
    <ScalarVariable name="v_mps" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="m/s"/>
    </ScalarVariable>
    <ScalarVariable name="pA_Pa" valueReference="12" causality="output" variability="continuous" initial="calculated">
      <Real unit="Pa"/>
    </ScalarVariable>
    <ScalarVariable name="pB_Pa" valueReference="13" causality="output" variability="continuous" initial="calculated">
      <Real unit="Pa"/>
    </ScalarVariable>
    <ScalarVariable name="rod_force_N" valueReference="14" causality="output" variability="continuous" initial="calculated">
      <Real unit="N"/>
    </ScalarVariable>
    
    <!-- States (with initial values) -->
    <ScalarVariable name="x_m_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="m" start="0.05"/>
    </ScalarVariable>
    <ScalarVariable name="v_mps_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="m/s" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="pA_Pa_state" valueReference="22" causality="local" variability="continuous" initial="exact">
      <Real unit="Pa" start="1.0e7"/>
    </ScalarVariable>
    <ScalarVariable name="pB_Pa_state" valueReference="23" causality="local" variability="continuous" initial="exact">
      <Real unit="Pa" start="5.0e6"/>
    </ScalarVariable>
    
    <!-- Parameters - Geometry -->
    <ScalarVariable name="stroke_m" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="m" start="0.10"/>
    </ScalarVariable>
    <ScalarVariable name="x_min_m" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="m" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="x_max_m" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="m" start="0.10"/>
    </ScalarVariable>
    
    <!-- Parameters - Mass and stops -->
    <ScalarVariable name="m_kg" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="kg" start="12.0"/>
    </ScalarVariable>
    <ScalarVariable name="k_stop_Npm" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="N/m" start="200000.0"/>
    </ScalarVariable>
    <ScalarVariable name="c_stop_Nspm" valueReference="112" causality="parameter" variability="fixed">
      <Real unit="N*s/m" start="1200.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Hydraulic -->
    <ScalarVariable name="A_A_m2" valueReference="120" causality="parameter" variability="fixed">
      <Real unit="m^2" start="0.0012"/>
    </ScalarVariable>
    <ScalarVariable name="A_B_m2" valueReference="121" causality="parameter" variability="fixed">
      <Real unit="m^2" start="0.0010"/>
    </ScalarVariable>
    <ScalarVariable name="V0_A_m3" valueReference="122" causality="parameter" variability="fixed">
      <Real unit="m^3" start="3.0e-4"/>
    </ScalarVariable>
    <ScalarVariable name="V0_B_m3" valueReference="123" causality="parameter" variability="fixed">
      <Real unit="m^3" start="3.0e-4"/>
    </ScalarVariable>
    
    <!-- Parameters - Fluid -->
    <ScalarVariable name="beta_eff_Pa" valueReference="130" causality="parameter" variability="fixed">
      <Real unit="Pa" start="8.0e8"/>
    </ScalarVariable>
    <ScalarVariable name="leak_C_L" valueReference="131" causality="parameter" variability="fixed">
      <Real unit="m^3/(s*Pa)" start="2.0e-12"/>
    </ScalarVariable>
    
    <!-- Parameters - Supply -->
    <ScalarVariable name="p_supply_Pa" valueReference="140" causality="parameter" variability="fixed">
      <Real unit="Pa" start="2.0e7"/>
    </ScalarVariable>
    <ScalarVariable name="p_tank_Pa" valueReference="141" causality="parameter" variability="fixed">
      <Real unit="Pa" start="2.0e5"/>
    </ScalarVariable>
    
    <!-- Parameters - Valve -->
    <ScalarVariable name="Cq" valueReference="150" causality="parameter" variability="fixed">
      <Real unit="m^3/(s*sqrt(Pa))" start="3.2e-5"/>
    </ScalarVariable>
    <ScalarVariable name="u_flow_sat" valueReference="151" causality="parameter" variability="fixed">
      <Real unit="-" start="1.0"/>
    </ScalarVariable>
    
    <!-- Parameters - Friction -->
    <ScalarVariable name="F_coulomb_N" valueReference="160" causality="parameter" variability="fixed">
      <Real unit="N" start="250.0"/>
    </ScalarVariable>
    <ScalarVariable name="F_static_N" valueReference="161" causality="parameter" variability="fixed">
      <Real unit="N" start="380.0"/>
    </ScalarVariable>
    <ScalarVariable name="v_stribeck_mps" valueReference="162" causality="parameter" variability="fixed">
      <Real unit="m/s" start="0.004"/>
    </ScalarVariable>
    <ScalarVariable name="b_visc_Nspm" valueReference="163" causality="parameter" variability="fixed">
      <Real unit="N*s/m" start="900.0"/>
    </ScalarVariable>
    <ScalarVariable name="v_tanh_mps" valueReference="164" causality="parameter" variability="fixed">
      <Real unit="m/s" start="0.002"/>
    </ScalarVariable>
  </ModelVariables>
  
  <ModelStructure>
    <Outputs>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
      <Unknown index="7"/>
    </Outputs>
    <Derivatives>
      <Unknown index="8" dependencies=""/>
      <Unknown index="9" dependencies=""/>
      <Unknown index="10" dependencies=""/>
      <Unknown index="11" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="3"/>
      <Unknown index="4"/>
      <Unknown index="5"/>
      <Unknown index="6"/>
      <Unknown index="7"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

# Python model implementation
MODEL_PY = '''#!/usr/bin/env python3
"""
HydraulicCylinderPlant FMU Model Implementation
FMI 2.0 Co-Simulation

Double-acting hydraulic cylinder + moving table with:
- 4 continuous states: x, v, pA, pB
- Nonlinear orifice flows, pressure dynamics, friction
- Semi-implicit Euler integration for stability

Physics:
- Orifice flow: q = Cq * alpha * sgn(dp) * sqrt(|dp|)
- Pressure dynamics: dp/dt = beta/V * (q_in - q_out - A*v - q_leak)
- Stribeck friction + soft stops at stroke limits
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


def phi_sqrt(dp):
    """Signed square root for orifice flow"""
    return sign(dp) * math.sqrt(abs(dp) + 1e-12)


class HydraulicCylinderPlant:
    """Double-acting Hydraulic Cylinder with Nonlinear Dynamics"""
    
    def __init__(self):
        # Physical parameters (defaults from spec)
        # Geometry
        self.stroke_m = 0.10
        self.x_min_m = 0.0
        self.x_max_m = 0.10
        
        # Mass and stops
        self.m_kg = 12.0
        self.k_stop_Npm = 200000.0
        self.c_stop_Nspm = 1200.0
        
        # Hydraulic areas and volumes
        self.A_A_m2 = 0.0012
        self.A_B_m2 = 0.0010
        self.V0_A_m3 = 3.0e-4
        self.V0_B_m3 = 3.0e-4
        
        # Fluid properties
        self.beta_eff_Pa = 8.0e8
        self.leak_C_L = 2.0e-12
        
        # Supply pressures
        self.p_supply_Pa = 2.0e7
        self.p_tank_Pa = 2.0e5
        
        # Valve
        self.Cq = 3.2e-5
        self.u_flow_sat = 1.0
        
        # Friction parameters
        self.F_coulomb_N = 250.0
        self.F_static_N = 380.0
        self.v_stribeck_mps = 0.004
        self.b_visc_Nspm = 900.0
        self.v_tanh_mps = 0.002
        
        # State variables
        self.x = 0.05         # position (m) - mid-stroke
        self.v = 0.0           # velocity (m/s)
        self.pA = 1.0e7        # chamber A pressure (Pa)
        self.pB = 5.0e6        # chamber B pressure (Pa)
        
        # Inputs
        self.spool_u = 0.0
        self.load_force_N = 0.0
        
        # Outputs
        self.x_m = 0.05
        self.v_mps = 0.0
        self.pA_Pa = 1.0e7
        self.pB_Pa = 5.0e6
        self.rod_force_N = 0.0
        
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
            if v == 0: values.append(self.spool_u)
            elif v == 1: values.append(self.load_force_N)
            # Outputs
            elif v == 10: values.append(self.x_m)
            elif v == 11: values.append(self.v_mps)
            elif v == 12: values.append(self.pA_Pa)
            elif v == 13: values.append(self.pB_Pa)
            elif v == 14: values.append(self.rod_force_N)
            # States
            elif v == 20: values.append(self.x)
            elif v == 21: values.append(self.v)
            elif v == 22: values.append(self.pA)
            elif v == 23: values.append(self.pB)
            # Parameters - Geometry
            elif v == 100: values.append(self.stroke_m)
            elif v == 101: values.append(self.x_min_m)
            elif v == 102: values.append(self.x_max_m)
            # Parameters - Mass and stops
            elif v == 110: values.append(self.m_kg)
            elif v == 111: values.append(self.k_stop_Npm)
            elif v == 112: values.append(self.c_stop_Nspm)
            # Parameters - Hydraulic
            elif v == 120: values.append(self.A_A_m2)
            elif v == 121: values.append(self.A_B_m2)
            elif v == 122: values.append(self.V0_A_m3)
            elif v == 123: values.append(self.V0_B_m3)
            # Parameters - Fluid
            elif v == 130: values.append(self.beta_eff_Pa)
            elif v == 131: values.append(self.leak_C_L)
            # Parameters - Supply
            elif v == 140: values.append(self.p_supply_Pa)
            elif v == 141: values.append(self.p_tank_Pa)
            # Parameters - Valve
            elif v == 150: values.append(self.Cq)
            elif v == 151: values.append(self.u_flow_sat)
            # Parameters - Friction
            elif v == 160: values.append(self.F_coulomb_N)
            elif v == 161: values.append(self.F_static_N)
            elif v == 162: values.append(self.v_stribeck_mps)
            elif v == 163: values.append(self.b_visc_Nspm)
            elif v == 164: values.append(self.v_tanh_mps)
            else: values.append(0.0)
        return values
    
    def set_real(self, vr, values):
        """Set real values by value references"""
        for i, v in enumerate(vr):
            val = values[i]
            # Inputs
            if v == 0: self.spool_u = val
            elif v == 1: self.load_force_N = val
            # States
            elif v == 20: self.x = val
            elif v == 21: self.v = val
            elif v == 22: self.pA = val
            elif v == 23: self.pB = val
            # Parameters - Geometry
            elif v == 100: self.stroke_m = val
            elif v == 101: self.x_min_m = val
            elif v == 102: self.x_max_m = val
            # Parameters - Mass and stops
            elif v == 110: self.m_kg = val
            elif v == 111: self.k_stop_Npm = val
            elif v == 112: self.c_stop_Nspm = val
            # Parameters - Hydraulic
            elif v == 120: self.A_A_m2 = val
            elif v == 121: self.A_B_m2 = val
            elif v == 122: self.V0_A_m3 = val
            elif v == 123: self.V0_B_m3 = val
            # Parameters - Fluid
            elif v == 130: self.beta_eff_Pa = val
            elif v == 131: self.leak_C_L = val
            # Parameters - Supply
            elif v == 140: self.p_supply_Pa = val
            elif v == 141: self.p_tank_Pa = val
            # Parameters - Valve
            elif v == 150: self.Cq = val
            elif v == 151: self.u_flow_sat = val
            # Parameters - Friction
            elif v == 160: self.F_coulomb_N = val
            elif v == 161: self.F_static_N = val
            elif v == 162: self.v_stribeck_mps = val
            elif v == 163: self.b_visc_Nspm = val
            elif v == 164: self.v_tanh_mps = val
    
    def _compute_outputs(self):
        """Compute output values from current state"""
        self.x_m = self.x
        self.v_mps = self.v
        self.pA_Pa = self.pA
        self.pB_Pa = self.pB
        self.rod_force_N = self.A_A_m2 * self.pA - self.A_B_m2 * self.pB
    
    def _friction(self, v):
        """Stribeck friction model with smooth tanh sign"""
        Fc = self.F_coulomb_N
        Fs = self.F_static_N
        vst = self.v_stribeck_mps
        vt = self.v_tanh_mps
        b = self.b_visc_Nspm
        
        # Stribeck + Coulomb + viscous
        F_stribeck = Fc + (Fs - Fc) * math.exp(-(abs(v) / vst) ** 2)
        return F_stribeck * math.tanh(v / vt) + b * v
    
    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        """FMI function: Perform one simulation step
        
        Uses semi-implicit Euler integration.
        Implements nonlinear hydraulic cylinder dynamics.
        """
        dt = communication_step_size
        
        # Unpack state
        x = self.x
        v = self.v
        pA = self.pA
        pB = self.pB
        
        # Unpack inputs
        u = clip(self.spool_u, -1.0, 1.0)
        FL = self.load_force_N
        
        # Valve opening factor
        alpha = clip(abs(u), 0.0, 1.0)
        
        # Chamber volumes (position-dependent)
        VA = max(1e-6, self.V0_A_m3 + self.A_A_m2 * x)
        VB = max(1e-6, self.V0_B_m3 + self.A_B_m2 * (self.stroke_m - x))
        
        # Supply and tank pressures
        pS = self.p_supply_Pa
        pT = self.p_tank_Pa
        
        # Internal leakage
        q_leak = self.leak_C_L * (pA - pB)
        
        # Flows depending on direction
        if u >= 0:
            # Extension mode: A -> supply, B -> tank
            qSA = self.Cq * alpha * phi_sqrt(pS - pA)
            qBT = self.Cq * alpha * phi_sqrt(pB - pT)
            dpA = (self.beta_eff_Pa / VA) * (qSA - self.A_A_m2 * v - q_leak)
            dpB = (self.beta_eff_Pa / VB) * (-qBT + self.A_B_m2 * v + q_leak)
        else:
            # Retraction mode: B -> supply, A -> tank
            qSB = self.Cq * alpha * phi_sqrt(pS - pB)
            qAT = self.Cq * alpha * phi_sqrt(pA - pT)
            dpA = (self.beta_eff_Pa / VA) * (-qAT - self.A_A_m2 * v - q_leak)
            dpB = (self.beta_eff_Pa / VB) * (qSB + self.A_B_m2 * v + q_leak)
        
        # Hydraulic force
        Fh = self.A_A_m2 * pA - self.A_B_m2 * pB
        
        # Friction force
        Ff = self._friction(v)
        
        # Soft stop force
        Fstop = 0.0
        if x < self.x_min_m:
            Fstop = self.k_stop_Npm * (self.x_min_m - x) - self.c_stop_Nspm * v
        elif x > self.x_max_m:
            Fstop = -self.k_stop_Npm * (x - self.x_max_m) - self.c_stop_Nspm * v
        
        # Acceleration
        dv = (Fh - Ff - FL + Fstop) / self.m_kg
        dx = v
        
        # Semi-implicit Euler: update velocities first
        v_new = v + dv * dt
        pA_new = pA + dpA * dt
        pB_new = pB + dpB * dt
        
        # Then update position using new velocity
        x_new = x + v_new * dt
        
        # Clamp pressures to physical bounds (with small margin)
        pA_new = clip(pA_new, pT * 0.5, pS * 1.05)
        pB_new = clip(pB_new, pT * 0.5, pS * 1.05)
        
        # Update state
        self.x = x_new
        self.v = v_new
        self.pA = pA_new
        self.pB = pB_new
        self.time = current_time + dt
        
        # Compute outputs
        self._compute_outputs()
        
        return 0  # OK status


# FMI 2.0 Co-Simulation entry points
_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = HydraulicCylinderPlant()
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