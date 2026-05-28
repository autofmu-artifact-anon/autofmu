# BatteryPackElectroThermal 行为模型（手工规格）

> 目标：提供一个用于数据集的“电-热耦合”电池包 FMU 规格（非现成 FMU）。
> 该模型包含多状态（SOC、核心温度、表面温度）、非线性（OCV(SOC)、R(SOC,T)、流量对换热的非线性缩放、饱和/裁剪）。

## 1. 状态、输入、输出

- 状态：
  - `soc`：电池荷电状态，范围 \([0,1]\)
  - `T_core_C`：核心温度 (°C)
  - `T_surface_C`：表面/壳体温度 (°C)

- 输入：
  - `current_A`：电池电流，正值放电，负值充电
  - `coolant_in_temp_C`：冷却液入口温度
  - `coolant_flow_kgps`：冷却液质量流量
  - `ambient_temp_C`：环境温度

- 输出：
  - `voltage_V`、`soc`、`T_core_C`、`T_surface_C`、`heat_W`

## 2. 电学子模型（OCV + 内阻）

### 2.1 OCV(SOC) 多项式（非线性）

设 \(z=soc\)。

\[
OCV(z) = \sum_{i=0}^{4} a_i z^i
\]

其中 \(a_i\) 为参数 `ocv_poly_coeff`。

### 2.2 内阻 R(SOC,T)（非线性、带裁剪）

核心温度 \(T = T_{core}\)。

\[
R(z,T) = R_0 \cdot \big(1 + k_{soc}(1-z)^2\big) \cdot \big(1 + k_T (T - T_{ref})\big)
\]

- \(k_{soc} =\) `R_soc_gain`
- \(k_T =\) `R_temp_coeff_perC`

为避免出现负电阻，对 \(R\) 做下限裁剪：

\[
R \leftarrow \max(R, R_{min})
\]

其中 \(R_{min}=0.005\,\Omega\)（实现常量，可写死在 FMU 内部）。

### 2.3 端电压

\[
V = OCV(z) - I \cdot R(z,T)
\]

其中 \(I\) 为实际电流（已饱和裁剪，见 4.1）。

## 3. 热子模型（两节点：核心/表面）

采用两热容 + 热阻网络：核心与表面之间热阻 `R_core_to_surface_KpW`；表面与环境的对流 `hA_ambient_WpK`；表面与冷却板的对流换热 `hA_coolant(flow)`。

### 3.1 发热量（焦耳热 + 简化熵热）

\[
Q_{joule} = I^2 \cdot R(z,T)
\]

熵热项用简单形式表示（保持非线性耦合）：

\[
Q_{entropic} = I \cdot dU/dT \cdot (T_{core,K})
\]

其中 `dUdT_VpK` 为参数（包级等效），\(T_{core,K}=T_{core,C}+273.15\)。

总发热：

\[
Q = Q_{joule} + Q_{entropic}
\]

输出 `heat_W = Q`。

### 3.2 冷却板换热系数随流量非线性变化

用饱和的幂律近似：

\[
hA_{coolant}(\dot m) = hA_{base} \cdot \left(\frac{\max(\dot m,0)}{\dot m_{nom}}\right)^{\gamma}
\]

- `hA_coolant_base_WpK` = \(hA_{base}\)
- `flow_nom_kgps` = \(\dot m_{nom}\)
- 取 \(\gamma = 0.6\)（实现常量）

并对 \(hA\) 上限做裁剪，避免极端流量导致刚性爆炸：

\[
hA_{coolant} \leftarrow \min(hA_{coolant}, 400)\;\text{W/K}
\]

### 3.3 热平衡方程

核心热容：\(C_c = m_{core} c_{p,core}\)

表面热容：\(C_s = m_{surface} c_{p,surface}\)

核心到表面传热：

\[
Q_{c\to s} = \frac{T_{core}-T_{surface}}{R_{c\to s}}
\]

表面对环境散热：

\[
Q_{s\to amb} = hA_{amb}(T_{surface} - T_{amb})
\]

表面对冷却液散热：

\[
Q_{s\to cool} = hA_{coolant}(T_{surface} - T_{cool,in})
\]

状态导数：

\[
\frac{dT_{core}}{dt} = \frac{Q - Q_{c\to s}}{C_c}
\]

\[
\frac{dT_{surface}}{dt} = \frac{Q_{c\to s} - Q_{s\to amb} - Q_{s\to cool}}{C_s}
\]

## 4. 约束与饱和（非线性）

### 4.1 电流饱和

\[
I \leftarrow \mathrm{clip}(I_{cmd}, -I_{max\_charge}, I_{max\_discharge})
\]

### 4.2 SOC 动力学 + 裁剪

\[
\frac{dz}{dt} = -\frac{I}{3600\,C_{Ah}}
\]

步进后：\(z\leftarrow \mathrm{clip}(z,0,1)\)。

## 5. doStep 伪代码

```python
def clip(x, lo, hi):
    return max(lo, min(hi, x))

def poly_ocv(z, a):
    # a: [a0..a4]
    return a[0] + a[1]*z + a[2]*z**2 + a[3]*z**3 + a[4]*z**4

def doStep(dt, inputs, p, s):
    # Unpack
    I_cmd = inputs['current_A']
    Tcool = inputs['coolant_in_temp_C']
    mdot = max(0.0, inputs['coolant_flow_kgps'])
    Tamb = inputs['ambient_temp_C']

    z = s['soc']
    Tcore = s['T_core_C']
    Tsurf = s['T_surface_C']

    # 1) Current saturation
    I = clip(I_cmd, -p['I_max_charge_A'], p['I_max_discharge_A'])

    # 2) Nonlinear electrical model
    OCV = poly_ocv(z, p['ocv_poly_coeff'])
    R = p['R0_ohm'] * (1.0 + p['R_soc_gain'] * (1.0 - z)**2) * (1.0 + p['R_temp_coeff_perC'] * (Tcore - p['T_ref_C']))
    R = max(R, 0.005)

    V = OCV - I * R

    # 3) Heat generation
    Q_joule = (I**2) * R
    Q_entropic = I * p['dUdT_VpK'] * (Tcore + 273.15)
    Q = Q_joule + Q_entropic

    # 4) Cooling conductance vs flow
    gamma = 0.6
    hA = p['hA_coolant_base_WpK'] * (mdot / p['flow_nom_kgps'])**gamma if mdot > 0 else 0.0
    hA = min(hA, 400.0)

    # 5) Thermal network
    Cc = p['m_core_kg'] * p['cp_core_JpkgK']
    Cs = p['m_surface_kg'] * p['cp_surface_JpkgK']

    Q_c_to_s = (Tcore - Tsurf) / p['R_core_to_surface_KpW']
    Q_s_to_amb = p['hA_ambient_WpK'] * (Tsurf - Tamb)
    Q_s_to_cool = hA * (Tsurf - Tcool)

    dTcore = (Q - Q_c_to_s) / Cc
    dTsurf = (Q_c_to_s - Q_s_to_amb - Q_s_to_cool) / Cs

    # 6) SOC dynamics
    dz = -I / (3600.0 * p['capacity_Ah'])

    # Integrate
    z_new = clip(z + dz*dt, 0.0, 1.0)
    Tcore_new = Tcore + dTcore*dt
    Tsurf_new = Tsurf + dTsurf*dt

    states_new = {'soc': z_new, 'T_core_C': Tcore_new, 'T_surface_C': Tsurf_new}
    outputs = {'voltage_V': V, 'soc': z_new, 'T_core_C': Tcore_new, 'T_surface_C': Tsurf_new, 'heat_W': Q}
    return states_new, outputs
```

## 6. 备注

- 该模型不追求严格电化学准确性，但保留了“电-热耦合 + 控制相关非线性”的关键结构。
- 可用于检验：连接错误（比如把 coolant_in_temp 接到 ambient_temp）会导致温度/电压明显偏离范围。
