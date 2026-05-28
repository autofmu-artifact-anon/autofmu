# PositionController 行为模型

一个用于液压轴的简单位置闭环：**PI + 速度反馈阻尼 + 饱和 + 抗积分饱和**。

## 变量

- 输入：
  - \(x_{ref}\) 位置参考 (m)
  - \(x\) 测量位置 (m)
  - \(v\) 测量速度 (m/s)
  - `enable` 使能
- 输出：
  - \(u\in[-1,1]\)：阀命令 `valve_cmd`
  - `sat_flag`：是否饱和
- 连续状态：
  - \(i\)：积分器内部状态 `i_state`

## 误差与死区（非线性）

\[
 e = x_{ref} - x
\]

为了减少稳态附近抖动，使用死区（deadband）：
\[
 e_{db} = \begin{cases}
 0, & |e| \le d \\
 e - d\,\mathrm{sgn}(e), & |e| > d
 \end{cases}
\]
其中 \(d = \texttt{deadband\_m}\)。

## 未饱和控制律

\[
 u_{raw} = K_p\, e_{db} + K_i\, i - K_v\, v
\]

## 饱和与抗积分饱和（back-calculation）

饱和：
\[
 u = \mathrm{clip}(u_{raw}, u_{min}, u_{max})
\]

抗积分饱和：当 \(u\neq u_{raw}\) 时，把饱和差反馈到积分器：
\[
 \dot{i} = e_{db} + a_{w}\,(u - u_{raw})
\]
其中 \(a_w=\texttt{aw\_gain}\)。同时对积分器状态做限幅：\(i\in[-i_{lim}, i_{lim}]\)。

禁用时（`enable=false`）：\(u=0\)，积分器以泄放方式回到 0：\(\dot{i}=-2i\)。

## 伪代码

```python
def clip(x, lo, hi):
    return max(lo, min(hi, x))

def sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

def deadband(e, d):
    if abs(e) <= d:
        return 0.0
    return e - d * sign(e)

def doStep(dt, inputs, parameters, states):
    if not inputs['enable']:
        u = 0.0
        di = -2.0 * states['i_state']
        i_new = clip(states['i_state'] + di*dt,
                     -parameters['integrator_limit'],
                     parameters['integrator_limit'])
        return {'i_state': i_new}, {'valve_cmd': u, 'sat_flag': False}

    e = inputs['x_ref_m'] - inputs['x_meas_m']
    e_db = deadband(e, parameters['deadband_m'])

    u_raw = parameters['Kp'] * e_db + parameters['Ki'] * states['i_state'] - parameters['Kv'] * inputs['v_meas_mps']
    u = clip(u_raw, parameters['u_min'], parameters['u_max'])
    sat_flag = (abs(u - u_raw) > 1e-12)

    di = e_db + parameters['aw_gain'] * (u - u_raw)
    i_new = clip(states['i_state'] + di*dt,
                 -parameters['integrator_limit'],
                 parameters['integrator_limit'])

    return {'i_state': i_new}, {'valve_cmd': u, 'sat_flag': sat_flag}
```
