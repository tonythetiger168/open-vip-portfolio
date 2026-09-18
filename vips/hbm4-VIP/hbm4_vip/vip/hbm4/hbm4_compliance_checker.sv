// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_compliance_checker.sv -- HBM4 SVA compliance checker
// L1 = signal sanity, L2 = timing & data integrity, L3 = error handling,
// L4 = HBM4 protocol-specific rules (timing parameters, bank-state
// legality, refresh servicing). Instantiated in tb_top.
// HBM4 stacked DRAM: 2048-bit interface, doubled pseudo-channels vs HBM3, stack_id up to 16Hi.

`ifndef HBM4_COMPLIANCE_CHECKER_SV
`define HBM4_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm4_compliance_checker (hbm4_if vif);

  // ---------------- L1: signal sanity (4) ----------------
  property p_hbm4_cmd_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.ca); endproperty
  assert_p_hbm4_cmd_valid: assert property(p_hbm4_cmd_valid) else `uvm_warning("HBM4", "Command valid failed");
  cover_p_hbm4_cmd_valid: cover property(p_hbm4_cmd_valid);
  property p_hbm4_addr_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.addr); endproperty
  assert_p_hbm4_addr_valid: assert property(p_hbm4_addr_valid) else `uvm_warning("HBM4", "Address valid failed");
  cover_p_hbm4_addr_valid: cover property(p_hbm4_addr_valid);
  property p_hbm4_pseudo_ch; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pseudo_ch <= 2'd3; endproperty
  assert_p_hbm4_pseudo_ch: assert property(p_hbm4_pseudo_ch) else `uvm_warning("HBM4", "Pseudo channel 0-3 failed");
  cover_p_hbm4_pseudo_ch: cover property(p_hbm4_pseudo_ch);
  property p_hbm4_stack_id; @(posedge vif.ck) disable iff (!vif.rst_n) vif.stack_id <= 4'd15; endproperty
  assert_p_hbm4_stack_id: assert property(p_hbm4_stack_id) else `uvm_warning("HBM4", "Stack ID 0-15 failed");
  cover_p_hbm4_stack_id: cover property(p_hbm4_stack_id);

  // ---------------- L2: timing & data integrity (10) ----------------
  property p_hbm4_tRCD; @(posedge vif.ck) disable iff (!vif.rst_n) $fell(vif.cs_n) |-> ##[8:12] vif.ca[4] == 0; endproperty
  assert_p_hbm4_tRCD: assert property(p_hbm4_tRCD) else `uvm_warning("HBM4", "tRCD 8-12 cycles failed");
  cover_p_hbm4_tRCD: cover property(p_hbm4_tRCD);
  property p_hbm4_tRP; @(posedge vif.ck) disable iff (!vif.rst_n) $rose(vif.cs_n) |-> ##[8:12] $fell(vif.cs_n); endproperty
  assert_p_hbm4_tRP: assert property(p_hbm4_tRP) else `uvm_warning("HBM4", "tRP 8-12 cycles failed");
  cover_p_hbm4_tRP: cover property(p_hbm4_tRP);
  property p_hbm4_bl; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bl inside {3'b001,3'b010,3'b011,3'b100,3'b101}; endproperty
  assert_p_hbm4_bl: assert property(p_hbm4_bl) else `uvm_warning("HBM4", "Burst length 2/4/8/16/32 failed");
  cover_p_hbm4_bl: cover property(p_hbm4_bl);
  property p_hbm4_data_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dqs_t == 1 |-> !$isunknown(vif.dq); endproperty
  assert_p_hbm4_data_valid: assert property(p_hbm4_data_valid) else `uvm_warning("HBM4", "Data valid failed");
  cover_p_hbm4_data_valid: cover property(p_hbm4_data_valid);
  property p_hbm4_dbis; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dbis == 1 |-> vif.dqs_t == 1; endproperty
  assert_p_hbm4_dbis: assert property(p_hbm4_dbis) else `uvm_warning("HBM4", "DBI valid failed");
  cover_p_hbm4_dbis: cover property(p_hbm4_dbis);
  property p_hbm4_temp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp <= 8'd127; endproperty
  assert_p_hbm4_temp: assert property(p_hbm4_temp) else `uvm_warning("HBM4", "Temperature failed");
  cover_p_hbm4_temp: cover property(p_hbm4_temp);
  property p_hbm4_no_x; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.ca); endproperty
  assert_p_hbm4_no_x: assert property(p_hbm4_no_x) else `uvm_warning("HBM4", "No X when active failed");
  cover_p_hbm4_no_x: cover property(p_hbm4_no_x);
  property p_hbm4_reset; @(posedge vif.ck) disable iff (!vif.rst_n) vif.rst_n == 0 |-> ##[100:200] vif.rst_n == 1; endproperty
  assert_p_hbm4_reset: assert property(p_hbm4_reset) else `uvm_warning("HBM4", "Reset stable failed");
  cover_p_hbm4_reset: cover property(p_hbm4_reset);
  property p_hbm4_speed; @(posedge vif.ck) disable iff (!vif.rst_n) vif.speed_grade >= 4'd15; endproperty
  assert_p_hbm4_speed: assert property(p_hbm4_speed) else `uvm_warning("HBM4", "Speed grade 2Gbps+ failed");
  cover_p_hbm4_speed: cover property(p_hbm4_speed);
  property p_hbm4_wck; @(posedge vif.ck) disable iff (!vif.rst_n) vif.wck_ratio inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_hbm4_wck: assert property(p_hbm4_wck) else `uvm_warning("HBM4", "WCK ratio failed");
  cover_p_hbm4_wck: cover property(p_hbm4_wck);

  // ---------------- L3: error handling (8) ----------------
  property p_hbm4_pm; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pm_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_hbm4_pm: assert property(p_hbm4_pm) else `uvm_warning("HBM4", "Power management failed");
  cover_p_hbm4_pm: cover property(p_hbm4_pm);
  property p_hbm4_refresh; @(posedge vif.ck) disable iff (!vif.rst_n) vif.refresh |-> ##[1:3900] vif.cs_n == 0; endproperty
  assert_p_hbm4_refresh: assert property(p_hbm4_refresh) else `uvm_warning("HBM4", "Refresh interval failed");
  cover_p_hbm4_refresh: cover property(p_hbm4_refresh);
  property p_hbm4_overtemp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp > 8'd85 |-> vif.cs_n == 1; endproperty
  assert_p_hbm4_overtemp: assert property(p_hbm4_overtemp) else `uvm_warning("HBM4", "Overtemp failed");
  cover_p_hbm4_overtemp: cover property(p_hbm4_overtemp);
  property p_hbm4_dfe; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dfe_tap <= 4'd15; endproperty
  assert_p_hbm4_dfe: assert property(p_hbm4_dfe) else `uvm_warning("HBM4", "DFE tap failed");
  cover_p_hbm4_dfe: cover property(p_hbm4_dfe);
  property p_hbm4_ecc; @(posedge vif.ck) disable iff (!vif.rst_n) vif.ecc_en |-> vif.data_width >= 5'b01000; endproperty
  assert_p_hbm4_ecc: assert property(p_hbm4_ecc) else `uvm_warning("HBM4", "On-die ECC failed");
  cover_p_hbm4_ecc: cover property(p_hbm4_ecc);
  property p_hbm4_pam4; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pam4_en |-> vif.data_width >= 5'b10000; endproperty
  assert_p_hbm4_pam4: assert property(p_hbm4_pam4) else `uvm_warning("HBM4", "PAM4 mode failed");
  cover_p_hbm4_pam4: cover property(p_hbm4_pam4);
  property p_hbm4_bw; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bandwidth <= 32'hFFFFFFFF; endproperty
  assert_p_hbm4_bw: assert property(p_hbm4_bw) else `uvm_warning("HBM4", "Bandwidth failed");
  cover_p_hbm4_bw: cover property(p_hbm4_bw);
  property p_hbm4_latency; @(posedge vif.ck) disable iff (!vif.rst_n) vif.latency_target <= 8'd127; endproperty
  assert_p_hbm4_latency: assert property(p_hbm4_latency) else `uvm_warning("HBM4", "Latency target failed");
  cover_p_hbm4_latency: cover property(p_hbm4_latency);

  // ---------------- L4: HBM4 protocol-specific rules (10) ----------------
  localparam int L4_TRCD  = 10;
  localparam int L4_TRP   = 10;
  localparam int L4_TRAS  = 14;
  localparam int L4_TRFC  = 48;
  localparam int L4_TREFI = 3900;

  // Command decode (mirrors the driver/monitor truth table)
  wire l4_act = (!vif.cs_n) && (!vif.act_n);
  wire l4_rd  = (!vif.cs_n) && vif.act_n && vif.ras_n && (!vif.cas_n) && vif.we_n;
  wire l4_wr  = (!vif.cs_n) && vif.act_n && vif.ras_n && (!vif.cas_n) && (!vif.we_n);
  wire l4_col = l4_rd || l4_wr;
  wire l4_pre = (!vif.cs_n) && vif.act_n && (!vif.ras_n) && vif.cas_n && (!vif.we_n);
  wire l4_ref = (!vif.cs_n) && vif.act_n && (!vif.ras_n) && (!vif.cas_n) && vif.we_n;
  wire [4:0] l4_bidx = {vif.bg, vif.ba};

  // Bank open/close state used by the legality rules below
  bit [31:0] l4_open;
  always @(posedge vif.ck or negedge vif.rst_n) begin
    if (!vif.rst_n) l4_open <= '0;
    else begin
      if (l4_act) l4_open[l4_bidx] <= 1'b1;
      if (l4_pre) l4_open[l4_bidx] <= 1'b0;
      if (l4_ref) l4_open <= '0;
    end
  end

  // L4-1: ACT may only target a closed (precharged) bank
  a_hbm4_l4_act_closed : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_act |-> !l4_open[l4_bidx])
    else `uvm_error("SVA_L4", "hbm4: ACT issued to an already-active bank")
  // L4-2: RD/WR may only target an activated bank
  a_hbm4_l4_col_open : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_col |-> l4_open[l4_bidx])
    else `uvm_error("SVA_L4", "hbm4: RD/WR to a non-activated bank")
  // L4-3: PRE may only target an activated bank
  a_hbm4_l4_pre_open : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_pre |-> l4_open[l4_bidx])
    else `uvm_error("SVA_L4", "hbm4: PRE to a non-activated bank")
  // L4-4: tRCD -- no column command within tRCD cycles after ACT
  a_hbm4_l4_trcd : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_act |-> ##1 (!l4_col)[*(L4_TRCD-1)])
    else `uvm_error("SVA_L4", "hbm4: tRCD violation (column command too soon after ACT)")
  // L4-5: tRP -- no ACT within tRP cycles after PRE
  a_hbm4_l4_trp : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_pre |-> ##1 (!l4_act)[*(L4_TRP-1)])
    else `uvm_error("SVA_L4", "hbm4: tRP violation (ACT too soon after PRE)")
  // L4-6: tRAS -- no PRE within tRAS cycles after ACT
  a_hbm4_l4_tras : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_act |-> ##1 (!l4_pre)[*(L4_TRAS-1)])
    else `uvm_error("SVA_L4", "hbm4: tRAS violation (PRE too soon after ACT)")
  // L4-7: refresh pulse must complete within tRFC (+2) cycles
  a_hbm4_l4_ref_pulse : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    $rose(vif.refresh) |-> ##[1:(L4_TRFC+2)] $fell(vif.refresh))
    else `uvm_error("SVA_L4", "hbm4: refresh pulse wider than tRFC")
  // L4-8: commands require CKE high
  a_hbm4_l4_cke : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    (!vif.cs_n && !vif.act_n) |-> vif.cke)
    else `uvm_error("SVA_L4", "hbm4: command issued while CKE low")

  // L4-9 (HBM): pseudo-channel select must be stable during a command cycle
  a_hbm4_l4_pseudo_ch : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    (!vif.cs_n) |-> $stable(vif.pseudo_ch))
    else `uvm_error("SVA_L4", "hbm4: pseudo-channel switched mid-command")
  // L4-10 (HBM): stack select must be known on any activate
  a_hbm4_l4_stack : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_act |-> !$isunknown(vif.stack_id))
    else `uvm_error("SVA_L4", "hbm4: stack_id unknown on ACT")

  // Refresh must be serviced again within tREFI after each REF command
  c_hbm4_l4_ref_interval : cover property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_ref ##[1:(L4_TREFI)] l4_ref);
  // Full ACT -> column -> PRE bank cycle observed
  c_hbm4_l4_rw_cycle : cover property (@(posedge vif.ck) disable iff (!vif.rst_n)
    l4_act ##[1:64] l4_col ##[1:64] l4_pre);

endmodule
`endif
