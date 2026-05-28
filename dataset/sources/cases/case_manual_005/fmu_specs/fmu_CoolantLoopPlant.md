# CoolantLoopPlant 行为模型

该 FMU 表示一个“冷却回路 + 散热器”的聚合模型：
- 状态包含冷却液温度 $T_c$ 以及泵内部状态 $u_p$（执行器惯性 + 限速）。
- 非线性：散热能力用 $UA(u_p)$ 表示，随泵速上升而增加但最终饱和。

## 变量

- 输入：
  - $u$：泵命令（0..1）
  - $T_{amb}$：环境温度（°C）
  - $\dot Q_{in}$：进入回路的热量（W）
- 状态：
  - $T_c$：冷却液代表温度（°C）
  - $u_p$：泵内部状态（0..1），跟随命令但有惯性/限速
- 输出：
  - $T_c$：冷却液温度
  - $\dot Q_{rem}$：散热器移除热量（W）

## 泵执行器（惯性 + 限速）

一阶惯性：
\[
\dot u_p = \frac{u - u_p}{\tau_p}
\]

并对 $\dot u_p$ 做限速：
\[
\dot u_p \leftarrow \mathrm{clip}(\dot u_p, -r_{lim}, r_{lim})
\]

且 $u_p \in [0,1]$。

## 非线性 UA 模型

将 UA 随泵状态提高而增加，但趋于饱和：

\[
UA(u_p) = UA_{min} + (UA_{max} - UA_{min})\cdot \left(1 - e^{-k\,u_p^{\alpha}}\right)
\]

- $\alpha$（`ua_shape`）控制曲率。
- 该形式在低泵速时增长较快/较慢可调，在 $u_p\to 1$ 时饱和。

## 冷却液温度动力学

能量平衡：
\[
C_c\,\dot T_c = \dot Q_{in} - \dot Q_{rem}
\]

散热器向环境移除：
\[
\dot Q_{rem} = UA(u_p)\,(T_c - T_{amb})
\]

因此：
\[
\dot T_c = \frac{\dot Q_{in} - UA(u_p)(T_c - T_{amb})}{C_c}
\]

温度做数值保护：$T_c\leftarrow\mathrm{clip}(T_c, T_{min}, T_{max})$。

## 伪代码

```python
import math

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def doStep(dt, inputs, p, x):
    u = clip(inputs['pump_cmd'], 0.0, 1.0)
    Tamb = inputs['ambient_temp_C']
    Qin = inputs['heat_in_W']

    Tc = x['coolant_temp_C']
    up = clip(x['pump_state'], 0.0, 1.0)

    # pump actuator
    dup = (u - up) / p['pump_tau_s']
    dup = clip(dup, -p['pump_rate_limit_per_s'], p['pump_rate_limit_per_s'])
    up_new = clip(up + dup*dt, 0.0, 1.0)

    # UA nonlinearity
    UA = p['ua_min_WK'] + (p['ua_max_WK'] - p['ua_min_WK']) * (1.0 - math.exp(-2.0 * (up_new ** p['ua_shape'])))

    Qrem = UA * (Tc - Tamb)

    dTc = (Qin - Qrem) / p['coolant_thermal_mass_JK']
    Tc_new = clip(Tc + dTc*dt, p['temp_min_C'], p['temp_max_C'])

    states = {'coolant_temp_C': Tc_new, 'pump_state': up_new}
    outputs = {'coolant_temp_C': Tc_new, 'heat_removed_W': Qrem}
    return states, outputs
```
