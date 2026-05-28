# PoleAngleEstimator 行为模型

## 目的

对来自 Plant 的 \(\theta\) 与 \(\dot\theta\) 传感器信号进行处理：
- 角度信号：一阶低通滤波（降低噪声）
- 角速度信号：估计并去除常值/慢变偏置（体现 2 个连续状态：\(\theta\) 滤波状态 + 偏置状态）

注意：角度测量已 wrap 到 \([-\pi,\pi]\)，若直接做差可能出现跳变，因此创新项使用 wrap-to-pi + 限幅。

## 方程

### 角度滤波

令 \(\theta_m\) 为测量角度，\(\hat\theta\) 为估计角度：

\[
\dot{\hat\theta} = \frac{\mathrm{wrapToPi}(\theta_m - \hat\theta)}{\tau_\theta}
\]

这是对误差的一阶滤波（等价于对角度做一阶低通，但在圆周变量上用 wrap 保持连续）。

### 偏置估计（非线性：wrap + clip）

定义角度创新：
\[
\nu = \mathrm{clip}(\mathrm{wrapToPi}(\theta_m - \hat\theta), -\nu_{max}, \nu_{max})
\]

偏置自适应：
\[
\dot{\hat b} = k_b \cdot \nu
\]

角速度估计：
\[
\hat{\dot\theta} = \dot\theta_m - \hat b
\]

其中 \(\hat b\) 的单位是 rad/s。

## 实现伪代码

```python
import math

def wrap_to_pi(a):
    while a <= -math.pi:
        a += 2*math.pi
    while a > math.pi:
        a -= 2*math.pi
    return a

def clip(x, lo, hi):
    return max(lo, min(hi, x))


def doStep(dt, inputs, p, s):
    if inputs['reset']:
        # reset to current measurement, bias=0
        s_next = {
            'theta_hat_rad': inputs['theta_meas_rad'],
            'bias_hat_rps': 0.0
        }
        y = {
            'theta_hat_rad': s_next['theta_hat_rad'],
            'theta_dot_hat_rps': inputs['theta_dot_meas_rps'],
            'bias_hat_rps': 0.0
        }
        return s_next, y

    e = wrap_to_pi(inputs['theta_meas_rad'] - s['theta_hat_rad'])
    d_theta_hat = e / p['theta_lpf_tau_s']
    theta_hat_new = s['theta_hat_rad'] + d_theta_hat * dt

    nu = clip(wrap_to_pi(inputs['theta_meas_rad'] - theta_hat_new),
              -p['innovation_clip_rad'], p['innovation_clip_rad'])
    d_bias = p['bias_adapt_rate'] * nu
    bias_new = s['bias_hat_rps'] + d_bias * dt

    theta_dot_hat = inputs['theta_dot_meas_rps'] - bias_new

    s_next = {
        'theta_hat_rad': theta_hat_new,
        'bias_hat_rps': bias_new
    }
    y = {
        'theta_hat_rad': theta_hat_new,
        'theta_dot_hat_rps': theta_dot_hat,
        'bias_hat_rps': bias_new
    }
    return s_next, y
```
