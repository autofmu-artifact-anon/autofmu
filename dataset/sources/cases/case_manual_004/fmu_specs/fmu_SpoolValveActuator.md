# SpoolValveActuator 行为模型

阀芯执行器把控制器的归一化命令 `valve_cmd` 转换为阀口开度 `spool_u`。包含：**死区（deadzone）**、**一阶执行器动态**、**速率限制** 和 **饱和**。

## 死区（非线性）

\[
 u_{eff} = \begin{cases}
 0, & |u_{cmd}| \le d \\
 \frac{u_{cmd} - d\,\mathrm{sgn}(u_{cmd})}{1-d}, & |u_{cmd}| > d
 \end{cases}
\]
其中 \(d=\texttt{deadzone}\)。该映射确保在越过死区后仍能覆盖 [-1,1] 范围。

## 一阶动态 + 速率限制

内部状态 \(s\) 满足：
\[
 \dot{s} = \frac{u_{eff} - s}{\tau}
\]
并施加速率限制：\(\dot{s}\leftarrow \mathrm{clip}(\dot{s}, -r, r)\)，其中 \(r=\texttt{rate\_limit\_per\_s}\)。

输出：\(u = \mathrm{clip}(s, u_{min}, u_{max})\)。

## 伪代码

```python
def clip(x, lo, hi):
    return max(lo, min(hi, x))

def sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

def deadzone_map(u_cmd, d):
    if abs(u_cmd) <= d:
        return 0.0
    return (u_cmd - d*sign(u_cmd)) / (1.0 - d)

def doStep(dt, inputs, parameters, states):
    u_cmd = clip(inputs['valve_cmd'], parameters['u_min'], parameters['u_max'])
    u_eff = deadzone_map(u_cmd, parameters['deadzone'])

    ds = (u_eff - states['spool_state']) / parameters['tau_s']
    ds = clip(ds, -parameters['rate_limit_per_s'], parameters['rate_limit_per_s'])

    s_new = states['spool_state'] + ds * dt
    u = clip(s_new, parameters['u_min'], parameters['u_max'])
    return {'spool_state': s_new}, {'spool_u': u}
```
