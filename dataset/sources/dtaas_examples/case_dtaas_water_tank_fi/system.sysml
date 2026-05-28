package PkgWaterTankFi {
  part def Tankcontroller {
    in level : Real;
    out valve : Boolean;
  }
  part def Singlewatertank {
    in valvecontrol : Real;
    out level : Real;
  }
  part def SystemWaterTankFi {
    part x1 : Tankcontroller;
    part x2 : Singlewatertank;
    connect x1.valve to x2.valvecontrol;
    connect x2.level to x1.level;
  }
}
