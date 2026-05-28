package PkgMassSpringDamper {
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
  part def SystemMassSpringDamper {
    part msd1 : Massspringdamper1;
    part msd2 : Massspringdamper2;
    connect msd1.x1 to msd2.x1;
    connect msd1.v1 to msd2.v1;
    connect msd2.fk to msd1.fk;
  }
}
