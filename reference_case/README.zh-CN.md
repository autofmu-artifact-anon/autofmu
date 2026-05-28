# 船舶推进系统参考案例

COMPASS 论文 Section 5.5 的 case study 参考数据，对应一个 14 块 SysML 架构的船舶推进系统。

## 系统概述

全推进链包含：控制器、命令-发动机接口（CE Wrapper）、柴油机模型、齿轮箱、轴系模型、螺旋桨、燃油消耗模型、船体阻力估计器、空化代理、排气热监测器，以及效率估计和轴承监测等辅助块。

## 候选 FMU 库

共 18 个 FMU 候选，其中 10 个被选中、8 个被拒绝。所有 FMU 均从 Modelica 模型经 FMI 2.0 CoSimulation 接口导出。

### 选中的 10 个 FMU

| FMU | 步长 | 角色 |
|-----|------|------|
| controller | 0.005 s | 推进控制器 |
| ce_wrapper | 0.005 s | 命令-发动机线性映射 |
| engine_model | 0.5 s | 柴油机模型 |
| gearbox | 0.05 s | 齿轮箱 |
| shaft_line_model | 0.05 s | 轴系动力学 |
| propeller_design | 0.1 s | 螺旋桨推力模型 |
| fuel_consumption_model | 1.0 s | 燃油消耗估计 |
| hull_load_estimator | 1.0 s | 船体阻力估计 |
| cavitation_proxy | 0.5 s | 空化裕度估计 |
| exhaust_thermal_monitor | 2.0 s | 排气热安全监测 |

### 被拒绝的 8 个候选

| 候选 | 轮次 | 拒绝原因 |
|------|------|----------|
| shaft_dynamics_v2 | 1 (mask) | shaft_RPM 定义为输入（振动监测器） |
| engine_model_legacy | 2 (mask) | 缺少 engine_state_vector 端口 |
| shaft_speed_sensor | 3 (hard) | 无输入端口 |
| thrust_allocator | 3 (hard) | 扭矩-推力因果关系反转 |
| fuel_meter_digital | 3 (hard) | fuel_flow_rate 为 Integer 类型 |
| thermal_protection_relay | 3 (hard) | 输出为 Boolean，需连续信号 |
| propeller_pitch_ctrl | 3 (hard) | 桨距控制，非推力计算 |
| auxiliary_cooling_pump | 3 (hard) | 无关子系统 |

## 编排图

10 个 FMU 节点 + 2 个环境节点 + 2 个 wrapper 节点，共 22 条有向边。

### 强连通分量

- **SCC1**: controller, ce_wrapper, engine_model（K_T/RPM 反馈，每 0.5 s 迭代一次）
- **SCC2**: gearbox, shaft_line_model, propeller_design（shaft_RPM/resistance_torque 反馈，每 0.05 s 迭代一次）

### Wrapper

1. CE Wrapper: 归一化信号 [0,1] → RPM [40,120] 的线性映射
2. Projection Wrapper: 4 维发动机状态向量 → 提取 2 个分量（engine_power, engine_RPM）
3. Unit Wrapper: 燃油流量 kg/h → g/s（系数 1000/3600）

## 仿真场景

300 秒，分 5 个阶段：

| 阶段 | 时间段 | 航速 | 海况 |
|------|--------|------|------|
| Phase 1: Cold start | 0–40 s | 0→12 kn | SS 2 |
| Phase 2: Steady cruise | 40–100 s | 12 kn | SS 2 |
| Phase 3: Sea-state disturbance | 100–160 s | 12 kn | SS 6 |
| Phase 4: Speed step | 160–240 s | 14 kn | SS 4 |
| Phase 5: Deceleration | 240–300 s | 14→8 kn | SS 3 |

## 监测信号

K_T, RPM, Thrust, cavitation_margin, resistance_margin, shaft_torsional_stress, thermal_margin, SFOC

## 运行仿真

```bash
python3 run_case_simulation.py
```

输出文件：
- `output/simulated_timeseries.csv` — 3000 行时序数据
- `output/command_events.csv` — 5 个阶段事件

## 文件结构

```
reference_case/
├── system.sysml              # 14 块 SysML 系统模型
├── requirement.json          # 需求定义（8 信号 + 14 验收准则）
├── fmu_list.json             # 18 个候选 FMU 列表
├── orchestration.json        # 编排配置（连接、调度、SCC、wrapper）
├── ground_truth.json         # 真值数据（正确 FMU、验收结果）
├── run_case_simulation.py    # 合成仿真脚本
├── fmu_specs/                # 各 FMU 规格文件（.json + .md）
├── output/
│   ├── simulated_timeseries.csv
│   └── command_events.csv
├── README.zh-CN.md
└── LOG.md
```
