# CoolingLoop 行为模型（手工规格）

> 目标：把“泵+管路+散热器+风扇”抽象为一个带有执行器动态与非线性的冷却回路 FMU。
> 状态包含：冷却液平均温度、流量执行器状态（近似泵转速/流量）。

## 1. 状态、输入、输出

- 状态：
  - `coolant_temp_C`：回路平均冷却液温度 (°C)
  - `flow_state_kgps`：流量状态（执行器一阶响应后的实际流量）(kg/s)

- 输入：
  - `pump_cmd`、`fan_cmd`：0..1
  - `ambient_temp_C`
  - `T_batt_surface_C`
  - `heat_load_W`：来自电池的热负荷（正值为冷却液吸热）

- 输出：
  - `coolant_flow_kgps`：实际流量
  - `radiator_out_temp_C`：经散热器后的温度（作为进入电池的温度）
  - `coolant_in_temp_C`：等同 `radiator_out_temp_C`
  - `pump_power_W`

## 2. 非线性：流量-命令关系 + 执行器一阶滞后

设归一化泵命令 \(u_p = clip(pump\_cmd,0,1)\)。

期望流量采用平方关系（低开度更“钝”，体现非线性）：

\[
\dot m_{cmd} = \dot m_{max} \cdot u_p^2
\]

实际流量状态满足一阶滞后：

\[
\frac{d\dot m}{dt} = \frac{\dot m_{cmd} - \dot m}{\tau_p}
\]

其中：\(\tau_p\) 为 `pump_tau_s`。

## 3. 非线性：散热器 UA 随风扇命令变化

设 \(u_f = clip(fan\_cmd,0,1)\)。

用幂律模拟风扇提升换热（典型指数 0.7）：

\[
UA = UA_{base} + UA_{fan\_gain} \cdot u_f^{0.7}
\]

并裁剪：\(UA \leftarrow min(UA, UA_{max})\)。

## 4. 回路热平衡（集总能量）

将冷却回路等效为单一热容 \(C = m_{cool} c_p\)。

冷却液从电池吸热：\(Q_{in} = heat\_load\_W\)。

通过散热器向环境放热：

\[
Q_{rad} = UA \cdot (T_{cool} - T_{amb})
\]

则：

\[
\frac{dT_{cool}}{dt} = \frac{Q_{in} - Q_{rad}}{m_{cool} c_p}
\]

## 5. 散热器出口温度（代数近似）

为给电池提供“冷却液入口温度”，需要估计散热器出口温度。这里用一个与 UA、流量相关的指数形式（来自换热器有效度思想的简化）：

\[
\epsilon = 1 - \exp\left( -\frac{UA}{\max(\dot m, \epsilon_m) c_p}\right)
\]

\[
T_{out} = T_{cool} - \epsilon \cdot (T_{cool} - T_{amb})
\]

其中 \(\epsilon_m\) 是很小的防零常量（实现常量，例如 1e-4 kg/s）。

输出：

- `radiator_out_temp_C = T_out`
- `coolant_in_temp_C = T_out`

> 注意：这里 `coolant_temp_C` 是“回路平均温度”，而 `T_out` 是散热后进入电池的温度。二者差值由 \(\epsilon\) 体现。

## 6. 泵功耗（非线性）

泵功耗近似与命令三次方成正比：

\[
P_{pump} = P_{max} \cdot u_p^3
\]

输出 `pump_power_W`。

## 7. doStep 伪代码

```python
import math

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def doStep(dt, inputs, p, s):
    up = clip(inputs['pump_cmd'], 0.0, 1.0)
    uf = clip(inputs['fan_cmd'], 0.0, 1.0)
    Tamb = inputs['ambient_temp_C']
    Q_in = inputs['heat_load_W']  # W

    Tcool = s['coolant_temp_C']
    mdot = max(0.0, s['flow_state_kgps'])

    # 1) Flow actuator dynamics (nonlinear cmd mapping)
    mdot_cmd = p['flow_max_kgps'] * (up**2)
    dmdot = (mdot_cmd - mdot) / p['pump_tau_s']

    # 2) Radiator UA vs fan
    UA = p['UA_base_WpK'] + p['UA_fan_gain'] * (uf**0.7)
    UA = min(UA, p['UA_max_WpK'])

    # 3) Coolant thermal dynamics
    C = p['coolant_mass_kg'] * p['coolant_cp_JpkgK']
    Q_rad = UA * (Tcool - Tamb)
    dT = (Q_in - Q_rad) / C

    # Integrate
    mdot_new = max(0.0, mdot + dmdot*dt)
    Tcool_new = Tcool + dT*dt
    Tcool_new = clip(Tcool_new, p['T_min_C'], p['T_max_C'])

    # 4) Radiator outlet temperature (effective heat exchanger)
    eps_m = 1e-4
    eps = 1.0 - math.exp(-UA / (max(mdot_new, eps_m) * p['coolant_cp_JpkgK']))
    T_out = Tcool_new - eps * (Tcool_new - Tamb)

    P_pump = p['pump_power_max_W'] * (up**3)

    states_new = {'coolant_temp_C': Tcool_new, 'flow_state_kgps': mdot_new}
    outputs = {
        'coolant_flow_kgps': mdot_new,
        'radiator_out_temp_C': T_out,
        'coolant_in_temp_C': T_out,
        'pump_power_W': P_pump
    }
    return states_new, outputs
```

## 8. 备注

- 该 FMU 同时包含多状态（2 个）与非线性（平方流量、幂律 UA、指数有效度、饱和裁剪）。
- 连接错误（例如把 heat_load_W 接错成温度）会导致 Tcool 或 T_out 出现明显异常。
