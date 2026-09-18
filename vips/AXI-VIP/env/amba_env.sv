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
// AMBA Environment (AXI4 deepened: agent + end-to-end scoreboard + coverage)
//============================================================================
`ifndef AMBA_ENV_SV
`define AMBA_ENV_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import amba_vip_pkg::*;

class amba_env extends uvm_env;
  `uvm_component_utils(amba_env)
  amba_cov               cov;
  amba_sb                sb;
  axi_protocol_checker   axi_chk;
  ahb_protocol_checker   ahb_chk;
  apb_protocol_checker   apb_chk;
  axi_compliance_checker sva_chk;
  axi_agent              agt;
  axi_coverage           fcov;

  function new(string name = "amba_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    cov     = amba_cov::type_id::create("cov", this);
    sb      = amba_sb::type_id::create("sb", this);
    axi_chk = axi_protocol_checker::type_id::create("axi_chk", this);
    ahb_chk = ahb_protocol_checker::type_id::create("ahb_chk", this);
    apb_chk = apb_protocol_checker::type_id::create("apb_chk", this);
    sva_chk = axi_compliance_checker::type_id::create("sva_chk", this);
    agt     = axi_agent::type_id::create("agt", this);
    fcov    = axi_coverage::type_id::create("fcov", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap.connect(sb.obs_ap);        // observed (monitor-decoded)
    agt.drv.drv_ap.connect(sb.exp_ap);    // expected (driver-issued)
    agt.mon.ap.connect(sb.analysis_imp);  // legacy counting
    agt.mon.ap.connect(fcov.analysis_export);
    agt.mon.ap.connect(cov.analysis_export);  // wire amba_cov (was never sampled)
  endfunction

  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("ENV_RPT", "AMBA VIP Done", UVM_LOW)
    `uvm_info("COV", $sformatf("Coverage: %0.2f%%", cov.get_cov()), UVM_LOW)
  endfunction
endclass
`endif
