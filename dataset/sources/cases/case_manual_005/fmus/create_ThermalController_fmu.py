#!/usr/bin/env python3
"""Generate ThermalController FMU (FMI 2.0 Co-Simulation)

Implements the behavior described in:
- fmu_specs/fmu_ThermalController.json
- fmu_specs/fmu_ThermalController.md

Controller summary:
- Hysteresis-gated PI control
- Saturation with anti-windup (back-calculation)
- Output slew-rate limit implemented via internal state

States:
- integrator
- u_cmd_state

Inputs:
- enable (Boolean)
- temp_ref_C (Real)
- temp_cell_C (Real)
- coolant_temp_C (Real)

Outputs:
- pump_cmd (Real 0..1)
- sat_flag (Boolean)

Packaging:
- Python FMU style: sources/model.py + modelDescription.xml inside the .fmu (zip)
"""

import tempfile
import zipfile
from pathlib import Path

MODEL_NAME = "ThermalController"
GUID = "{e6b5af40-9c60-4f21-a9d9-3e2fa18b9e0b}"

MODEL_DESCRIPTION = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{MODEL_NAME}"
  guid="{GUID}"
  generationTool="Python-FMPy"
  generationDateAndTime="2026-03-09T02:04:00Z"
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
    <Unit name="1/C"><BaseUnit K="-1"/></Unit>
    <Unit name="1/(C*s)"><BaseUnit K="-1" s="-1"/></Unit>
  </UnitDefinitions>

  <LogCategories>
    <Category name="logAll"/>
    <Category name="logError"/>
    <Category name="logFmiCall"/>
    <Category name="logEvent"/>
  </LogCategories>

  <DefaultExperiment startTime="0" stopTime="900" stepSize="0.1"/>

  <ModelVariables>
    <!-- Inputs -->
    <ScalarVariable name="enable" valueReference="0" causality="input" variability="continuous">
      <Boolean start="true"/>
    </ScalarVariable>

    <ScalarVariable name="temp_ref_C" valueReference="1" causality="input" variability="continuous">
      <Real unit="C" start="35.0"/>
    </ScalarVariable>
    <ScalarVariable name="temp_cell_C" valueReference="2" causality="input" variability="continuous">
      <Real unit="C" start="30.0"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_temp_C" valueReference="3" causality="input" variability="continuous">
      <Real unit="C" start="28.0"/>
    </ScalarVariable>

    <!-- Outputs -->
    <ScalarVariable name="pump_cmd" valueReference="10" causality="output" variability="continuous" initial="calculated">
      <Real unit="1"/>
    </ScalarVariable>
    <ScalarVariable name="sat_flag" valueReference="11" causality="output" variability="continuous" initial="calculated">
      <Boolean/>
    </ScalarVariable>

    <!-- States -->
    <ScalarVariable name="integrator" valueReference="20" causality="local" variability="continuous" initial="exact">
      <Real unit="1" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_cmd_state" valueReference="21" causality="local" variability="continuous" initial="exact">
      <Real unit="1" start="0.2"/>
    </ScalarVariable>

    <!-- Parameters -->
    <ScalarVariable name="kp" valueReference="100" causality="parameter" variability="fixed">
      <Real unit="1/C" start="0.08"/>
    </ScalarVariable>
    <ScalarVariable name="ki" valueReference="101" causality="parameter" variability="fixed">
      <Real unit="1/(C*s)" start="0.010"/>
    </ScalarVariable>
    <ScalarVariable name="u_min" valueReference="102" causality="parameter" variability="fixed">
      <Real unit="1" start="0.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_max" valueReference="103" causality="parameter" variability="fixed">
      <Real unit="1" start="1.0"/>
    </ScalarVariable>

    <ScalarVariable name="hys_band_C" valueReference="104" causality="parameter" variability="fixed">
      <Real unit="C" start="0.8"/>
    </ScalarVariable>
    <ScalarVariable name="coolant_overtemp_C" valueReference="105" causality="parameter" variability="fixed">
      <Real unit="C" start="60.0"/>
    </ScalarVariable>
    <ScalarVariable name="u_slew_per_s" valueReference="106" causality="parameter" variability="fixed">
      <Real unit="1/s" start="0.8"/>
    </ScalarVariable>
  </ModelVariables>

  <ModelStructure>
    <Outputs>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </Outputs>
    <Derivatives>
      <Unknown index="7" dependencies=""/>
      <Unknown index="8" dependencies=""/>
    </Derivatives>
    <InitialUnknowns>
      <Unknown index="5"/>
      <Unknown index="6"/>
    </InitialUnknowns>
  </ModelStructure>
</fmiModelDescription>
'''

MODEL_PY = '''#!/usr/bin/env python3
"""ThermalController FMU Model Implementation (FMI 2.0 Co-Simulation)

Based on spec pseudocode.

Error definition:
  e = T_cell - T_ref

Hysteresis gating:
  g = 0 if |e| <= hys_band else 1

PI with anti-windup (back-calculation):
  nu = kp*e + xi
  u = clip(nu, u_min, u_max)
  dxi = g*ki*e + kaw*(u - nu), kaw = ki/max(kp, eps)

Protection:
  if coolant_temp_C > coolant_overtemp_C: u = u_max

Output slew-rate state:
  dus = clip(u - us, -u_slew_per_s, u_slew_per_s)
  us <- clip(us + dus*dt, u_min, u_max)

Outputs:
  pump_cmd = us
  sat_flag indicates saturation / protection activity

Integration: forward Euler.
"""


def clip(x, lo, hi):
    return max(lo, min(hi, x))


class ThermalController:

    def __init__(self):
        # Parameters (defaults from spec)
        self.kp = 0.08
        self.ki = 0.010
        self.u_min = 0.0
        self.u_max = 1.0
        self.hys_band_C = 0.8
        self.coolant_overtemp_C = 60.0
        self.u_slew_per_s = 0.8

        # States
        self.integrator = 0.0
        self.u_cmd_state = 0.2

        # Inputs
        self.enable = True
        self.temp_ref_C = 35.0
        self.temp_cell_C = 30.0
        self.coolant_temp_C = 28.0

        # Outputs
        self.pump_cmd = 0.0
        self.sat_flag = False

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
        values = []
        for v in vr:
            # inputs (reals)
            if v == 1: values.append(self.temp_ref_C)
            elif v == 2: values.append(self.temp_cell_C)
            elif v == 3: values.append(self.coolant_temp_C)
            # outputs (reals)
            elif v == 10: values.append(self.pump_cmd)
            # states
            elif v == 20: values.append(self.integrator)
            elif v == 21: values.append(self.u_cmd_state)
            # parameters
            elif v == 100: values.append(self.kp)
            elif v == 101: values.append(self.ki)
            elif v == 102: values.append(self.u_min)
            elif v == 103: values.append(self.u_max)
            elif v == 104: values.append(self.hys_band_C)
            elif v == 105: values.append(self.coolant_overtemp_C)
            elif v == 106: values.append(self.u_slew_per_s)
            else: values.append(0.0)
        return values

    def set_real(self, vr, values):
        for i, v in enumerate(vr):
            val = values[i]
            # inputs
            if v == 1: self.temp_ref_C = val
            elif v == 2: self.temp_cell_C = val
            elif v == 3: self.coolant_temp_C = val
            # states
            elif v == 20: self.integrator = val
            elif v == 21: self.u_cmd_state = val
            # parameters
            elif v == 100: self.kp = val
            elif v == 101: self.ki = val
            elif v == 102: self.u_min = val
            elif v == 103: self.u_max = val
            elif v == 104: self.hys_band_C = val
            elif v == 105: self.coolant_overtemp_C = val
            elif v == 106: self.u_slew_per_s = val

    def get_boolean(self, vr):
        values = []
        for v in vr:
            if v == 0: values.append(bool(self.enable))
            elif v == 11: values.append(bool(self.sat_flag))
            else: values.append(False)
        return values

    def set_boolean(self, vr, values):
        for i, v in enumerate(vr):
            val = values[i]
            if v == 0:
                self.enable = bool(val)

    def _compute_outputs(self):
        # Hold last state-based output
        self.pump_cmd = clip(self.u_cmd_state, self.u_min, self.u_max)
        # sat_flag is computed in do_step; keep as-is here

    def do_step(self, current_time, communication_step_size, no_set_fmu_state_prior_to_current_point=False):
        dt = communication_step_size

        en = bool(self.enable)

        # states
        xi = self.integrator
        us = self.u_cmd_state

        if not en:
            # Disabled: clear integrator, slew command toward minimum
            xi_new = 0.0
            r = abs(self.u_slew_per_s)
            dus = clip(self.u_min - us, -r, r)
            us_new = clip(us + dus * dt, self.u_min, self.u_max)

            self.integrator = xi_new
            self.u_cmd_state = us_new
            self.pump_cmd = us_new
            self.sat_flag = False
            self.time = current_time + dt
            return 0

        # inputs
        Tref = self.temp_ref_C
        T = self.temp_cell_C
        Tcool = self.coolant_temp_C

        e = T - Tref

        # hysteresis gating
        g = 0.0 if abs(e) <= abs(self.hys_band_C) else 1.0

        # PI raw
        nu = self.kp * e + xi

        # saturation
        u = clip(nu, self.u_min, self.u_max)
        sat = (abs(u - nu) > 1e-12)

        # coolant overtemp protection
        if Tcool > self.coolant_overtemp_C:
            u = self.u_max
            sat = True

        # anti-windup
        kp = self.kp
        ki = self.ki
        kaw = ki / max(1e-6, abs(kp))
        dxi = g * ki * e + kaw * (u - nu)
        xi_new = xi + dxi * dt

        # output slew-rate
        r = abs(self.u_slew_per_s)
        dus = clip(u - us, -r, r)
        us_new = clip(us + dus * dt, self.u_min, self.u_max)

        # commit
        self.integrator = xi_new
        self.u_cmd_state = us_new
        self.pump_cmd = us_new
        self.sat_flag = bool(sat)
        self.time = current_time + dt
        return 0


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
