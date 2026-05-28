# PendulumController 行为模型

## 控制目标

- 使倒立摆保持直立：\(\theta \to \theta_{ref}\)（通常为0）
- 同时将小车位置跟踪到 \(x_{ref}\)
- 在执行器饱和下仍保持可用的闭环行为（抗积分饱和）

## 状态、非线性与多状态特性

控制器包含 3 个连续状态：
- \(I_\theta\)（`int_theta`）：摆角误差积分
- \(I_x\)（`int_x`）：位置误差积分
- \(F_a\)（`force_act_N`）：执行器输出力（对指令力的一阶滞后）

非线性环节：
- 输出饱和：\(\mathrm{sat}(\cdot,\pm u_{max})\)
- 死区：\(|u| < deadzone\Rightarrow u=0\)

## 数学关系

误差：
\[
 e_\theta = \theta_{ref} - \theta,\quad e_x = x_{ref} - x
\]

未饱和的“期望力”指令：
\[
 u_{raw} = K_{p\theta} e_\theta - K_{d\theta} \dot\theta + K_{i\theta} I_\theta 
        + K_{px} e_x - K_{dx} \dot x + K_{ix} I_x
\]

饱和：
\[
 u_{sat} = \mathrm{clip}(u_{raw}, -u_{max}, +u_{max})
\]

死区（对饱和后的结果）：
\[
 u_{dz} = \begin{cases}
 0, & |u_{sat}| < deadzone \\
 u_{sat}, & \text{otherwise}
\end{cases}
\]

抗积分饱和（back-calculation）：令 \(k_{aw}=\) `antiwindup_gain`。

\[
\dot I_\theta = e_\theta + k_{aw}(u_{sat}-u_{raw})\cdot w_\theta
\]
\[
\dot I_x = e_x + k_{aw}(u_{sat}-u_{raw})\cdot w_x
\]

其中 \(w_\theta,w_x\) 为分配权重（为了简单可取常数，例如 \(w_\theta=1\), \(w_x=0.2\)；表示优先稳定角度，位置积分较弱）。

执行器一阶滞后：\(\tau=\) `actuator_tau_s`
\[
\dot F_a = \frac{u_{dz} - F_a}{\tau}
\]

输出：
\[
 force\_cmd = F_a
\]

## doStep 伪代码

```python

def clip(x, lo, hi):
    return max(lo, min(hi, x))


def doStep(dt, inputs, p, s):
    x_ref = inputs['x_ref_m']
    th_ref = inputs['theta_ref_rad']

    x = inputs['x_m']
    xdot = inputs['x_dot_mps']
    th = inputs['theta_rad']
    thdot = inputs['theta_dot_radps']

    e_th = th_ref - th
    e_x = x_ref - x

    I_th = s['int_theta']
    I_x = s['int_x']
    F_a = s['force_act_N']

    # raw (unsaturated) command
    u_raw = (
        p['Kp_theta'] * e_th
        - p['Kd_theta'] * thdot
        + p['Ki_theta'] * I_th
        + p['Kp_x'] * e_x
        - p['Kd_x'] * xdot
        + p['Ki_x'] * I_x
    )

    # saturation
    u_sat = clip(u_raw, -p['u_max_N'], p['u_max_N'])

    # deadzone
    if abs(u_sat) < p['deadzone_N']:
        u_dz = 0.0
    else:
        u_dz = u_sat

    # anti-windup back calculation (angle prioritized)
    kaw = p['antiwindup_gain']
    w_th = 1.0
    w_x = 0.2

    dI_th = e_th + kaw * (u_sat - u_raw) * w_th
    dI_x = e_x + kaw * (u_sat - u_raw) * w_x

    # actuator lag
    tau = max(1e-4, p['actuator_tau_s'])
    dF_a = (u_dz - F_a) / tau

    # integrate
    I_th_new = I_th + dI_th * dt
    I_x_new = I_x + dI_x * dt
    F_a_new = F_a + dF_a * dt

    states_new = {
        'int_theta': I_th_new,
        'int_x': I_x_new,
        'force_act_N': F_a_new
    }

    outputs = {'force_cmd_N': F_a_new}
    return states_new, outputs
```

参数调节提示：
- \(Kp_\theta,Kd_\theta\) 主导快速稳定；\(Ki_\theta\) 用于消除偏置/扰动稳态误差。
- \(Kp_x,Kd_x,Ki_x\) 控制位置回归速度，但过大可能引入对角度的激励。
- `u_max_N` 过小会导致无法稳住倒立摆；过大在真实系统会受限于电机能力。
