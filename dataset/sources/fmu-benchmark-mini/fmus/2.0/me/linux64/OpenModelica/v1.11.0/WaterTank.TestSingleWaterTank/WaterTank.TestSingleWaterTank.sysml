package WaterTank {
    // 属性定义
    attribute def maxlevel: Real;
    attribute def minlevel: Real;
    attribute def area: Real; // Area of tank
    attribute def drain_r: Real;
    attribute def fs_phi: Real;
    attribute def gravity: Real;
    attribute def level_start: Real;
    attribute def liquid_density: Real;
    attribute def valve_outflow_int_initial: Real;
    attribute def volume_initial: Real;

    // 端口定义
    port def OutputPort {
        out attribute valve_outflow_int: Real;
        out attribute volume: Real;
    }

    // 抽象部件定义
    part def TestSingleWaterTank {
        attribute maxlevel: maxlevel;
        attribute minlevel: minlevel;
        attribute area: area;
        attribute drain_r: drain_r;
        attribute fs_phi: fs_phi;
        attribute gravity: gravity;
        attribute level_start: level_start;
        attribute liquid_density: liquid_density;
        attribute valve_outflow_int_initial: valve_outflow_int_initial;
        attribute volume_initial: volume_initial;

        part output: OutputPort;
    }
}
