// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// ddr_pin_mon.sv -- DRAM-side observer for the open-ip *_Lite memory
// controllers, written from the JEDEC DDR4 command truth table (JESD79-4
// table "Command truth table": CS_n, ACT_n, RAS_n/A16, CAS_n/A15, WE_n/A14,
// A10/AP, A12/BC_n) and the DRAM timing definitions, not from the RTL:
//   * decodes ACT / RD / WR / PRE / PREA / REF / MRS from the pins and
//     tracks every bank (open row, last ACT / PRE / write-burst end)
//   * checks tRCD, tRP, tRC, tRAS, tRRD, tWR, tWTR, tRFC (and tRFCpb for
//     per-bank refresh), REF only with the banks it covers precharged,
//     RD / WR only to an open bank, ACT only to a closed one, no undefined
//     command encoding, DQ driven only inside a burst window
//   * measures read / write latency (command to first data beat), checks
//     the 8-beat burst with one DQS toggle per beat, keeps a shadow array
//     keyed by the pin address {BA, row, column} filled from the write
//     bursts and compares every read burst against it
//   * records the refresh history: largest REF-to-REF gap per bank
// Notes (pin-level differences from JESD79-4 that do not change the data
// a controller-plus-array model returns) are printed once each.
module ddr_pin_mon #(
  parameter int NB = 4,
  parameter int T_RCD = 6, T_RP = 6, T_RC = 24, T_RAS = 16, T_RRD = 3,
  parameter int T_WR = 8, T_WTR = 4, T_RFC = 40, T_RFC_PB = 20,
  parameter bit PB_REF = 0            // REF with A10 = 0 refreshes bank BA only
) (
  input logic        clk,
  input logic        rst_n,
  input logic        cs_n, act_n, ras_n, cas_n, we_n,
  input logic [2:0]  ba,
  input logic [13:0] addr,
  input wire  [15:0] dq,
  input wire  [1:0]  dqs
);
  int cyc = 0;
  always @(posedge clk) cyc <= cyc + 1;

  int viol = 0, data_bad = 0, nact = 0, nrd = 0, nwr = 0, npre = 0, nprea = 0, nref = 0,
      nrefpb = 0, nmrs = 0, nnotes = 0;
  int lat_rd [$], lat_wr [$];
  int ref_gap_max [NB];
  int last_ref [NB];

  task automatic bad(input string m);
    viol++;
    if (viol <= 10) $display("  [PIN] cycle %0d: %s", cyc, m);
  endtask
  bit noted [8];
  task automatic note(input int k, input string m);
    if (!noted[k]) begin noted[k] = 1; nnotes++; $display("  [NOTE] %s", m); end
  endtask

  // bank state
  bit          open_ [NB];
  logic [13:0] row [NB];
  int t_act [NB], t_pre [NB], t_wend [NB], t_refpb [NB];
  int t_act_any = -1000, t_prea = -1000, t_ref = -1000, t_wend_any = -1000;
  // data windows: 0 none, 1 write, 2 read
  int win_kind = 0, win_cmd = 0, win_beats = 0;
  logic [27:0] win_key;
  logic [15:0] win_d [8];
  logic last_dqs;
  // shadow array {BA, row[8:0], column[6:4]}; other row / column bits must be 0
  logic [127:0] shadow [0:32767];
  initial for (int i = 0; i < 32768; i++) shadow[i] = '0;
  int pend_kind [$], pend_t [$];
  logic [27:0] pend_key [$];

  initial for (int b = 0; b < NB; b++) begin
    t_act[b] = -1000; t_pre[b] = -1000; t_wend[b] = -1000; t_refpb[b] = -1000;
    ref_gap_max[b] = 0; last_ref[b] = 0;
  end

  always @(negedge clk) if (rst_n) begin
    int b;
    b = int'(ba) % NB;
    // ---------------- command decode ----------------
    if (!cs_n) begin
      if (cyc - t_ref < T_RFC) bad($sformatf("command inside tRFC (%0d after REF)", cyc - t_ref));
      if (!act_n) begin                                        // ACT
        nact++;
        if (ras_n || cas_n || we_n)
          note(0, $sformatf("ACT drives RAS_n/A16 CAS_n/A15 WE_n/A14 = %b%b%b: JESD79-4 takes them as row bits 16:14, so a DDR4 device would open row 0x%0h, not 0x%0h",
                            ras_n, cas_n, we_n, {ras_n, cas_n, we_n, addr}, addr));
        if (open_[b]) bad($sformatf("ACT to open bank %0d", b));
        if (cyc - t_pre[b] < T_RP) bad($sformatf("tRP: ACT bank %0d %0d after PRE", b, cyc - t_pre[b]));
        if (cyc - t_prea < T_RP) bad($sformatf("tRP: ACT %0d after PREA", cyc - t_prea));
        if (cyc - t_act[b] < T_RC) bad($sformatf("tRC: ACT bank %0d %0d after its last ACT", b, cyc - t_act[b]));
        if (cyc - t_act_any < T_RRD) bad($sformatf("tRRD: ACT %0d after the previous ACT", cyc - t_act_any));
        if (PB_REF && cyc - t_refpb[b] < T_RFC_PB) bad($sformatf("tRFCpb: ACT bank %0d %0d after its REFpb", b, cyc - t_refpb[b]));
        open_[b] = 1; row[b] = addr; t_act[b] = cyc; t_act_any = cyc;
      end else if (ras_n && !cas_n) begin                       // RD (WE_n 1) / WR (WE_n 0)
        if (!addr[12]) note(1, "RD / WR with A12/BC_n = 0: with MR0 BL = on-the-fly this is a BC4 burst chop; the bursts here are 8 beats");
        if (addr[10]) note(2, "RD / WR with A10/AP = 1 (auto precharge)");
        if (!open_[b]) bad($sformatf("%s to closed bank %0d", we_n ? "RD" : "WR", b));
        if (cyc - t_act[b] < T_RCD) bad($sformatf("tRCD: %s bank %0d %0d after ACT", we_n ? "RD" : "WR", b, cyc - t_act[b]));
        if (we_n && cyc - t_wend_any < T_WTR) bad($sformatf("tWTR: RD %0d after the end of a write burst", cyc - t_wend_any));
        pend_kind.push_back(we_n ? 2 : 1); pend_t.push_back(cyc);
        if (row[b][13:9] != 0 || addr[9:7] != 0 || addr[3:0] != 0)
          bad($sformatf("address outside the model's array: row %h column %h", row[b], addr[9:0]));
        pend_key.push_back(28'({3'(b), row[b][8:0], addr[6:4]}));
        if (we_n) nrd++; else nwr++;
      end else if (!ras_n && cas_n && !we_n) begin              // PRE / PREA
        for (int i = 0; i < NB; i++) if ((addr[10] || i == b) && open_[i]) begin
          if (cyc - t_act[i] < T_RAS) bad($sformatf("tRAS: PRE bank %0d %0d after ACT", i, cyc - t_act[i]));
          if (cyc - t_wend[i] < T_WR) bad($sformatf("tWR: PRE bank %0d %0d after its write burst", i, cyc - t_wend[i]));
          open_[i] = 0; t_pre[i] = cyc;
        end
        if (addr[10]) begin nprea++; t_prea = cyc; end else npre++;
      end else if (!ras_n && !cas_n && we_n) begin              // REF
        bit all;
        all = !PB_REF || addr[10];
        for (int i = 0; i < NB; i++) if (all || i == b) begin
          if (open_[i]) bad($sformatf("REF with bank %0d open", i));
          if (cyc - t_pre[i] < T_RP) bad($sformatf("tRP: REF %0d after PRE of bank %0d", cyc - t_pre[i], i));
          if (cyc - last_ref[i] > ref_gap_max[i]) ref_gap_max[i] = cyc - last_ref[i];
          last_ref[i] = cyc;
        end
        if (cyc - t_prea < T_RP) bad($sformatf("tRP: REF %0d after PREA", cyc - t_prea));
        if (all) begin nref++; t_ref = cyc; end
        else begin nrefpb++; t_refpb[b] = cyc; end
      end else if (!ras_n && !cas_n && !we_n) nmrs++;           // MRS
      else bad($sformatf("undefined command encoding ACT_n %b RAS_n %b CAS_n %b WE_n %b", act_n, ras_n, cas_n, we_n));
    end

    // ---------------- data bursts ----------------
    if (dq !== 16'hzzzz) begin
      if (win_kind == 0) begin
        if (pend_kind.size() == 0) bad("DQ driven outside any burst");
        else begin
          win_kind = pend_kind.pop_front(); win_cmd = pend_t.pop_front(); win_key = pend_key.pop_front();
          win_beats = 0;
          if (win_kind == 1) lat_wr.push_back(cyc - win_cmd); else lat_rd.push_back(cyc - win_cmd);
        end
      end
      if (win_kind != 0) begin
        if (win_beats > 0 && dqs[0] === last_dqs) data_bad++;      // one DQS toggle per beat
        if (dqs[1] !== ~dqs[0]) data_bad++;
        last_dqs = dqs[0];
        win_d[win_beats] = dq;
        win_beats++;
        if (win_beats == 8) begin
          logic [127:0] line;
          line = {win_d[7], win_d[6], win_d[5], win_d[4], win_d[3], win_d[2], win_d[1], win_d[0]};
          if (win_kind == 1) begin
            shadow[win_key[14:0]] = line;
            t_wend[win_key[14:12] % NB] = cyc; t_wend_any = cyc;
          end else begin
            logic [127:0] e;
            e = shadow[win_key[14:0]];
            if (line !== e) begin
              data_bad++;
              if (data_bad <= 5) $display("  [PIN] cycle %0d: read burst %h, written %h", cyc, line, e);
            end
          end
          win_kind = 0;
        end
      end
    end else if (win_kind != 0) begin
      data_bad++;
      if (data_bad <= 5) $display("  [PIN] cycle %0d: burst stopped after %0d beats", cyc, win_beats);
      win_kind = 0;
    end
  end

  // refresh gap at the end of simulation (the last REF to now)
  function automatic int worst_gap();
    int w;
    w = 0;
    for (int i = 0; i < NB; i++) begin
      if (ref_gap_max[i] > w) w = ref_gap_max[i];
      if (cyc - last_ref[i] > w) w = cyc - last_ref[i];
    end
    return w;
  endfunction
endmodule
