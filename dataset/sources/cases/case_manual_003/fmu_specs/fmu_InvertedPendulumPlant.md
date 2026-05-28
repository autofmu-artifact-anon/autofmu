# InvertedPendulumPlant 行为模型

## 状态、输入、输出

- 状态（连续）：
  - \(x\)：小车位置 (m)
  - \(\dot x\)：小车速度 (m/s)
  - \(\theta\)：摆角 (rad)，\(\theta=0\) 为竖直向上
  - \(\dot\theta\)：角速度 (rad/s)

- 输入：
  - \(u\) = `force_cmd_N`：控制输入水平力 (N)
  - \(d\) = `disturbance_N`：外部扰动水平力 (N)

- 输出：\(x,\dot x,\theta,\dot\theta\) 直接作为输出（传感器理想化）。

## 非线性动力学方程（带摩擦/阻尼）

采用经典倒立摆-小车模型（点质量摆，质心距转轴 \(l\)）。令

- \(M\) = `m_cart_kg`
- \(m\) = `m_pend_kg`
- \(l\) = `length_m`
- \(g\) = `g_mps2`
- \(b\) = `cart_friction_Nspm`（小车粘性摩擦）
- \(c\) = `pend_damping_Nms`（关节粘性阻尼矩系数）
- 总水平外力 \(F = u + d - b\dot x\)

定义分母项：

\[
\Delta(\theta)= M + m\sin^2\theta
\]

则一种常用写法为：

\[
\ddot x = \frac{F + m\sin\theta\,(l\dot\theta^2 + g\cos\theta) - c\,\dot\theta\,\cos\theta / l}{\Delta(\theta)}
\]

\[
\ddot\theta = \frac{-F\cos\theta - m l \dot\theta^2\cos\theta\sin\theta - (M+m)g\sin\theta + c\,\dot\theta\,(M+m)/(m l^2)}{l\,\Delta(\theta)}
\]

说明：
- \(\sin\theta,\cos\theta\) 使系统强非线性。
- \(\dot\theta^2\) 项体现离心/科氏耦合。
- \(b\dot x\) 与 \(c\dot\theta\) 引入耗散（更接近真实装置）。

> 注：上式是“可用于数据集建模/验证”的规范描述；实现时只要保持同等物理意义和非线性耦合即可。

## doStep 伪代码（离散积分）

```python
import math

def doStep(dt, inputs, p, s):
    # unpack
    x = s['x_m']
    xdot = s['x_dot_mps']
    th = s['theta_rad']
    thdot = s['theta_dot_radps']

    u = inputs['force_cmd_N']
    d = inputs['disturbance_N']

    M = p['m_cart_kg']
    m = p['m_pend_kg']
    l = p['length_m']
    g = p['g_mps2']
    b = p['cart_friction_Nspm']
    c = p['pend_damping_Nms']

    # total horizontal force with viscous cart friction
    F = u + d - b * xdot

    s_th = math.sin(th)
    c_th = math.cos(th)

    Delta = M + m * (s_th**2)

    # nonlinear accelerations
    xdd = (F + m*s_th*(l*(thdot**2) + g*c_th) - (c*thdot*c_th)/max(1e-6, l)) / max(1e-6, Delta)

    thdd = (
        -F*c_th
        - m*l*(thdot**2)*c_th*s_th
        - (M + m)*g*s_th
        + c*thdot*(M + m)/max(1e-6, (m*l*l))
    ) / max(1e-6, (l*Delta))

    # semi-implicit Euler (more stable than explicit Euler for some settings)
    xdot_new = xdot + xdd * dt
    thdot_new = thdot + thdd * dt

    x_new = x + xdot_new * dt
    th_new = th + thdot_new * dt

    states_new = {
        'x_m': x_new,
        'x_dot_mps': xdot_new,
        'theta_rad': th_new,
        'theta_dot_radps': thdot_new
    }

    outputs = {
        'x_m': x_new,
        'x_dot_mps': xdot_new,
        'theta_rad': th_new,
        'theta_dot_radps': thdot_new
    }

    return states_new, outputs
```

实现注意：
- 需要避免 \(\Delta(\theta)\) 或 \(l\) 过小造成数值除零（用 `max(1e-6, ...)` 保护）。
- 若要模拟“倒下后撞击止挡”，可在实现中添加 \(\theta\) 角度限制/碰撞，但本规格不强制。
