// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 Protocol Compliance Checker (L1)
// NOTE: deepened to a module-based SVA checker (concurrent assertions are
// module items); the interface port keeps the original vif.* references.

`ifndef HBM5_PROTOCOL_CHECKER_SV
`define HBM5_PROTOCOL_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm5_protocol_checker (hbm5_if vif);

  property p_hbm5_cmd_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.ca); endproperty
  assert_p_hbm5_cmd_valid: assert property(p_hbm5_cmd_valid) else `uvm_warning("HBM5", "Command valid when CS active failed");
  cover_p_hbm5_cmd_valid: cover property(p_hbm5_cmd_valid);
  property p_hbm5_addr_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.addr); endproperty
  assert_p_hbm5_addr_valid: assert property(p_hbm5_addr_valid) else `uvm_warning("HBM5", "Address valid failed");
  cover_p_hbm5_addr_valid: cover property(p_hbm5_addr_valid);
  property p_hbm5_pseudo_ch; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pseudo_ch <= 3'd7; endproperty
  assert_p_hbm5_pseudo_ch: assert property(p_hbm5_pseudo_ch) else `uvm_warning("HBM5", "Pseudo channel 0-7 failed");
  cover_p_hbm5_pseudo_ch: cover property(p_hbm5_pseudo_ch);
  property p_hbm5_stack_id; @(posedge vif.ck) disable iff (!vif.rst_n) vif.stack_id <= 4'd15; endproperty
  assert_p_hbm5_stack_id: assert property(p_hbm5_stack_id) else `uvm_warning("HBM5", "Stack ID 0-15 failed");
  cover_p_hbm5_stack_id: cover property(p_hbm5_stack_id);

endmodule : hbm5_protocol_checker
`endif
