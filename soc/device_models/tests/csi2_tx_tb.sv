// SPDX-License-Identifier: Apache-2.0
// csi2_tx_model against CSI_2_top (open-ip-portfolio): two frames of three
// RAW8 lines, then one frame of RAW10-typed lines on VC 1.
module csi2_tx_tb;
  logic clk = 1'b0, rst_n = 1'b0;
  always #5 clk = ~clk;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask
  function automatic logic [7:0] pix(input int f, input int l, input int j);
    return 8'(j) ^ 8'(l * 37) ^ 8'(f * 101);
  endfunction

  // bench A: VC 0, RAW8, 2 frames x 3 lines x 20 bytes
  logic va, ba, da; logic [15:0] fa;
  csi2_tx_model #(.FRAMES(2), .LINES(3), .WIDTH(20)) u_txa (
    .clk(clk), .rst_n(rst_n), .en(1'b1), .rx_valid(va), .rx_bit(ba), .frames_sent(fa), .done(da));
  logic        irq_a, fact_a; logic [15:0] fc_a, lc_a, wc_a, len_a; logic [7:0] dt_a, rd_a; logic [3:0] ef_a;
  logic [8:0]  ad_a;
  CSI_2_top u_rxa (.clk(clk), .rst_n(rst_n), .rx_bit(ba), .rx_valid(va), .irq(irq_a), .frame_active(fact_a),
                   .frame_cnt(fc_a), .line_cnt(lc_a), .last_dt(dt_a), .last_wc(wc_a), .err_flags(ef_a),
                   .lb_len(len_a), .lb_addr(ad_a), .lb_rdata(rd_a));
  // bench B: VC 1, DT 0x2B, 1 frame x 2 lines x 300 bytes, short gaps
  logic vb, bb, db; logic [15:0] fb;
  csi2_tx_model #(.FRAMES(1), .LINES(2), .WIDTH(300), .VC(2'd1), .DT(6'h2B), .LEAD(3), .TRAIL(1), .GAP(2)) u_txb (
    .clk(clk), .rst_n(rst_n), .en(1'b1), .rx_valid(vb), .rx_bit(bb), .frames_sent(fb), .done(db));
  logic        irq_b, fact_b; logic [15:0] fc_b, lc_b, wc_b, len_b; logic [7:0] dt_b, rd_b; logic [3:0] ef_b;
  logic [8:0]  ad_b;
  CSI_2_top u_rxb (.clk(clk), .rst_n(rst_n), .rx_bit(bb), .rx_valid(vb), .irq(irq_b), .frame_active(fact_b),
                   .frame_cnt(fc_b), .line_cnt(lc_b), .last_dt(dt_b), .last_wc(wc_b), .err_flags(ef_b),
                   .lb_len(len_b), .lb_addr(ad_b), .lb_rdata(rd_b));

  int irqs = 0, fas = 0;
  logic pfa = 0;
  always @(posedge clk) begin
    if (irq_a || irq_b) irqs++;
    if (fact_a && !pfa) fas++;
    pfa <= fact_a;
  end
  bit ok;
  initial begin
    ad_a = '0; ad_b = '0;
    repeat (3) @(posedge clk); rst_n = 1'b1;
    // frame 1 of bench A: line count and the line buffer after line 3
    wait (fa == 16'd1); @(posedge clk);
    chk(fc_a == 16'd1 && lc_a == 16'd3 && ef_a == 4'h0, "A frame 1: 3 good lines, no errors");
    wait (da && db); repeat (4) @(posedge clk);
    chk(fc_a == 16'd2 && lc_a == 16'd3 && ef_a == 4'h0 && !fact_a, "A: 2 frames, closed, no errors");
    chk(dt_a == 8'h01 && wc_a == 16'd2, "A: last packet FE with frame number 2");
    chk(len_a == 16'd20, "A: line length 20");
    ok = 1;
    for (int j = 0; j < 20; j++) begin ad_a = 9'(j); #1; if (rd_a !== pix(2, 3, j)) ok = 0; end
    chk(ok, "A: last line bytes match the pattern");
    chk(fas == 2, "A: frame_active rose twice");
    chk(fc_b == 16'd1 && lc_b == 16'd2 && ef_b == 4'h0, "B: 1 frame, 2 lines, no errors (1-bit trailer, 2-clock gaps)");
    chk(dt_b == 8'h41 && wc_b == 16'd1, "B: FE on VC 1");
    chk(len_b == 16'd300, "B: line length 300");
    ok = 1;
    for (int j = 0; j < 300; j++) begin ad_b = 9'(j); #1; if (rd_b !== pix(1, 2, j)) ok = 0; end
    chk(ok, "B: last line bytes");
    chk(irqs == 0, "no receiver error interrupt");
    if (fails == 0) $display("FUNC_PASS csi2_tx checks=%0d", checks);
    else            $display("FUNC_FAIL csi2_tx checks=%0d fails=%0d", checks, fails);
    $finish;
  end
  initial begin #50ms; $display("FUNC_FAIL csi2_tx timeout"); $finish; end
endmodule
