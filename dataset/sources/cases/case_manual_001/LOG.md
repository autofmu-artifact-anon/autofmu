# case_manual_001 设计日志

## 设计的 FMU

1. **BatteryPackElectroThermal**
   - 文件：`fmu_specs/fmu_BatteryPackElectroThermal.json` + `.md`
   - 物理原理：
     - 电学：OCV(SOC) 多项式 + R_int(SOC,T) 温度/SOC 相关内阻
     - 热学：两节点热网络（核心/表面），核心发热经热阻传到表面，表面对环境与冷却液对流散热
     - 发热：焦耳热 I^2R + 简化熵热项（I * dU/dT * T）

2. **CoolingLoop**
   - 文件：`fmu_specs/fmu_CoolingLoop.json` + `.md`
   - 物理原理：
     - 泵：命令到流量平方映射 + 一阶执行器动态
     - 散热器：UA = UA_base + UA_gain * fan_cmd^0.7，并带上限
     - 回路热平衡：集总冷却液热容，吸热(heat_load)与散热(UA*(Tcool-Tamb))
     - 散热器出口温度：用指数有效度近似，体现流量与UA共同作用

3. **ThermalController**
   - 文件：`fmu_specs/fmu_ThermalController.json` + `.md`
   - 物理原理：
     - 监督模式机：NORMAL/DERATE/SHUTDOWN，温度阈值带滞回
     - 电流命令：I ≈ (P_req/V) 的非线性映射，并随温度、SOC、电压做降额与饱和
     - 冷却命令：PI(温度误差) + 环境前馈；风扇用 u^1.4 增强高温段响应

## 为什么足够复杂

- **多状态**：
  - BatteryPackElectroThermal 至少 3 个连续状态（SOC、T_core、T_surface）
  - CoolingLoop 2 个连续状态（coolant_temp、flow_state）
  - ThermalController 含连续积分状态 + 离散模式状态

- **非线性**：
  - OCV(SOC) 多项式、R(SOC,T) 乘积结构
  - I^2R 发热项、指数有效度换热器模型
  - flow ~ cmd^2，UA ~ fan_cmd^0.7，风扇命令 u^1.4
  - 多处 clip/saturation + min 组合 + 滞回模式机（分段非线性）

- **有意义的参数**：
  - capacity_Ah、R0_ohm、m_core_kg、cp_core、UA_base、flow_max、温度阈值等均具物理含义

## 预期闭环行为

- 在 35°C 环境与功率阶跃下：电池升温 → 控制器增加泵/风扇 → 若温度继续逼近阈值则进入 DERATE 降低电流，从而将 T_core 限制在上限内。
- SOC 在持续放电时单调下降；电压处于合理范围（连接错误会导致明显违背该范围）。
