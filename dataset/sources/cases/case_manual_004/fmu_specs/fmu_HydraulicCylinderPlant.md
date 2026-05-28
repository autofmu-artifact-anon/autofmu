# HydraulicCylinderPlant 行为模型

双作用液压缸 + 滑台运动学/动力学模型。主要非线性来源：

- **阀口流量**：\(q \propto A(u)\,\mathrm{sgn}(\Delta p)\sqrt{|\Delta p|}\)
- **腔压动力学**：\(\dot p \propto (q - A\,v - q_{leak})/V(x)\)
- **摩擦**：库仑 + Stribeck（指数）+ 速度平滑 tanh
- **行程软限位**：靠近边界引入刚度/阻尼（分段非线性）

---

## 状态、输入与输出

- 状态：\(x, v, p_A, p_B\)
- 输入：
  - \(u\in[-1,1]\)：阀芯开度 `spool_u`（\(u>0\) 表示**伸出**：A 接供压，B 接回油）
  - \(F_L\)：外部负载 `load_force_N`（正值阻碍伸出）
- 输出：\(x, v, p_A, p_B\) 以及 `rod_force_N = A_A p_A - A_B p_B`

---

## 容积几何关系（非线性耦合）

\[
V_A(x) = V_{0A} + A_A\,x
\]
\[
V_B(x) = V_{0B} + A_B\,(stroke - x)
\]

> 体积随位置变化，使压力方程与机械方程强耦合。

---

## 阀口流量（orifice flow）

定义平滑的阀口“开度面积因子” \(\alpha(u)\)：
\[
\alpha = \mathrm{clip}(|u|, 0, 1)
\]

使用单个流量系数 \(C_q\)（已把 \(C_d A_{max}\) 合并）：

基本的有符号平方根：
\[
\phi(\Delta p) = \mathrm{sgn}(\Delta p)\sqrt{|\Delta p|}
\]

当 \(u>0\)（伸出）：
\[
q_{SA} = C_q\,\alpha\,\phi(p_S - p_A),\quad q_{BT} = C_q\,\alpha\,\phi(p_B - p_T)
\]

当 \(u<0\)（回缩）：
\[
q_{SB} = C_q\,\alpha\,\phi(p_S - p_B),\quad q_{AT} = C_q\,\alpha\,\phi(p_A - p_T)
\]

为统一写法，可以用条件分支实现。注意：此处忽略了阀口重叠/泄漏到外界，内部泄漏由 \(C_L\) 单独给出。

内部泄漏（A→B）：
\[
q_{leak} = C_L\,(p_A - p_B)
\]

---

## 压力动力学（可压缩性）

采用有效体积模量 \(\beta\)：


a) 伸出模式 \(u>0\)：
\[
\dot p_A = \frac{\beta}{V_A(x)}\big(q_{SA} - A_A v - q_{leak}\big)
\]
\[
\dot p_B = \frac{\beta}{V_B(x)}\big(-q_{BT} + A_B v + q_{leak}\big)
\]

b) 回缩模式 \(u<0\)：
\[
\dot p_A = \frac{\beta}{V_A(x)}\big(-q_{AT} - A_A v - q_{leak}\big)
\]
\[
\dot p_B = \frac{\beta}{V_B(x)}\big(q_{SB} + A_B v + q_{leak}\big)
\]

---

## 机械动力学 + 摩擦

液压力：
\[
F_h = A_A p_A - A_B p_B
\]

摩擦（平滑的 Stribeck + 库仑 + 粘性）：
\[
F_f(v) = \Big(F_c + (F_s - F_c)\,e^{-(|v|/v_{st})^2}\Big)\tanh\Big(\frac{v}{v_{\tanh}}\Big) + b\,v
\]

软限位：

- 当 \(x < x_{min}\)：\(F_{stop} = k(x_{min}-x) - c v\)
- 当 \(x > x_{max}\)：\(F_{stop} = -k(x-x_{max}) - c v\)
- 否则 \(F_{stop}=0\)

运动方程：
\[
\dot x = v
\]
\[
\dot v = \frac{1}{m}\Big(F_h - F_f(v) - F_L + F_{stop}(x,v)\Big)
\]

---

## 数值保护/约束

- 压力限制：\(p_A, p_B\) 夹紧到 \([p_T, p_S]\) 附近（留小裕度）防止数值发散。
- 体积下界：\(V_A, V_B\ge V_{min}\) 避免除零。
- 行程限制：可在积分后将 \(x\) 钳位到 \([x_{min}-\epsilon, x_{max}+\epsilon]\)，同时对越界的速度施加强阻尼（由软限位实现）。

---

## 伪代码（离散步进）

```python
import math

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

def phi_sqrt(dp):
    # signed sqrt
    return sign(dp) * math.sqrt(abs(dp) + 1e-12)

def friction(v, p):
    Fc = p['F_coulomb_N']
    Fs = p['F_static_N']
    vst = p['v_stribeck_mps']
    vt = p['v_tanh_mps']
    b = p['b_visc_Nspm']
    return (Fc + (Fs - Fc) * math.exp(- (abs(v)/vst)**2 )) * math.tanh(v / vt) + b * v


def doStep(dt, inputs, p, s):
    u = clip(inputs['spool_u'], -1.0, 1.0)
    alpha = clip(abs(u), 0.0, 1.0)

    # Geometry
    VA = max(1e-6, p['V0_A_m3'] + p['A_A_m2'] * s['x_m'])
    VB = max(1e-6, p['V0_B_m3'] + p['A_B_m2'] * (p['stroke_m'] - s['x_m']))

    pS, pT = p['p_supply_Pa'], p['p_tank_Pa']
    pA, pB = s['pA_Pa'], s['pB_Pa']

    q_leak = p['leak_C_L'] * (pA - pB)

    # Flows depending on direction
    qSA = qBT = qSB = qAT = 0.0
    if u >= 0:
        qSA = p['Cq'] * alpha * phi_sqrt(pS - pA)
        qBT = p['Cq'] * alpha * phi_sqrt(pB - pT)
        dpA = (p['beta_eff_Pa']/VA) * (qSA - p['A_A_m2']*s['v_mps'] - q_leak)
        dpB = (p['beta_eff_Pa']/VB) * (-qBT + p['A_B_m2']*s['v_mps'] + q_leak)
    else:
        qSB = p['Cq'] * alpha * phi_sqrt(pS - pB)
        qAT = p['Cq'] * alpha * phi_sqrt(pA - pT)
        dpA = (p['beta_eff_Pa']/VA) * (-qAT - p['A_A_m2']*s['v_mps'] - q_leak)
        dpB = (p['beta_eff_Pa']/VB) * (qSB + p['A_B_m2']*s['v_mps'] + q_leak)

    # Mechanical
    Fh = p['A_A_m2'] * pA - p['A_B_m2'] * pB
    Ff = friction(s['v_mps'], p)

    # Soft stops
    Fstop = 0.0
    if s['x_m'] < p['x_min_m']:
        Fstop = p['k_stop_Npm']*(p['x_min_m'] - s['x_m']) - p['c_stop_Nspm']*s['v_mps']
    elif s['x_m'] > p['x_max_m']:
        Fstop = -p['k_stop_Npm']*(s['x_m'] - p['x_max_m']) - p['c_stop_Nspm']*s['v_mps']

    dv = (Fh - Ff - inputs['load_force_N'] + Fstop) / p['m_kg']
    dx = s['v_mps']

    # Euler step (dataset spec, not a numerics tutorial)
    x_new = s['x_m'] + dx*dt
    v_new = s['v_mps'] + dv*dt
    pA_new = s['pA_Pa'] + dpA*dt
    pB_new = s['pB_Pa'] + dpB*dt

    # Clamp pressures within physical bounds (small margins)
    pA_new = clip(pA_new, pT*0.5, pS*1.05)
    pB_new = clip(pB_new, pT*0.5, pS*1.05)

    rod_force = p['A_A_m2']*pA_new - p['A_B_m2']*pB_new

    return (
        {'x_m': x_new, 'v_mps': v_new, 'pA_Pa': pA_new, 'pB_Pa': pB_new},
        {'x_m': x_new, 'v_mps': v_new, 'pA_Pa': pA_new, 'pB_Pa': pB_new, 'rod_force_N': rod_force}
    )
```
