# case_manual_005 设计日志

本 case：**电池包热管理闭环**（Battery Pack Thermal Management Closed-Loop）

## 设计了哪些 FMU

1. `fmu_BatteryPackPlant`
2. `fmu_CoolantLoopPlant`
3. `fmu_ThermalController`

## 每个 FMU 的物理原理

### 1) BatteryPackPlant（电-热耦合）

- **SOC 动力学**：库仑计量 $\dot{SOC} = -I/(3600\,C_{Ah})$。
- **电压模型**：$V = OCV(SOC) - I\,R(T,SOC) - k_{pol}|I|$。
- **热模型**：发热 $\dot Q = I^2R + |I|k_{pol}n_{series}$，并通过换热项 $h_{cool}(T-T_{cool})$ 与冷却液交换热量。

### 2) CoolantLoopPlant（泵-散热器热动力学）

- 以冷却液代表温度 $T_c$ 为主状态，能量平衡 $C\dot T_c = Q_{in} - UA(u_p)(T_c-T_{amb})$。
- 泵内部状态 $u_p$ 为一阶惯性并带变化率限制，反映执行器动态。
- $UA(u_p)$ 为**非线性饱和函数**，反映泵速提高带来换热能力提升但最终受散热器/流量限制饱和。

### 3) ThermalController（PI + 迟滞 + 抗饱和）

- 对电芯温度误差做 PI 控制。
- 引入迟滞带，当误差接近 0 时冻结/弱化积分，避免泵命令抖动。
- 使用输出限幅与抗积分饱和（回算项），并对泵命令加入限速。

## 为什么这个设计有足够的复杂度

- **多状态**：
  - BatteryPackPlant 至少 2 个连续状态（SOC、T_cell）。
  - CoolantLoopPlant 至少 2 个连续状态（T_coolant、pump_state）。
- **非线性**：
  - OCV(SOC) 多项式；R(T,SOC) 指数项；发热含 $I^2$ 与 $|I|$。
  - 冷却回路 UA 随泵速非线性饱和。
  - 控制器含迟滞、限幅、抗积分饱和与限速。
- **有意义参数**：容量(Ah)、串联数、热容(J/K)、换热系数(W/K)、泵时间常数(s) 等均有明确物理含义。

## 文件清单

- `system.sysml`
- `requirement.json`
- `ground_truth.json`
- `fmu_specs/`：
  - `fmu_BatteryPackPlant.json/.md`
  - `fmu_CoolantLoopPlant.json/.md`
  - `fmu_ThermalController.json/.md`
