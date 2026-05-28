# case_manual_003 日志

## 本 case 设计了哪些 FMU

1. **fmu_InvertedPendulumPlant**
   - 倒立摆-小车的非线性动力学模型（4 个连续状态）。
   - 输入：控制水平力 `force_cmd_N` 与外部扰动 `disturbance_N`。
   - 输出：位置/速度/角度/角速度。

2. **fmu_PendulumController**
   - 闭环控制器（角度 + 位置反馈），包含积分与执行器一阶滞后。
   - 非线性环节：力输出饱和（±u_max_N）+ 死区（deadzone_N）+ 抗积分饱和 back-calculation。

## 每个 FMU 的物理原理

- **InvertedPendulumPlant**：
  - 基于经典倒立摆方程：\(\sin\theta\)、\(\cos\theta\) 引入强非线性耦合；\(\dot\theta^2\) 体现摆杆运动产生的离心项。
  - 小车粘性摩擦（与速度成正比的阻力）与摆杆关节粘性阻尼（与角速度成正比的阻尼矩）用于模拟能量耗散，避免“理想模型”过于脆弱。

- **PendulumController**：
  - 将角度误差与位置误差映射为水平力指令（类似线性化附近的状态反馈/PD + I 结构）。
  - 执行器用一阶滞后建模（更贴近电机/驱动器动态）。
  - 饱和与死区用于体现真实执行器限制；抗积分饱和避免在饱和时积分项发散。

## 为什么这个设计有足够的复杂度

- **多状态**：
  - Plant 4 状态（x, x_dot, theta, theta_dot），Controller 3 状态（两个积分 + 执行器状态）。

- **非线性**：
  - Plant：\(\sin\theta\)、\(\cos\theta\)、\(\dot\theta^2\) 的乘积耦合。
  - Controller：饱和、死区、抗积分饱和（非线性/分段）。

- **有意义参数**：
  - 质量、长度、重力、摩擦/阻尼、控制增益、执行器时间常数、饱和上限等均具有明确物理含义。

- **可验证性强**：
  - requirement.json 定义了位置阶跃 + 短脉冲扰动的场景，可有效暴露符号反接、漏连反馈、单位错误等常见集成问题。
