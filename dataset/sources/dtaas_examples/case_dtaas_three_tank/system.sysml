package PkgThreeTank {
  part def Linear {
    in inport : Integer;
    out leak : Integer;
    out outport : Integer;
  }
  part def SystemThreeTank {
    part tank1 : Linear;
    part tank2 : Linear;
    part tank3 : Linear;
    connect tank1.outport to tank2.inport;
    connect tank2.outport to tank3.inport;
  }
}
