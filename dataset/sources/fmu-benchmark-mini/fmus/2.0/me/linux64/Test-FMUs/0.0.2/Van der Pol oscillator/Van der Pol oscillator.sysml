package 'Van der Pol oscillator' {
  // features: x0, x1
  // scenarios: [{'kind': 'step', 'start_time': 0.0, 'stop_time': 20.0, 'step_size': 0.01, 'seed': 0}, {'kind': 'ramp', 'start_time': 0.0, 'stop_time': 20.0, 'step_size': 0.01, 'seed': 0}, {'kind': 'sine', 'start_time': 0.0, 'stop_time': 20.0, 'step_size': 0.01, 'seed': 0}]
  part def 'Van der Pol oscillator' {
    out port x0;
    out port x1;
    attribute mu;
  }
}
