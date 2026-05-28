# BatteryPackPlant 行为模型

该 FMU 描述一个简化但“够真实”的电池包：
- 连续状态：SOC、代表性电芯温度 `T_cell`。
- 非线性：OCV(SOC) 多项式；内阻 `R(T,SOC)` 指数/分段；热生成含 `I^2 R` 与 `|I|` 项。

## 变量与符号

- 输入：
  - $I$：放电电流（A），放电为正
  - $T_{cool}$：冷却液入口温度（°C）
- 状态：
  - $z$：SOC（0..1）
  - $T$：电芯温度（°C）
- 输出：
  - $V_{term}$：端电压（V）
  - $\dot Q$：发热功率（W）

## 电学模型（非线性）

### OCV(SOC)

采用 3 次多项式（便于数据集任务，又能表达非线性）：

\[
\mathrm{OCV}(z) = a_0 + a_1 z + a_2 z^2 + a_3 z^3
\]

并对 $z$ 做软钳位：
\[
\tilde z = \mathrm{clip}(z, z_{min}, z_{max})
\]

### 内阻 R(T,SOC)

内阻随低 SOC 增大、随温度升高下降（近似 Arrhenius/指数）：

\[
R(\tilde z, T) = r_0 \cdot \left(1 + r_{soc\_gain} \cdot (1-\tilde z)^2\right) \cdot \exp\left(-\beta (T-25)\right)
\]

### 端电压

单体电压近似：
\[
V_{cell} = \mathrm{OCV}(\tilde z) - I\,R(\tilde z,T) - k_{pol}\,|I|
\]

电池包（$n_{series}$ 串联）端电压：
\[
V_{term} = n_{series}\,\max(0, V_{cell})
\]

> 注：`max(0,·)` 是数值保护，防止在大电流/低 SOC 下出现不合理负电压。

## SOC 动力学

\[
\dot z = -\frac{I}{3600\,C_{Ah}}
\]

- 其中 $C_{Ah}$ 为容量（Ah）。
- 可选：充电($I<0$)时乘以库仑效率，但本 case 主要使用放电工况。

## 热模型（能量守恒 + 冷却换热）

### 发热功率

\[
\dot Q = I^2 R(\tilde z,T) + |I|\,k_{pol}\,n_{series}
\]

解释：
- $I^2R$：欧姆热
- $|I|k_{pol}$：极化/反应损耗（用等效电压损耗近似）

### 温度动力学

\[
\dot T = \frac{\dot Q - h_{cool}(T - T_{cool})}{C_{th}}
\]

其中：
- $C_{th}$：等效热容（J/K）
- $h_{cool}$：电池到冷却液的等效换热系数（W/K）

对温度也做数值保护：
\[
T \leftarrow \mathrm{clip}(T, T_{min}, T_{max})
\]

## 伪代码（doStep）

```python
def clip(x, lo, hi):
    return max(lo, min(hi, x))

def doStep(dt, inputs, p, x):
    I = inputs['i_load_A']
    Tcool = inputs['coolant_in_temp_C']

    z = x['soc']
    T = x['temp_cell_C']

    zt = clip(z, p['soc_min'], p['soc_max'])

    ocv = (p['ocv_a0_V'] + p['ocv_a1_V']*zt + p['ocv_a2_V']*zt**2 + p['ocv_a3_V']*zt**3)

    R = p['r0_Ohm'] * (1.0 + p['r_soc_gain']*(1.0-zt)**2) * math.exp(-p['r_temp_beta']*(T-25.0))

    v_cell = ocv - I*R - p['k_pol_V']*abs(I)
    v_term = p['n_series'] * max(0.0, v_cell)

    # SOC dynamics
    dz = -I / (3600.0 * p['capacity_Ah'])
    z_new = clip(z + dz*dt, 0.0, 1.0)

    # Heat generation
    q_gen = (I**2)*R + abs(I)*p['k_pol_V']*p['n_series']

    # Thermal dynamics
    dT = (q_gen - p['h_cool_WK']*(T - Tcool)) / p['thermal_mass_JK']
    T_new = clip(T + dT*dt, p['temp_min_C'], p['temp_max_C'])

    states = {'soc': z_new, 'temp_cell_C': T_new}
    outputs = {'v_term_V': v_term, 'soc': z_new, 'temp_cell_C': T_new, 'heat_gen_W': q_gen}
    return states, outputs
```
