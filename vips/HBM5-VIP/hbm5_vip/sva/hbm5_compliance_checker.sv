// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm5_compliance_checker.sv -- HBM5 (High Bandwidth Memory, 5th generation) consolidated SVA compliance checker
// L1 = signal sanity, L2 = command legality, L3 = reset/refresh basics,
// L4 = HBM5 (High Bandwidth Memory, 5th generation)-specific protocol rules (timing windows, bank state,
// refresh interval). Detailed legacy L1/L2/L3 rule sets also live in
// vip/hbm5/hbm5_*checker.sv.
`ifndef HBM5_COMPLIANCE_CHECKER_SV
`define HBM5_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm5_compliance_checker (hbm5_if vif);

  localparam int TRCD_MIN = 6;
  localparam int TRAS_MIN = 16;
  localparam int TFAW_WIN = 12;
  localparam int TREFI_MAX = 3900;

  // Command decode helpers
  wire is_act = !vif.cs_n && !vif.act_n;
  wire is_rd  = !vif.cs_n &&  vif.act_n &&  vif.ras_n && !vif.cas_n &&  vif.we_n;
  wire is_wr  = !vif.cs_n &&  vif.act_n &&  vif.ras_n && !vif.cas_n && !vif.we_n;
  wire is_cas = is_rd || is_wr;
  wire is_pre = !vif.cs_n &&  vif.act_n && !vif.ras_n &&  vif.cas_n && !vif.we_n;
  wire is_ref = !vif.cs_n &&  vif.act_n && !vif.ras_n && !vif.cas_n &&  vif.we_n;

  // Protocol state tracked for L4 rules
  int unsigned cyc = 0;
  bit          bank_open [32];
  int unsigned act_hist [4];
  int          act_hist_idx = 0;
  int unsigned last_ref_cyc = 0;
  bit          seen_ref = 0;

  always @(posedge vif.ck) begin
    if (!vif.rst_n) begin
      cyc <= 0;
      for (int b = 0; b < 32; b++) bank_open[b] <= 1'b0;
      for (int i = 0; i < 4; i++) act_hist[i] <= 0;
      act_hist_idx <= 0;
      last_ref_cyc <= 0;
      seen_ref <= 1'b0;
    end
    else begin
      cyc <= cyc + 1;
      if (is_act) begin
        bank_open[vif.bg * 4 + vif.ba] <= 1'b1;
        act_hist[act_hist_idx] <= cyc;
        act_hist_idx <= (act_hist_idx + 1) % 4;
      end
      if (is_pre) bank_open[vif.bg * 4 + vif.ba] <= 1'b0;
      if (is_ref) begin
        for (int b = 0; b < 32; b++) bank_open[b] <= 1'b0;
        last_ref_cyc <= cyc;
        seen_ref <= 1'b1;
      end
    end
  end

  // ---------------- L1: signal sanity (3) ----------------
  a_hbm5_l1_clk : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    !$isunknown(vif.ck))
    else `uvm_error("SVA_L1", "HBM5: clock unknown")
  a_hbm5_l1_ca  : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    !vif.cs_n |-> !$isunknown({vif.act_n, vif.ras_n, vif.cas_n, vif.we_n}))
    else `uvm_error("SVA_L1", "HBM5: command bus unknown while selected")
  a_hbm5_l1_addr : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    (is_act || is_cas) |-> !$isunknown(vif.addr))
    else `uvm_error("SVA_L1", "HBM5: address unknown during ACT/RD/WR")

  // ---------------- L2: command legality (3) ----------------
  a_hbm5_l2_act_enc : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    !vif.cs_n && !vif.act_n |-> vif.ras_n && vif.cas_n && vif.we_n)
    else `uvm_error("SVA_L2", "HBM5: illegal ACT command encoding")
  a_hbm5_l2_bg : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    (is_act || is_cas || is_pre) |-> vif.bg <= 3)
    else `uvm_error("SVA_L2", "HBM5: bank group out of range")
  a_hbm5_l2_cke : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    !vif.cs_n |-> vif.cke)
    else `uvm_error("SVA_L2", "HBM5: command issued with CKE low")

  // ---------------- L3: reset/refresh basics (2) ----------------
  a_hbm5_l3_reset_idle : assert property (@(posedge vif.ck)
    $fell(vif.rst_n) |-> ##[1:8] vif.cs_n)
    else `uvm_error("SVA_L3", "HBM5: bus not deselected during reset")
  a_hbm5_l3_ref_quiet : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_ref |=> !is_cas[*4])
    else `uvm_error("SVA_L3", "HBM5: CAS issued too soon after refresh")

  // ---------------- L4: HBM5 (High Bandwidth Memory, 5th generation) protocol-specific rules (6) ----------------
  // L4-1: tRCD -- no CAS within TRCD_MIN cycles after ACT
  a_hbm5_l4_trcd : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act |=> !is_cas[*5])
    else `uvm_error("SVA_L4", "HBM5: tRCD violated (CAS too soon after ACT)")

  // L4-2: tRAS -- no PRE within TRAS_MIN cycles after ACT
  a_hbm5_l4_tras : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act |=> !is_pre[*15])
    else `uvm_error("SVA_L4", "HBM5: tRAS violated (PRE too soon after ACT)")

  // L4-3: tFAW -- no more than 4 ACTs inside the rolling TFAW window
  a_hbm5_l4_tfaw : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act |-> (act_hist[act_hist_idx] == 0) ||
               (cyc - act_hist[act_hist_idx] > TFAW_WIN))
    else `uvm_error("SVA_L4", "HBM5: tFAW violated (5th ACT inside window)")

  // L4-4: bank state legality -- RD/WR only to an open bank
  a_hbm5_l4_rdwr_open : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_cas |-> bank_open[vif.bg * 4 + vif.ba])
    else `uvm_error("SVA_L4", "HBM5: RD/WR to a closed bank")

  // L4-5: ACT to an already-open bank is illegal (missing PRE)
  a_hbm5_l4_act_open : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act |-> !bank_open[vif.bg * 4 + vif.ba])
    else `uvm_error("SVA_L4", "HBM5: ACT to an already-open bank")

  // L4-6: refresh interval -- REF at least every TREFI_MAX cycles
  a_hbm5_l4_trefi : assert property (@(posedge vif.ck) disable iff (!vif.rst_n)
    seen_ref |-> (cyc - last_ref_cyc <= TREFI_MAX))
    else `uvm_error("SVA_L4", "HBM5: refresh interval exceeded")

  c_hbm5_l4_act_to_cas : cover property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act ##[TRCD_MIN:TRCD_MIN+4] is_cas);
  c_hbm5_l4_full_cycle : cover property (@(posedge vif.ck) disable iff (!vif.rst_n)
    is_act ##[1:64] is_pre);

endmodule
`endif
