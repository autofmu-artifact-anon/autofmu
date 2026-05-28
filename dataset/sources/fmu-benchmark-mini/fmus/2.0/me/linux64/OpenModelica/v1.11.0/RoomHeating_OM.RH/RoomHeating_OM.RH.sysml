package RoomHeating_OM {
    // 输入端口定义
    port def InputPort {
        in attribute OAT: Real;
        in attribute fanspeed: Real;
        in attribute valveopen: Real;
    }

    // 输出端口定义
    port def OutputPort {
        out attribute RAT: Real;
    }

    // 主要部件定义
    part def RoomHeating {
        part input: InputPort;
        part output: OutputPort;

        // 属性定义
        attribute Awall: Real; // wall surface area
        attribute LWT: Real; // leaving water temperature
        attribute RATinit: Real; // initial room air temperature
        attribute cAir: Real; // specific heat of air
        attribute cWater: Real; // specific heat of water
        attribute eps: Real; // coil effectiveness
        attribute hAir: Real; // heat transfer coefficient
        attribute mdotat: Real; // total air flow rate available from the fan
        attribute mdotwt: Real; // total water flow rate available from the heat pump
        attribute rohAir: Real; // density of air
        attribute vAir: Real; // room air volume
        attribute TisurfInit: Real; // initial internal surface temperature of the wall
        attribute TosurfInit: Real; // initial external surface temperature of the wall
        attribute aWall: Real; // wall area
        attribute cWall: Real;
        attribute hi: Real; // indoor heat transfer coefficient
        attribute ho: Real; // outdoor heat transfer coefficient
        attribute lWall: Real; // wall thickness
        attribute lambda_Wall: Real;
        attribute rhoWall: Real;
    }
}
