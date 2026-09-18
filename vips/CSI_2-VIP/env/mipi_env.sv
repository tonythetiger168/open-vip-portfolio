// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mipi_env.sv -- MIPI Environment (CSI-2)
// Agent + end-to-end scoreboard + functional coverage + 9 protocol checkers
//============================================================================

`ifndef MIPI_ENV_SV
`define MIPI_ENV_SV

class mipi_env extends uvm_env;
  `uvm_component_utils(mipi_env)

  mipi_agent agt;
  mipi_cov   cov;
  mipi_sb    sb;

  // Protocol checkers
  csi2_protocol_checker  csi2_chk;
  dsi_protocol_checker   dsi_chk;
  dphy_protocol_checker  dphy_chk;
  cphy_protocol_checker  cphy_chk;
  mphy_protocol_checker  mphy_chk;
  unipro_protocol_checker unipro_chk;
  digrf_protocol_checker digrf_chk;
  hsi_protocol_checker   hsi_chk;
  cse_protocol_checker   cse_chk;

  function new(string name = "mipi_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agt = mipi_agent::type_id::create("agt", this);
    cov = mipi_cov::type_id::create("cov", this);
    sb  = mipi_sb::type_id::create("sb", this);
    csi2_chk  = csi2_protocol_checker::type_id::create("csi2_chk", this);
    dsi_chk   = dsi_protocol_checker::type_id::create("dsi_chk", this);
    dphy_chk  = dphy_protocol_checker::type_id::create("dphy_chk", this);
    cphy_chk  = cphy_protocol_checker::type_id::create("cphy_chk", this);
    mphy_chk  = mphy_protocol_checker::type_id::create("mphy_chk", this);
    unipro_chk = unipro_protocol_checker::type_id::create("unipro_chk", this);
    digrf_chk = digrf_protocol_checker::type_id::create("digrf_chk", this);
    hsi_chk   = hsi_protocol_checker::type_id::create("hsi_chk", this);
    cse_chk   = cse_protocol_checker::type_id::create("cse_chk", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    // end-to-end scoreboard: expected (driver) vs observed (monitor)
    agt.drv.drv_ap.connect(sb.exp_ap);
    agt.mon.ap.connect(sb.obs_ap);
    // functional coverage
    agt.mon.ap.connect(cov.cov_ap);
  endfunction

  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("ENV_RPT", "MIPI VIP Done", UVM_LOW);
    `uvm_info("COV", $sformatf(" Coverage: %0.2f%%", cov.get_cov()), UVM_LOW);
  endfunction
endclass
`endif
