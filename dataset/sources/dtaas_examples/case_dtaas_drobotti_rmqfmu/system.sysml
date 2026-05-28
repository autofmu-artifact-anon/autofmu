package PkgDrobottiRmqfmu {
  part def Unifmu {
    out distance : Integer;
    in xpos : Real;
    in ypos : Real;
  }
  part def Rabbitmq {
    out xpos : Real;
    out ypos : Real;
    in distance : Integer;
  }
  part def SystemDrobottiRmqfmu {
    part distance : Unifmu;
    part rbmq : Rabbitmq;
    connect distance.distance to rbmq.distance;
    connect rbmq.xpos to distance.xpos;
    connect rbmq.ypos to distance.ypos;
  }
}
