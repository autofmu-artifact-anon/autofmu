# SwingUpBalanceController 行为模型

## 目的

实现一个可解释的倒立摆控制策略：
- **摆起模式 (mode=0)**：基于能量整形（energy shaping）将摆从下垂摆到倒立附近
- **平衡模式 (mode=1)**：在倒立附近使用线性化增益（类似 LQR/PD）稳定，同时用位置误差积分改善稳态跟踪
- **非线性与多状态特性**：模式切换（带滞回）+ 输出饱和 + 积分抗饱和

> 注意：该控制器是“规格设计”，用于 dataset case 的 ground-truth 连接与复杂度覆盖，而不追求对所有参数都最优。

## 角度处理

控制器内部使用
\[
\tilde\theta = \mathrm{wrapToPi}(\theta_{hat} - \pi)
\]
使得倒立目标对应 \(\tilde\theta = 0\)。

## 模式切换（混合逻辑）

- 从摆起进入平衡：若 \(|\tilde\theta| < \theta_{bal}\) 且 \(|\dot\theta|\) 不太大（实现中可省略速度门限或仅弱门限）。
- 从平衡退回摆起：若 \(|\tilde\theta| > \theta_{fb}\)（\(\theta_{fb} > \theta_{bal}\) 形成滞回）。

模式用整数输出，但在规格中作为 state 记录（实现上是离散状态）。

## 摆起模式：能量整形（非线性）

杆的等效机械能（以“下垂点”为零势能基准的一种简单形式）：
\[
E = \frac{1}{2} \dot\theta^2 + (1 - \cos\theta_{hat})
\]
倒立目标能量（相对同一基准）约为：
\[
E^* = 2
\]

能量误差：\(e_E = E - E^*\)。

摆起控制律（示意）：
\[
F_{su} = -k_E \cdot e_E \cdot \mathrm{sign}(\dot\theta \cos\theta) - d_{su} \dot x
\]
其中 \(\mathrm{sign}(\dot\theta \cos\theta)\) 给出能量注入方向（常见摆起启发式）。

## 平衡模式：线性反馈 + 积分

线性反馈（以 \(\tilde\theta=\theta-\pi\) 为角度误差）：
\[
F_{bal} = -k_x (x-x_{ref}) - k_{\dot x} \dot x - k_{\theta} \tilde\theta - k_{\dot\theta} \dot\theta + k_i \int (x_{ref}-x) dt
\]

积分器：
\[
\dot I_x = \mathrm{clip}(x_{ref}-x, -e_{max}, e_{max})
\]
并且 \(I_x\) 自身也限幅到 \([-I_{lim}, I_{lim}]\) 防止 windup。

## 输出饱和与抗 windup

最终输出：
\[
F_{cmd} = \mathrm{clamp}(F, -F_{max}, F_{max})
\]

当输出饱和且积分项会进一步推动饱和时，冻结或反向泄放积分（此处用简单冻结即可）。

## 实现伪代码

```python
import math

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

def wrap_to_pi(a):
    while a <= -math.pi:
        a += 2*math.pi
    while a > math.pi:
        a -= 2*math.pi
    return a


def doStep(dt, inputs, p, s):
    if not inputs['enable']:
        # freeze integrator, output zero
        return s, {'force_cmd_N': 0.0, 'mode': int(s['mode'])}

    x = inputs['x_m']
    xd = inputs['x_dot_mps']
    th = inputs['theta_hat_rad']
    thd = inputs['theta_dot_hat_rps']
    xref = inputs['x_ref_m']

    th_tilde = wrap_to_pi(th - math.pi)

    mode = int(s['mode'])
    if mode == 0:
        if abs(th_tilde) < p['theta_balance_thresh_rad']:
            mode = 1
    else:
        if abs(th_tilde) > p['theta_fallback_thresh_rad']:
            mode = 0

    # integrator update (only in balance mode)
    I = s['x_err_int']
    if mode == 1:
        e = (xref - x)
        # clip instantaneous error before integrating
        e_clip = clamp(e, -0.5, 0.5)
        I_candidate = clamp(I + e_clip*dt, -p['x_int_limit'], p['x_int_limit'])
    else:
        I_candidate = I

    if mode == 0:
        # energy shaping swing-up
        E = 0.5*(thd**2) + (1.0 - math.cos(th))
        E_star = 2.0
        eE = E - E_star
        inject_dir = sign(thd * math.cos(th))
        F = -p['swingup_energy_gain'] * eE * inject_dir - p['swingup_damping'] * xd
    else:
        # balance
        F = (
            -p['balance_kx']  * (x - xref)
            -p['balance_kxd'] * xd
            -p['balance_kth'] * th_tilde
            -p['balance_kthd']* thd
            +p['x_int_ki']    * I_candidate
        )

    # saturation + simple anti-windup: freeze I when saturated and would worsen saturation
    F_sat = clamp(F, -p['F_max_N'], p['F_max_N'])
    if mode == 1 and (F != F_sat):
        # if saturated, keep previous I (no further integration)
        I_next = I
    else:
        I_next = I_candidate

    s_next = {'x_err_int': I_next, 'mode': float(mode)}
    y = {'force_cmd_N': F_sat, 'mode': mode}
    return s_next, y
```
