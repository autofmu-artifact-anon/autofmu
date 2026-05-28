package PkgWaterTankSwap {
  part def Tankcontroller {
    in level : Real;
    out valve : Boolean;
  }
  part def Singlewatertank {
    in valvecontrol : Real;
    out level : Real;
  }
  part def Unifmu {
    in valve : Real;
    in level : Real;
    out leak : Boolean;
  }
  part def SystemWaterTankSwap {
    part x1 : Tankcontroller;
    part x2 : Singlewatertank;
    part x3 : Unifmu;
    part x4 : Unifmu;
    connect x1.valve to x2.valvecontrol;
    connect x2.level to x1.level;
    connect x1.valve to x3.valve;
    connect x2.level to x3.level;
    connect x4.valve to x2.valvecontrol;
    connect x4.valve to x3.valve;
    connect x2.level to x4.level;
    connect x3.leak to x4.leak;
  }
}
