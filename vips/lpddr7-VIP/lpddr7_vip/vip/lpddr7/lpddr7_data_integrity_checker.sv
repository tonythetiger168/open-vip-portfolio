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

// LPDDR7 Data Integrity Checker (L2)
// UVM component handle (env hookup) + companion SVA module lpddr7_data_integrity_sva
// (concurrent assertions live in the module; LRM does not allow
//  property declarations inside classes).
`ifndef LPDDR7_DATA_INTEGRITY_CHECKER_SV
`define LPDDR7_DATA_INTEGRITY_CHECKER_SV
class lpddr7_data_integrity_checker extends uvm_component;
  `uvm_component_utils(lpddr7_data_integrity_checker)
  virtual lpddr7_if vif;
  function new(string name="lpddr7_data_integrity_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr7_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "LPDDR7: vif not found"); endfunction
endclass

// SVA rule module -- instantiated from tb/tb_top.sv
module lpddr7_data_integrity_sva(lpddr7_if vif);
`include "uvm_macros.svh"
  // REACHABILITY: legal BL values are 8 and 16 per lpddr7_transaction c_bl;
  // the old 4-bit literals {8,9,10,11} could not even express 16.
  property p_lpddr7_bl; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bl inside {5'd8,5'd16}; endproperty
  assert_p_lpddr7_bl: assert property(p_lpddr7_bl) else `uvm_warning("LPDDR7", "Burst length 8/16 failed");
  cover_p_lpddr7_bl: cover property(p_lpddr7_bl);
  property p_lpddr7_tRCD; @(posedge vif.ck) disable iff (!vif.rst_n) $fell(vif.cs_n) |-> ##[5:9] vif.ca[4] == 0; endproperty
  assert_p_lpddr7_tRCD: assert property(p_lpddr7_tRCD) else `uvm_warning("LPDDR7", "tRCD 5-9 cycles failed");
  cover_p_lpddr7_tRCD: cover property(p_lpddr7_tRCD);
  property p_lpddr7_tRP; @(posedge vif.ck) disable iff (!vif.rst_n) $rose(vif.cs_n) |-> ##[5:9] $fell(vif.cs_n); endproperty
  assert_p_lpddr7_tRP: assert property(p_lpddr7_tRP) else `uvm_warning("LPDDR7", "tRP 5-9 cycles failed");
  cover_p_lpddr7_tRP: cover property(p_lpddr7_tRP);
  property p_lpddr7_wck_ratio; @(posedge vif.ck) disable iff (!vif.rst_n) vif.wck_ratio inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_lpddr7_wck_ratio: assert property(p_lpddr7_wck_ratio) else `uvm_warning("LPDDR7", "WCK ratio failed");
  cover_p_lpddr7_wck_ratio: cover property(p_lpddr7_wck_ratio);
  property p_lpddr7_dmi; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dqs_t == 1 && vif.ca[4] == 0 |-> vif.dmi_t == 1; endproperty
  assert_p_lpddr7_dmi: assert property(p_lpddr7_dmi) else `uvm_warning("LPDDR7", "DMI on write failed");
  cover_p_lpddr7_dmi: cover property(p_lpddr7_dmi);
  property p_lpddr7_dbim; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dbim inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_lpddr7_dbim: assert property(p_lpddr7_dbim) else `uvm_warning("LPDDR7", "DBI mode failed");
  cover_p_lpddr7_dbim: cover property(p_lpddr7_dbim);
  property p_lpddr7_crc; @(posedge vif.ck) disable iff (!vif.rst_n) vif.crc_en == 1 && vif.we_n == 0 |-> vif.crc != 8'h00; endproperty
  assert_p_lpddr7_crc: assert property(p_lpddr7_crc) else `uvm_warning("LPDDR7", "CRC on write failed");
  cover_p_lpddr7_crc: cover property(p_lpddr7_crc);
  property p_lpddr7_odt; @(posedge vif.ck) disable iff (!vif.rst_n) vif.odt_ca == 1 |-> vif.cs_n == 0; endproperty
  assert_p_lpddr7_odt: assert property(p_lpddr7_odt) else `uvm_warning("LPDDR7", "ODT-CA active failed");
  cover_p_lpddr7_odt: cover property(p_lpddr7_odt);
  property p_lpddr7_pam4; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pam4_en |-> vif.data_width >= 5'b01000; endproperty
  assert_p_lpddr7_pam4: assert property(p_lpddr7_pam4) else `uvm_warning("LPDDR7", "PAM4 mode failed");
  cover_p_lpddr7_pam4: cover property(p_lpddr7_pam4);
  property p_lpddr7_ecc; @(posedge vif.ck) disable iff (!vif.rst_n) vif.ecc_en |-> vif.data_width >= 5'b01000; endproperty
  assert_p_lpddr7_ecc: assert property(p_lpddr7_ecc) else `uvm_warning("LPDDR7", "On-die ECC failed");
  cover_p_lpddr7_ecc: cover property(p_lpddr7_ecc);
endmodule
`endif
