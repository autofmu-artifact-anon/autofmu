# LOG - case_manual_002

## 本 case 设计的 FMU

1. **fmu_CartPolePlant**
   - **物理原理**：小车-倒立摆（cart-pole）的非线性耦合动力学（sin/cos 项），并加入执行器一阶滞后、输出饱和、非线性摩擦（tanh 平滑库仑摩擦 + 粘性摩擦）与轨道软限位（超限弹簧力）。
   - **状态**：x, x_dot, theta, theta_dot, F_act（>= 4 个连续状态，满足“多状态”）。
   - **非线性**：sin(theta)、cos(theta)、tanh(x_dot/v0)、clamp 饱和、软限位分段非线性。

2. **fmu_PoleAngleEstimator**
   - **物理原理**：对角度测量做圆周变量的一阶滤波（wrap-to-pi），同时用创新项驱动角速度偏置估计（bias_hat）。
   - **状态**：theta_hat, bias_hat（2 个连续状态）。
   - **非线性**：wrap-to-pi 与 clip（防止角度跳变造成估计发散）。

3. **fmu_SwingUpBalanceController**
   - **物理原理**：混合控制（摆起/平衡）。摆起使用能量整形（与 cos(theta) 和 sign(thd*cos(th)) 相关的非线性注能方向）；平衡使用线性化增益（类似 LQR/PD）+ 位置误差积分。输出力带饱和，并做简单 anti-windup。
   - **状态**：x_err_int（积分器状态）+ mode（离散模式，规格中作为 state 记录）。
   - **非线性**：模式切换（带滞回）、能量函数与 sign、输出饱和 clamp。

## 为什么复杂度足够

- **多状态**：Plant 5 状态（含执行器），Estimator 2 状态，Controller 至少 1 个连续状态（积分器）+ 1 个离散模式。
- **非线性**：动力学本身非线性（sin/cos），且叠加摩擦/饱和/软限位/模式切换/角度 wrap。
- **有意义参数**：质量、长度、惯量、摩擦、执行器时间常数、饱和力、估计器时间常数/自适应率、控制增益等均可解释。
- **接口与行为完整**：每个 FMU 都提供了接口 JSON 与方程/伪代码的行为说明（MD）。
