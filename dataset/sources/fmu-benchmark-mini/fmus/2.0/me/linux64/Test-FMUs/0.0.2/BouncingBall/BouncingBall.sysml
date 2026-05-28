package BouncingBall {
  // features: h, v
  // scenarios: [{'kind': 'step', 'start_time': 0.0, 'stop_time': 3.0, 'step_size': 0.001, 'seed': 0}, {'kind': 'ramp', 'start_time': 0.0, 'stop_time': 3.0, 'step_size': 0.001, 'seed': 0}, {'kind': 'sine', 'start_time': 0.0, 'stop_time': 3.0, 'step_size': 0.001, 'seed': 0}]
  part def BouncingBall {
    out port h;
    out port v;
    attribute g;
    attribute e;
  }
}
