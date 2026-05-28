# case_manual_004 设计日志

## 设计的 FMU

1. **HydraulicCylinderPlant**
   - 文件：`fmu_specs/fmu_HydraulicCylinderPlant.json` + `.md`
   - 物理原理：
     - 双作用液压缸与滑台的耦合动力学：位置/速度与两腔压力同时演化。
     - 压力由阀口流量、活塞运动导致的容积变化、以及腔间内部泄漏决定。
     - 机械侧包含库仑 + Stribeck + 粘性摩擦，并加入行程端部软限位（刚度+阻尼）。

2. **SpoolValveActuator**
   - 文件：`fmu_specs/fmu_SpoolValveActuator.json` + `.md`
   - 物理原理：
     - 阀芯执行器一阶动态（电磁/液压伺服放大器等效）。
     - 含阀口重叠导致的死区（deadzone）、速率限制与饱和。

3. **PositionController**
   - 文件：`fmu_specs/fmu_PositionController.json` + `.md`
   - 物理原理：
     - PI 位置控制 + 速度反馈阻尼（抑制振荡/超调）。
     - 命令饱和与 back-calculation 抗积分饱和；含小误差死区减少抖动。

## 为什么足够复杂

- **多状态**：
  - HydraulicCylinderPlant 含 4 个连续状态（x, v, pA, pB）。
  - SpoolValveActuator 含 1 个连续状态（spool_state）。
  - PositionController 含 1 个连续积分状态（i_state）。

- **非线性**：
  - 阀口流量为有符号平方根：q ~ sign(Δp)*sqrt(|Δp|) 并受 |u| 饱和影响。
  - 腔体体积 V(x) 随位置变化，使压力方程与机械方程强耦合。
  - 摩擦模型：tanh 平滑符号 + 指数 Stribeck 项（分段/强非线性）。
  - 多处 clip/死区/速率限制/软限位（分段非线性）。

- **有意义的参数**：
  - p_supply_Pa、beta_eff_Pa、A_A_m2、V0_A_m3、leak_C_L、F_static_N、v_stribeck_mps 等均具明确物理含义。

## 预期闭环行为

- 在位置参考阶跃下：阀命令先饱和推动阀芯打开，腔压建立驱动滑台运动；到达目标附近后阀芯回到小开度，靠积分消除静差。
- 在负载力阶跃扰动下：位置出现短暂偏差，控制器提高阀开度产生更大压差；由于抗积分饱和，扰动解除时不会产生长时间过冲。
