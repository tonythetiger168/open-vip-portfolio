// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// csi2_xchk_tb.sv -- CSI_2_top (open-ip-portfolio) against CSI-2 packets
// built by tools/run_ip_crosscheck.py (ECC from the CSI-2 parity equations,
// CRC-16 anchored to the specification's checksum examples).
// stim.hex nibbles: 0 = rx_valid low, 2/3 = serial bit 0/1, 8 = checkpoint,
// F = end. exp.hex, 75 bytes per checkpoint: frame_cnt[2] line_cnt[2]
// last_dt last_wc[2] err_flags irq lb_len[2] line[64].
`ifndef NCHK
`define NCHK 1
`endif
module csi2_xchk_tb;
  import xchk_ref_pkg::*;
  localparam int REC = 75;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  logic clk = 0, rst_n = 0, rx_bit = 0, rx_valid = 0;
  logic [8:0] lb_addr = 0;
  wire irq, frame_active;
  wire [15:0] frame_cnt, line_cnt, last_wc, lb_len;
  wire [7:0] last_dt, lb_rdata;
  wire [3:0] err_flags;
  always #5 clk = ~clk;

  CSI_2_top #(.LINE_BYTES(512)) dut (.clk, .rst_n, .rx_bit, .rx_valid, .irq, .frame_active, .frame_cnt,
                                     .line_cnt, .last_dt, .last_wc, .err_flags, .lb_len, .lb_addr, .lb_rdata);

  logic [3:0] stim [0:262143];
  logic [7:0] ex [0:`NCHK * REC - 1];

  initial begin
    int sp, c, b, bad, n;
    $readmemh("stim.hex", stim);
    $readmemh("exp.hex", ex);
    repeat (3) @(negedge clk);
    rst_n = 1;
    @(negedge clk);
    sp = 0; c = 0;
    while (stim[sp] !== 4'hF) begin
      if (stim[sp] == 4'h8) begin
        b = c * REC;
        chk(frame_cnt === {ex[b], ex[b + 1]} && line_cnt === {ex[b + 2], ex[b + 3]},
            $sformatf("checkpoint %0d: frame/line count %0d/%0d, expected %0d/%0d", c, frame_cnt, line_cnt,
                      {ex[b], ex[b + 1]}, {ex[b + 2], ex[b + 3]}));
        chk(last_dt === ex[b + 4] && last_wc === {ex[b + 5], ex[b + 6]},
            $sformatf("checkpoint %0d: DI %h WC %h, expected %h %h", c, last_dt, last_wc, ex[b + 4], {ex[b + 5], ex[b + 6]}));
        chk(err_flags === ex[b + 7][3:0] && irq === ex[b + 8][0],
            $sformatf("checkpoint %0d: err_flags %b irq %b, expected %b %b", c, err_flags, irq, ex[b + 7][3:0], ex[b + 8][0]));
        chk(lb_len === {ex[b + 9], ex[b + 10]}, $sformatf("checkpoint %0d: lb_len %0d", c, lb_len));
        bad = 0;
        n = (lb_len < 64) ? lb_len : 64;
        for (int i = 0; i < n; i++) begin
          lb_addr = i; #1;
          if (lb_rdata !== ex[b + 11 + i]) bad++;
        end
        chk(bad == 0, $sformatf("checkpoint %0d: line buffer holds the last good line (%0d bad)", c, bad));
        c++;
      end else begin
        @(negedge clk);
        rx_valid = stim[sp][1]; rx_bit = stim[sp][0];
      end
      sp++;
    end
    chk(c == `NCHK, "all checkpoints reached");
    if (fails == 0) $display("XCHK_PASS checks=%0d", checks);
    else            $display("XCHK_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
endmodule
