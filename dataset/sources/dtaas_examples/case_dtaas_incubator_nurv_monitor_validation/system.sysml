package PkgIncubatorNurvMonitorValidation {
  part def Unifmu {
    in kalman_input : Real;
    in sensor_data : Real;
    in error_threshold : Real;
    out verdict : Boolean;
  }
  part def EuFbkNurvSafeOperation {
    in anomaly : Boolean;
    in energy_saving : Boolean;
    out output : Integer;
    in soft_reset : Boolean;
  }
  part def Source {
    out error_threshold : Real;
    out sensor_data : Real;
    out kalman_input : Real;
  }
  part def Watcher {
    in desired_temperature : Real;
    out energy_saving : Boolean;
  }
  part def SystemIncubatorNurvMonitorValidation {
    part ad : Unifmu;
    part es : Unifmu;
    part mon : EuFbkNurvSafeOperation;
    part src : Source;
    part wtc : Watcher;
    connect src.sensor_data to ad.sensor_data;
    connect src.error_threshold to ad.error_threshold;
    connect src.kalman_input to ad.kalman_input;
    connect ad.verdict to es.lid_open;
    connect ad.verdict to mon.anomaly;
    connect es.ctrl_desired_temperature to wtc.desired_temperature;
    connect wtc.energy_saving to mon.energy_saving;
  }
}
