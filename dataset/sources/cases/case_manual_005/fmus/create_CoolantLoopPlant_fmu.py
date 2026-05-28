#!/usr/bin/env python3
"""Generate CoolantLoopPlant FMU (FMI 2.0 Co-Simulation) using Python + FMPy-style Python FMU packaging.

Implements the behavior described in:
- fmu_specs/fmu_CoolantLoopPlant.json
- fmu_specs/fmu_CoolantLoopPlant.md

Model summary:
- States: coolant_temp_C, pump_state
- Inputs: pump_cmd (0..1), ambient_temp_C, heat_in_W
- Outputs: coolant_temp_C, heat_removed_W

Integration:
- Forward Euler in do_step()

Note:
This FMU is packaged as a "Python FMU" (sources/model.py + modelDescription.xml).
"""

import tempfile
import zipfile
from pathlib import Path

MODEL_NAME = "CoolantLoopPlant"
GUID = "{c0a7b35b-6af4-4f7f-a6e2-0e1f0e3d9a15}"

MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T01:34:00Z"
  variableNamingConvention="structured">

  <ModelExchange modelIdentifier="{MODEL_NAME}"/>
  <CoSimulation modelIdentifier="{MODEL_NAME}">
    <SourceFiles>
      <File name="model.py"/>
    </SourceFiles>
  </CoSimulation>

  <UnitDefinitions>
    <Unit name="1"><BaseUnit/></Unit>
    <Unit name="s"><BaseUnit s="1"/></Unit>
    <Unit name="1/s"><BaseUnit s="-1"/></Unit>
    <Unit name="C"><BaseUnit K="1" offset="273.15"/></Unit>
    <Unit name="W"><BaseUnit kg="1" m="2" s="-3"/></Unit>
    <Unit name="J/K"><BaseUnit kg="1" m="2" s="-2" K="-1"/></Unit>
    <Unit name="W/K"><BaseUnit kg="1" m="2" s="-3" K="-1"/></Unit>
  </UnitDefinitions>
  
  <LogCategories>
    <Category name="logAll"/>
    <Category name="logError"/>
    <Category name="logFmiCall"/>
    <Category name="logEvent"/>
  </LogCategories>

  <DefaultExperiment startTime="0" stopTime="3600" stepSize="0.1"/>

  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="pump_cmd" valueReference="0" causality="input" variability="continuous">
      <Real unit="1" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="ambient_temp_C" valueReference="1" causality="input" variability="continuous">
      <Real unit="C" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="heat_in_W" valueReference="2" causality="input" variability="continuous">
      <Real unit="W" start="0.0"/>
    </ScalarVariable>

    <!-- Outputs -->
    <ScalarVariable name="coolant_temp_C" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="C"/>
    </ScalarVariable>
    <ScalarVariable name="heat_removed_W" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Real unit="W"/>
    </ScalarVariable>

    <!-- States -->
    <ScalarVariable name="coolant_temp_C_state" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="C" start="25.0"/>
    </ScalarVariable>
    <ScalarVariable name="pump_state_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="1" start="0.0"/>
    </ScalarVariable>

    <!-- Parameters -->
    <ScalarVariable name="coolant_thermal_mass_JK" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="J/K" start="18000.0"/>
    </ScalarVariable>
    <ScalarVariable name="ua_min_WK" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="W/K" start="40.0"/>
    </ScalarVariable>
    <ScalarVariable name="ua_max_WK" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="W/K" start="320.0"/>
    </ScalarVariable>
    <ScalarVariable name="ua_shape" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="1" start="2.2"/>
    </ScalarVariable>

    <ScalarVariable name="pump_tau_s" valueReference="110" causality="parameter" variability="fixed">
      <Real unit="s" start="2.5"/>
    </ScalarVariable>
    <ScalarVariable name="pump_rate_limit_per_s" valueReference="111" causality="parameter" variability="fixed">
      <Real unit="1/s" start="0.6"/>
    </ScalarVariable>

    <ScalarVariable name="temp_min_C" valueReference="120" causality="parameter" variability="fixed">
      <Real unit="C" start="-20.0"/>
    </ScalarVariable>
    <ScalarVariable name="temp_max_C" valueReference="121" causality="parameter" variability="fixed">
      <Real unit="C" start="120.0"/>
    </ScalarVariable>
  </ModelVariables>

  <ModelStructure>
    <Outputs>
      <Unknown index="4"/>
      <Unknown index="5"/>
    </Outputs>
    <Derivatives>
      <Unknown index="6" dependencies=""/>
      <Unknown index="7" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="4"/>
      <Unknown index="5"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

MODEL_PY = '''#!/usr/bin/env python3
"""CoolantLoopPlant FMU Model Implementation (FMI 2.0 Co-Simulation)

Equations (see spec markdown):
- Pump actuator (with rate limit):
    dup = clip((u - up)/tau_p, -r_lim, r_lim)
    up_new = clip(up + dup*dt, 0, 1)

- UA nonlinearity:
    UA = ua_min + (ua_max-ua_min)*(1 - exp(-2*(up_new**ua_shape)))

- Heat removed:
    Qrem = UA*(Tc - Tamb)

- Coolant temperature:
    dTc = (Qin - Qrem)/C_c
    Tc_new = clip(Tc + dTc*dt, T_min, T_max)

Integration: forward Euler
"""

import math


def clip(x, lo, hi):
    return max(lo, min(hi, x))


class CoolantLoopPlant:

    def __init__(self):
        # Parameters (defaults from spec)
        self.coolant_thermal_mass_JK = 18000.0
        self.ua_min_WK = 40.0
        self.ua_max_WK = 320.0
        self.ua_shape = 2.2

        self.pump_tau_s = 2.5
        self.pump_rate_limit_per_s = 0.6

        self.temp_min_C = -20.0
        self.temp_max_C = 120.0

        # States
        self.coolant_temp_C = 25.0
        self.pump_state = 0.0

        # Inputs
        self.pump_cmd = 0.0
        self.ambient_temp_C = 25.0
        self.heat_in_W = 0.0

        # Outputs
        self.heat_removed_W = 0.0

        self.time = 0.0

    def set_debug_logging(self, categories, logging_on):
        pass

    def setup_experiment(self, start_time, stop_time=None, tolerance=None):
        self.time = start_time

    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        self._compute_outputs()

    def terminate(self):
        pass

    def reset(self):
        self.__init__()

    def get_real(self, vr):
        out = []
        for v in vr:
            # inputs
            if v == 0: out.append(self.pump_cmd)
            elif v == 1: out.append(self.ambient_temp_C)
            elif v == 2: out.append(self.heat_in_W)
            # outputs
            elif v == 10: out.append(self.coolant_temp_C)
            elif v == 11: out.append(self.heat_removed_W)
            # states
            elif v == 20: out.append(self.coolant_temp_C)
            elif v == 21: out.append(self.pump_state)
            # parameters
            elif v == 100: out.append(self.coolant_thermal_mass_JK)
            elif v == 101: out.append(self.ua_min_WK)
            elif v == 102: out.append(self.ua_max_WK)
            elif v == 103: out.append(self.ua_shape)
            elif v == 110: out.append(self.pump_tau_s)
            elif v == 111: out.append(self.pump_rate_limit_per_s)
            elif v == 120: out.append(self.temp_min_C)
            elif v == 121: out.append(self.temp_max_C)
            else: out.append(0.0)
        return out

    def set_real(self, vr, values):
        for i, v in enumerate(vr):
            val = values[i]
            # inputs
            if v == 0: self.pump_cmd = val
            elif v == 1: self.ambient_temp_C = val
            elif v == 2: self.heat_in_W = val
            # states
            elif v == 20: self.coolant_temp_C = val
            elif v == 21: self.pump_state = val
            # parameters
            elif v == 100: self.coolant_thermal_mass_JK = val
            elif v == 101: self.ua_min_WK = val
            elif v == 102: self.ua_max_WK = val
            elif v == 103: self.ua_shape = val
            elif v == 110: self.pump_tau_s = val
            elif v == 111: self.pump_rate_limit_per_s = val
            elif v == 120: self.temp_min_C = val
            elif v == 121: self.temp_max_C = val

    def _compute_outputs(self):
        # compute UA with current pump_state (already clamped)
        up = clip(self.pump_state, 0.0, 1.0)
        UA = self.ua_min_WK + (self.ua_max_WK - self.ua_min_WK) * (1.0 - math.exp(-2.0 * (up ** self.ua_shape)))

        Tc = self.coolant_temp_C
        Tamb = self.ambient_temp_C
        self.heat_removed_W = UA * (Tc - Tamb)

    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        dt = communication_step_size

        # inputs
        u = clip(self.pump_cmd, 0.0, 1.0)
        Tamb = self.ambient_temp_C
        Qin = self.heat_in_W

        # states
        Tc = self.coolant_temp_C
        up = clip(self.pump_state, 0.0, 1.0)

        # pump actuator dynamics + rate limit
        tau = max(1e-6, self.pump_tau_s)
        dup = (u - up) / tau
        rlim = abs(self.pump_rate_limit_per_s)
        dup = clip(dup, -rlim, rlim)
        up_new = clip(up + dup * dt, 0.0, 1.0)

        # UA nonlinearity
        UA = self.ua_min_WK + (self.ua_max_WK - self.ua_min_WK) * (1.0 - math.exp(-2.0 * (up_new ** self.ua_shape)))

        # heat removed (use Tc at current step, consistent with spec pseudocode)
        Qrem = UA * (Tc - Tamb)

        # coolant temperature dynamics
        Cc = max(1e-6, self.coolant_thermal_mass_JK)
        dTc = (Qin - Qrem) / Cc
        Tc_new = clip(Tc + dTc * dt, self.temp_min_C, self.temp_max_C)

        # update
        self.pump_state = up_new
        self.coolant_temp_C = Tc_new
        self.ambient_temp_C = Tamb
        self.time = current_time + dt

        # outputs
        self.heat_removed_W = Qrem

        return 0


_instance = None


def instantiate(model_instance, fmu_type, fmu_resource_location, visible, logging_on):
    global _instance
    _instance = CoolantLoopPlant()
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


def create_fmu(output_path: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        sources_dir = tmpdir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)

        (tmpdir / "modelDescription.xml").write_text(MODEL_DESCRIPTION, encoding="utf-8")
        (sources_dir / "model.py").write_text(MODEL_PY, encoding="utf-8")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmpdir / "modelDescription.xml", "modelDescription.xml")
            zf.write(sources_dir / "model.py", "sources/model.py")

        print(f"Created FMU: {out}")
        return str(out)


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    create_fmu(out_dir / f"{MODEL_NAME}.fmu")
