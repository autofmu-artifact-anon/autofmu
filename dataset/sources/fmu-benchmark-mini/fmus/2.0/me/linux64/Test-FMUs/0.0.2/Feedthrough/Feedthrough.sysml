package Feedthrough {
  // features: bool_out, int_out, real_continuous_out, real_discrete_out
  // scenarios: [{'kind': 'step', 'start_time': 0.0, 'stop_time': 2.0, 'step_size': 0.01, 'seed': 0}, {'kind': 'ramp', 'start_time': 0.0, 'stop_time': 2.0, 'step_size': 0.01, 'seed': 0}, {'kind': 'sine', 'start_time': 0.0, 'stop_time': 2.0, 'step_size': 0.01, 'seed': 0}]
  part def Feedthrough {
    in port real_continuous_in;
    in port real_discrete_in;
    in port int_in;
    out port real_continuous_out;
    out port real_discrete_out;
    out port int_out;
    out port bool_out;
    attribute real_fixed_param;
    attribute real_tunable_param;
    attribute string_param;
  }
}
