// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//============================================================================
//  MIPI Environment
//  Deepened: mipi_agent (CSE driver/monitor) is closed-loop with the DUT;
//  driver drv_ap -> sb.exp_ap (expected), monitor -> sb.obs_ap (observed)
//  and -> mipi_cov.
//============================================================================
`ifndef MIPI_ENV_SV
`define MIPI_ENV_SV

import uvm_pkg::*;
`include "uvm_macros.svh"
import mipi_vip_pkg::*;

// Protocol checker classes (separate files; pulled into this compilation
// unit so the env can instantiate them regardless of the tool's
// compilation-unit mode; resolved via the scripts/Makefile +incdir list)
`include "csi2_protocol_checker.sv"
`include "dsi_protocol_checker.sv"
`include "dphy_protocol_checker.sv"
`include "cphy_protocol_checker.sv"
`include "mphy_protocol_checker.sv"
`include "unipro_protocol_checker.sv"
`include "digrf_protocol_checker.sv"
`include "hsi_protocol_checker.sv"
`include "cse_protocol_checker.sv"

class mipi_env extends uvm_env;
  `uvm_component_utils(mipi_env)

  mipi_cov   cov;
  mipi_sb    sb;
  mipi_agent agt;

  // Protocol checkers
  csi2_protocol_checker   csi2_chk;
  dsi_protocol_checker    dsi_chk;
  dphy_protocol_checker   dphy_chk;
  cphy_protocol_checker   cphy_chk;
  mphy_protocol_checker   mphy_chk;
  unipro_protocol_checker unipro_chk;
  digrf_protocol_checker  digrf_chk;
  hsi_protocol_checker    hsi_chk;
  cse_protocol_checker    cse_chk;

  function new(string name = "mipi_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    cov = mipi_cov::type_id::create("cov", this);
    sb  = mipi_sb::type_id::create("sb", this);
    agt = mipi_agent::type_id::create("agt", this);
    csi2_chk   = csi2_protocol_checker::type_id::create("csi2_chk", this);
    dsi_chk    = dsi_protocol_checker::type_id::create("dsi_chk", this);
    dphy_chk   = dphy_protocol_checker::type_id::create("dphy_chk", this);
    cphy_chk   = cphy_protocol_checker::type_id::create("cphy_chk", this);
    mphy_chk   = mphy_protocol_checker::type_id::create("mphy_chk", this);
    unipro_chk = unipro_protocol_checker::type_id::create("unipro_chk", this);
    digrf_chk  = digrf_protocol_checker::type_id::create("digrf_chk", this);
    hsi_chk    = hsi_protocol_checker::type_id::create("hsi_chk", this);
    cse_chk    = cse_protocol_checker::type_id::create("cse_chk", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    // CSE end-to-end: expected (driver) / observed (monitor)
    if (agt.is_active == UVM_ACTIVE)
      agt.drv.drv_ap.connect(sb.exp_ap);
    agt.mon.item_collected_port.connect(sb.obs_ap);
    agt.mon.item_collected_port.connect(cov.analysis_export);
  endfunction

  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("ENV_RPT", "MIPI VIP Done", UVM_LOW)
    `uvm_info("COV", $sformatf("Coverage: %0.2f%%", cov.get_cov()), UVM_LOW)
  endfunction
endclass

`endif // MIPI_ENV_SV
