package PkgMassSpringDamperMonitor {
  part def EuFbkNurvM2 {
    in x1 : Integer;
    in x2 : Integer;
    out output : Integer;
    in soft_reset : Boolean;
  }
  part def Massspringdamper1 {
    in fk : Real;
    out x1 : Real;
    out v1 : Real;
  }
  part def Massspringdamper2 {
    out fk : Real;
    in x1 : Real;
    in v1 : Real;
    out x2 : Real;
    out v2 : Real;
  }
  part def Rti {
    in u : Real;
    out y : Integer;
  }
  part def SystemMassSpringDamperMonitor {
    part m2 : EuFbkNurvM2;
    part msd1 : Massspringdamper1;
    part msd2 : Massspringdamper2;
    part rti1 : Rti;
    part rti2 : Rti;
    connect msd1.x1 to msd2.x1;
    connect msd1.x1 to rti1.u;
    connect rti1.y to m2.x1;
    connect msd1.v1 to msd2.v1;
    connect msd2.fk to msd1.fk;
    connect msd2.x2 to rti2.u;
    connect rti2.y to m2.x2;
  }
}
