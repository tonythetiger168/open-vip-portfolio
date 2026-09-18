// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM environment -- agent + end-to-end scoreboard + functional coverage.
// (SVA checkers are modules bound at the testbench level.)
`ifndef HBM5_ENV_SV
`define HBM5_ENV_SV

class hbm5_env extends uvm_env;
  `uvm_component_utils(hbm5_env)

  hbm5_agent      agt;
  hbm5_scoreboard sb;
  hbm5_coverage   cov;

  function new(string name = "hbm5_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agt = hbm5_agent::type_id::create("agt", this);
    sb  = hbm5_scoreboard::type_id::create("sb", this);
    cov = hbm5_coverage::type_id::create("cov", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap.connect(sb.obs_ap);        // observed (bus-decoded)
    agt.drv.drv_ap.connect(sb.exp_ap);    // expected (driver-issued)
    agt.mon.ap.connect(cov.analysis_export);
  endfunction
endclass
`endif
