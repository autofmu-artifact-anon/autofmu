# ThermalController 行为模型

该 FMU 是一个用于电池热管理的控制器：
- 输入电芯温度 $T$ 与目标温度 $T_{ref}$。
- 使用带迟滞的 PI：当温度误差落在迟滞带内时弱化/冻结积分，避免泵命令抖动。
- 输出 `pump_cmd` 在 0..1，并带输出限速（slew-rate）。

## 控制律

定义误差：
\[
e = T - T_{ref}
\]

### 迟滞逻辑（非线性）

设迟滞带宽 $b$：
- 若 $e > +b$：需要增强冷却（正常 PI）
- 若 $e < -b$：允许降低冷却（但不强制为 0，可让 PI 输出下降）
- 若 $|e| \le b$：进入“保持区”，冻结积分或衰减积分以减少抖动

可实现为一个门控因子 $g(e)$：
\[
 g(e) = \begin{cases}
 1, & |e| > b \\
 0, & |e| \le b
 \end{cases}
\]

### PI + 抗积分饱和

未限幅的控制量：
\[
u = k_p e + x_i\]

其中积分状态：
\[
\dot x_i = g(e)\,k_i\,e + k_{aw}(u - \nu)
\]

- $u$ 是限幅后的命令（见下）
- $k_{aw}$ 为抗饱和回算增益（可取 $k_{aw}=k_i/k_p$ 或常数）

限幅：
\[
 u = \mathrm{clip}(\nu, u_{min}, u_{max})
\]

### 输出限速

最终输出以内部一阶/限速状态 $u_s$ 表示：
\[
\dot u_s = \mathrm{clip}(u - u_s, -r_{slew}, r_{slew})
\]

输出：`pump_cmd = clip(u_s, u_min, u_max)`。

### 保护前馈（冷却液过温）

若 $T_{cool} > T_{cool,max}$，强制：
\[
 u \leftarrow u_{max}
\]

## 伪代码

```python
import math

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def doStep(dt, inputs, p, x):
    en = bool(inputs['enable'])
    Tref = inputs['temp_ref_C']
    T = inputs['temp_cell_C']
    Tcool = inputs['coolant_temp_C']

    xi = x['integrator']
    us = x['u_cmd_state']

    if not en:
        # 失能：缓慢回到低泵速，积分清零
        xi_new = 0.0
        us_new = clip(us + clip(p['u_min'] - us, -p['u_slew_per_s'], p['u_slew_per_s']) * dt, p['u_min'], p['u_max'])
        return {'integrator': xi_new, 'u_cmd_state': us_new}, {'pump_cmd': us_new, 'sat_flag': False}

    e = T - Tref

    # hysteresis gating
    g = 0.0 if abs(e) <= p['hys_band_C'] else 1.0

    nu = p['kp'] * e + xi

    # saturation
    u = clip(nu, p['u_min'], p['u_max'])
    sat = (u != nu)

    # coolant overtemp protection
    if Tcool > p['coolant_overtemp_C']:
        u = p['u_max']
        sat = True

    # anti-windup (simple back-calculation)
    kaw = (p['ki'] / max(1e-6, p['kp']))
    dxi = g * p['ki'] * e + kaw * (u - nu)
    xi_new = xi + dxi * dt

    # output slew-rate
    dus = clip(u - us, -p['u_slew_per_s'], p['u_slew_per_s'])
    us_new = clip(us + dus * dt, p['u_min'], p['u_max'])

    states = {'integrator': xi_new, 'u_cmd_state': us_new}
    outputs = {'pump_cmd': us_new, 'sat_flag': sat}
    return states, outputs
```
