// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// PCIe Protocol Checker (UVM): online protocol rule checks on the interface
//============================================================================
`ifndef PCIE_PROTOCOL_CHECKER_SV
`define PCIE_PROTOCOL_CHECKER_SV
class pcie_protocol_checker extends uvm_component;
  `uvm_component_utils(pcie_protocol_checker)

  virtual mp_vip_if vif;
  protocol_e        protocol;
  int unsigned      check_count = 0;
  logic [7:0]       tag_d = 0;
  int unsigned      error_count = 0;

  function new(string name = "pcie_protocol_checker", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual mp_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "PCIe checker: vif not found")
    if (!uvm_config_db#(protocol_e)::get(this, "", "protocol", protocol))
      protocol = PROTO_PCIE_GEN5;
  endfunction

  task run_phase(uvm_phase phase);
    wait (vif.rst_n === 1'b1);
    forever begin
      @(posedge vif.clk);
      if (!vif.rst_n) continue;
      check_count++;
      // Rule: traffic only when link is up
      if (vif.valid && !vif.link_up)
        chk_error("VALID asserted while link is down");
      // Rule: SOP implies a non-zero payload length field
      if (vif.valid && vif.sop && vif.length_dw == 10'd0 && !vif.eop)
        chk_error("SOP with length_dw==0 on multi-beat TLP");
      // Rule: EOP only together with VALID
      if (vif.eop && !vif.valid)
        chk_error("EOP asserted without VALID");
      // Rule: poisoned bit only on valid data beats
      if (vif.ep && !vif.valid)
        chk_error("EP asserted without VALID");
      // Rule: SOP only at a TLP boundary
      if (vif.valid && vif.sop && $past(vif.valid && !vif.eop))
        chk_error("SOP asserted in the middle of a TLP");
      // PCIe: TLP tag recycling check (tag must not change mid-TLP)
      if (vif.valid && !vif.sop && vif.tag != tag_d)
        chk_error("TLP tag changed mid-packet");
      tag_d = vif.tag;
    end
  endtask

  function void chk_error(string msg);
    error_count++;
    `uvm_error("PCIE_CHK", $sformatf("%s (total=%0d)", msg, error_count))
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("PCIE_CHK", $sformatf("PCIe protocol checker: checks=%0d errors=%0d",
      check_count, error_count), UVM_LOW)
  endfunction
endclass
`endif
