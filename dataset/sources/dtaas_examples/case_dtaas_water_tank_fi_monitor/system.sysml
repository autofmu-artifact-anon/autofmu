package PkgWaterTankFiMonitor {
  part def Tankcontroller {
    in level : Real;
    out valve : Boolean;
  }
  part def Singlewatertank {
    in valvecontrol : Real;
    out level : Real;
  }
  part def Rti {
    in u : Real;
    out y : Integer;
  }
  part def EuFbkNurvM1 {
    in level : Integer;
    out output : Integer;
    in soft_reset : Boolean;
  }
  part def SystemWaterTankFiMonitor {
    part x1 : Tankcontroller;
    part x2 : Singlewatertank;
    part x3 : Rti;
    part x4 : EuFbkNurvM1;
    connect x1.valve to x2.valvecontrol;
    connect x2.level to x1.level;
    connect x2.level to x3.u;
    connect x3.y to x4.level;
  }
}
