# ThermalController 行为模型（手工规格）

> 目标：提供一个带状态（积分环节）、带模式切换（滞回）、带非线性饱和的热管理控制器规格。
> 它根据电池核心温度、SOC、电压和驾驶员功率请求，输出电流命令与冷却执行器命令。

## 1. 模式机（离散状态，含滞回）

模式 `mode`：
- 0 = NORMAL
- 1 = DERATE
- 2 = SHUTDOWN

切换逻辑（滞回）：

- 若 `mode` != SHUTDOWN 且 \(T_{core} \ge T_{shutdown\_on}\) → 进入 SHUTDOWN
- 若 `mode` == SHUTDOWN 且 \(T_{core} \le T_{shutdown\_off}\) → 退出到 DERATE（保守）
- 若 `mode` == NORMAL 且 \(T_{core} \ge T_{derate\_on}\) → 进入 DERATE
- 若 `mode` == DERATE 且 \(T_{core} \le T_{derate\_off}\) → 退出到 NORMAL

此外保护条件：
- 若 \(soc \le soc_{min}\) 或 \(V \le V_{min}\)，则强制 DERATE（或直接将电流限制到最小）。

## 2. 电流命令：基于功率请求 + 保护降额（非线性）

驾驶员功率请求 \(P_{req} \ge 0\)。

基准电流（近似 \(I=P/V\)，带一个比例系数）：

\[
I_{base} = k_P \cdot \frac{P_{req}}{\max(V, V_{min})}
\]

降额系数 \(\alpha\)：

- NORMAL：\(\alpha=1\)
- DERATE：随温度超限线性降低，并裁剪到 \([0,1]\)

\[
\alpha_T = \mathrm{clip}\left(1 - \frac{T_{core}-T_{derate\_on}}{T_{shutdown\_on}-T_{derate\_on}},\;0,\;1\right)
\]

并叠加 SOC 低时的降额（平滑非线性）：

\[
\alpha_{soc} = \mathrm{clip}\left(\frac{soc - soc_{min}}{0.1},\;0,\;1\right)
\]

DERATE 下：\(\alpha = \min(\alpha_T, \alpha_{soc})\)。

SHUTDOWN：\(\alpha=0\)。

最终电流命令：

\[
I_{cmd} = \mathrm{clip}(\alpha \cdot I_{base},\;I_{min},\;I_{max})
\]

> 非线性点：除法、裁剪、min 组合、分段模式机。

## 3. 冷却命令：温度误差 PI + 环境前馈（积分状态）

温度误差：\(e = T_{core} - T_{set}\)。

积分状态：

\[
\frac{dI_e}{dt} = e
\]

并对积分项做 clamp：\(I_e \leftarrow clip(I_e, -int\_clamp, int\_clamp)\)。

冷却基础命令：

\[
u_{cool} = clip(k_{P,cool} e + k_{I,cool} I_e + k_{ff}(T_{amb}-25), 0, 1)
\]

映射到泵/风扇命令：

- 泵：\(pump\_cmd = u_{cool}\)
- 风扇：风扇在高温时更激进（引入非线性增益）：

\[
fan\_cmd = clip(u_{cool}^{1.4}, 0, 1)
\]

在 SHUTDOWN 模式下，仍允许冷却保持最大以帮助降温：

- `pump_cmd = 1`
- `fan_cmd = 1`

## 4. doStep 伪代码

```python
import math

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def doStep(dt, inputs, p, s):
    T = inputs['T_core_C']
    soc = inputs['soc']
    V = inputs['voltage_V']
    P_req = max(0.0, inputs['driver_power_request_W'])
    Tamb = inputs['ambient_temp_C']

    I_e = s['integral_err']
    mode = int(s['mode_state'])  # 0/1/2

    # 1) Mode switching with hysteresis
    if mode != 2 and T >= p['T_shutdown_on_C']:
        mode = 2
    elif mode == 2 and T <= p['T_shutdown_off_C']:
        mode = 1
    elif mode == 0 and T >= p['T_derate_on_C']:
        mode = 1
    elif mode == 1 and T <= p['T_derate_off_C']:
        mode = 0

    if soc <= p['soc_min'] or V <= p['V_min_V']:
        mode = max(mode, 1)  # at least DERATE

    # 2) Cooling PI + feedforward
    e = T - p['T_set_C']
    dI_e = e
    I_e_new = clip(I_e + dI_e*dt, -p['int_clamp'], p['int_clamp'])

    u_cool = p['kP_cool']*e + p['kI_cool']*I_e_new + p['ambient_ff_gain']*(Tamb - 25.0)
    u_cool = clip(u_cool, 0.0, 1.0)

    if mode == 2:
        pump_cmd = 1.0
        fan_cmd = 1.0
    else:
        pump_cmd = u_cool
        fan_cmd = clip(u_cool**1.4, 0.0, 1.0)

    # 3) Current command with derating
    I_base = p['kP_current'] * (P_req / max(V, p['V_min_V']))

    if mode == 0:
        alpha = 1.0
    elif mode == 1:
        alpha_T = clip(1.0 - (T - p['T_derate_on_C']) / (p['T_shutdown_on_C'] - p['T_derate_on_C']), 0.0, 1.0)
        alpha_soc = clip((soc - p['soc_min']) / 0.1, 0.0, 1.0)
        alpha = min(alpha_T, alpha_soc)
    else:
        alpha = 0.0

    I_cmd = clip(alpha * I_base, p['I_min_A'], p['I_max_A'])

    states_new = {'integral_err': I_e_new, 'mode_state': mode}
    outputs = {'current_A': I_cmd, 'pump_cmd': pump_cmd, 'fan_cmd': fan_cmd, 'mode': mode}
    return states_new, outputs
```

## 5. 备注

- 该控制器含连续状态（积分）+ 离散状态（模式机），对连接与单位错误非常敏感。
- 设计上能产生“有意义的闭环行为”：温度高时加大冷却并降额电流；温度回落后退出降额（滞回避免抖振）。
