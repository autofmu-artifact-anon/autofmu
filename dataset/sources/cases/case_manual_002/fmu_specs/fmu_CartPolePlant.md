# CartPolePlant 行为模型

## 目的

模拟小车-倒立摆的连续时间非线性动力学，并在 FMU 内部体现一些现实因素：
- 电机/执行器饱和 + 一阶滞后
- 非线性摩擦（库仑 + 粘性，tanh 平滑）
- 轨道软限位（超出位置范围后的非线性弹簧力）
- 简化传感器：角度测量噪声、角速度测量偏置

角度约定：\(\theta=0\) 为下垂，\(\theta=\pi\) 为倒立。

## 状态

- \(x\) (m): 小车位置
- \(\dot x\) (m/s): 小车速度
- \(\theta\) (rad): 杆角度
- \(\dot\theta\) (rad/s): 杆角速度
- \(F_{act}\) (N): 执行器实际输出力（用于建模一阶滞后）

## 执行器与饱和（非线性）

指令力：\(F_{cmd}\)；饱和：

\[
F_{sat} = \mathrm{clamp}(F_{cmd}, -F_{max}, F_{max})
\]

执行器一阶动态：

\[
\dot F_{act} = \frac{F_{sat} - F_{act}}{\tau_{act}}
\]

总输入力包含外扰：

\[
F = F_{act} + F_{dist}
\]

## 摩擦（非线性）

小车摩擦力（方向与速度相反）：

\[
F_{fric} = c_c \tanh\left(\frac{\dot x}{v_0}\right) + c_v \dot x
\]

其中 \(c_c\) 是库仑摩擦等效幅值，\(v_0\) 用于平滑零速附近的符号函数。

## 软限位（非线性）

若 \(|x| > x_{limit}\)，施加恢复力：

\[
F_{lim} = -k_{lim} \cdot (|x|-x_{limit}) \cdot \mathrm{sign}(x)
\]

否则 \(F_{lim}=0\)。

## Cart-Pole 动力学（非线性多状态）

采用常见的 cart-pole 连续时间模型（含杆转动惯量）。令：
- \(M\): 小车质量
- \(m\): 杆质量
- \(l\): 转轴到杆质心距离
- \(I\): 杆绕质心惯量
- \(g\): 重力

定义
\[
\alpha = I + m l^2
\]
\[
S = \sin\theta,\quad C = \cos\theta
\]

加入摩擦与限位后，小车受力项：
\[
F_{eff} = F - F_{fric} + F_{lim}
\]

耦合方程（可视作从拉格朗日方程整理得到的一种写法）：

\[
(M+m) \ddot x + m l (\ddot\theta C - \dot\theta^2 S) = F_{eff}
\]
\[
\alpha \ddot\theta + m l \ddot x C = m g l S
\]

解出 \(\ddot x, \ddot\theta\)（实现中建议直接解 2x2 线性方程组）：

\[
\begin{bmatrix}
M+m & m l C \\
m l C & \alpha
\end{bmatrix}
\begin{bmatrix}
\ddot x\\
\ddot\theta
\end{bmatrix}
=
\begin{bmatrix}
F_{eff} + m l \dot\theta^2 S\\
 m g l S
\end{bmatrix}
\]

## 传感器输出（带噪声/偏置）

- \(\theta_{meas} = \mathrm{wrapToPi}(\theta + n_\theta)\)
- \(\dot\theta_{meas} = \dot\theta + b_{\dot\theta} + n_{\dot\theta}\)

其中 \(n_\theta\sim\mathcal N(0,\sigma_\theta^2)\)，\(n_{\dot\theta}\sim\mathcal N(0,\sigma_{\dot\theta}^2)\)，\(b_{\dot\theta}\) 为常值偏置参数。

## 实现伪代码

```python
import math

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

def wrap_to_pi(a):
    # map to (-pi, pi]
    while a <= -math.pi:
        a += 2*math.pi
    while a > math.pi:
        a -= 2*math.pi
    return a


def doStep(dt, inputs, p, s, rng):
    F_cmd = inputs['force_cmd_N']
    F_dist = inputs['disturbance_force_N']

    # actuator
    F_sat = clamp(F_cmd, -p['F_max_N'], p['F_max_N'])
    dF_act = (F_sat - s['F_act_N']) / p['actuator_tau_s']
    F_act_new = s['F_act_N'] + dF_act * dt

    # friction
    x_dot = s['x_dot_mps']
    F_fric = p['cart_fric_coulomb_N'] * math.tanh(x_dot / p['fric_smooth_v0_mps']) \
             + p['cart_fric_visc_Ns_per_m'] * x_dot

    # soft limit
    x = s['x_m']
    if abs(x) > p['x_limit_m']:
        F_lim = -p['x_limit_k_N_per_m'] * (abs(x) - p['x_limit_m']) * sign(x)
    else:
        F_lim = 0.0

    F_eff = (F_act_new + F_dist) - F_fric + F_lim

    # dynamics: solve 2x2
    theta = s['theta_rad']
    th_dot = s['theta_dot_rps']
    S = math.sin(theta)
    C = math.cos(theta)
    M = p['m_cart_kg']; m = p['m_pole_kg']; l = p['l_com_m']; I = p['I_pole_kgm2']; g = p['g_mps2']
    alpha = I + m*l*l

    a11 = M + m
    a12 = m*l*C
    a21 = m*l*C
    a22 = alpha

    b1 = F_eff + m*l*(th_dot**2)*S
    b2 = m*g*l*S

    det = a11*a22 - a12*a21
    x_ddot = ( b1*a22 - a12*b2) / det
    th_ddot = (-b1*a21 + a11*b2) / det

    # integrate
    x_new = x + x_dot*dt
    x_dot_new = x_dot + x_ddot*dt
    th_new = theta + th_dot*dt
    th_dot_new = th_dot + th_ddot*dt

    # measurements
    n_theta = rng.normal(0.0, p['theta_meas_sigma_rad'])
    n_thdot = rng.normal(0.0, p['theta_dot_meas_sigma_rps'])
    theta_meas = wrap_to_pi(th_new + n_theta)
    thdot_meas = th_dot_new + p['theta_dot_bias_rps'] + n_thdot

    s_next = {
        'x_m': x_new,
        'x_dot_mps': x_dot_new,
        'theta_rad': th_new,
        'theta_dot_rps': th_dot_new,
        'F_act_N': F_act_new,
    }
    y = {
        'x_m': x_new,
        'x_dot_mps': x_dot_new,
        'theta_rad': th_new,
        'theta_dot_rps': th_dot_new,
        'theta_meas_rad': theta_meas,
        'theta_dot_meas_rps': thdot_meas,
    }
    return s_next, y
```
