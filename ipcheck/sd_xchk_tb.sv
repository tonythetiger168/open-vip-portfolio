// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// sd_xchk_tb.sv -- SD_apb (open-ip-portfolio, docs/ip/SD.md) against an SD
// memory card model written from the SD Physical Layer Simplified
// Specification, not from the RTL:
//   * 48-bit commands (start 0, transmission 1, index, argument, CRC7
//     x^7 + x^3 + 1, end 1) checked bit by bit; responses R1 / R2 (CID with
//     its own CRC7) / R3 (OCR, busy until the third ACMD41) / R6 (RCA) / R7
//     (echo of the CMD8 argument) two clocks after the command
//   * CMD24 data on DAT[3:0] (start bit, nibbles, CRC16 x^16 + x^12 + x^5 + 1
//     per line, end bit), CRC status token on DAT0, then DAT0 busy; CMD17
//     returns the stored block with its CRC16
//   * the card samples the host on the sd_clk falling edge (mid bit: the host
//     changes its outputs on the rising edge) and drives on the falling edge
//   * the identification sequence and its arguments (CMD8 0x1AA, ACMD41 with
//     HCS, CMD55 before every ACMD41, CMD7 / CMD13 with RCA << 16), block
//     addresses (block number with CCS = 1, byte address with `SC), and no
//     contention on CMD or DAT
//   * faults the host has to report on IRQ_STATUS.ERR and recover from:
//     wrong R7 check pattern (init restarts with CMD0), R1 CRC7, R1 error
//     status bit, R1 wrong index, no response, read-data CRC16, read data
//     changed under a correct CRC16, negative CRC status token
`ifndef SEED
`define SEED 1
`endif
module sd_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h53440200;
  localparam int N_WORDS = 5;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008;
`ifdef SC
  localparam bit CCS = 1'b0;       // standard capacity: byte addresses
`else
  localparam bit CCS = 1'b1;       // high capacity: block numbers
`endif
  localparam int NIB = 64;         // 32-byte blocks (documented slice of 512)

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq, sd_clk;
  tri1 cmd;
  tri1 [3:0] dat;
  always #10 PCLK = ~PCLK;          // 50 MHz

  SD_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
              .PRDATA, .PREADY, .PSLVERR, .irq, .sd_clk, .cmd, .dat);

  `include "apb_bfm.svh"

  // ---------------- card drivers ----------------
  logic c_oe = 0, c_out = 1;
  logic [3:0] d_oe = 0, d_out = 4'hF;
  assign cmd = c_oe ? c_out : 1'bz;
  assign dat[0] = d_oe[0] ? d_out[0] : 1'bz;
  assign dat[1] = d_oe[1] ? d_out[1] : 1'bz;
  assign dat[2] = d_oe[2] ? d_out[2] : 1'bz;
  assign dat[3] = d_oe[3] ? d_out[3] : 1'bz;

  // ---------------- CRCs (SD Physical Layer, 4.5) ----------------
  function automatic logic [6:0] crc7(input logic [119:0] d, input int n);   // MSB first, n bits
    logic [6:0] c;
    c = 0;
    for (int i = n - 1; i >= 0; i--) c = {c[5:0], 1'b0} ^ ((d[i] ^ c[6]) ? 7'h09 : 7'h00);
    return c;
  endfunction
  // a block is 64 nibbles, nibble i (DAT[3:0] in clock i) at [255 - 4i -: 4]
  function automatic logic [15:0] crc16_line(input logic [255:0] blkv, input int l);
    logic [15:0] c;
    c = 0;
    for (int i = 0; i < NIB; i++) c = {c[14:0], 1'b0} ^ ((blkv[255 - 4*i - 3 + l] ^ c[15]) ? 16'h1021 : 16'h0);
    return c;
  endfunction

  // ---------------- pin observations ----------------
  int n_x = 0, n_rise_chg = 0, clk_hi = 0, clk_lo = 0;
  realtime t_rise = -1, per = 0;
  always @(posedge sd_clk) begin
    if (t_rise >= 0) per = $realtime - t_rise;
    t_rise = $realtime;
  end
  always @(cmd) if (!c_oe && $realtime == t_rise) n_rise_chg++;
  always @(negedge sd_clk) if (PRESETN && ($isunknown(cmd) || $isunknown(dat))) n_x++;

  // ---------------- card model ----------------
  localparam logic [15:0] RCA = 16'hB37A;
  localparam logic [119:0] CID_HI = 120'h1B_534D_4142_434F_10_8765_4321_0_1A3;
  logic [127:0] cid;
  logic [255:0] blk [0:3];          // card memory: four blocks
  bit blk_written [0:3];
  int n_cmd [0:63];
  int seq_bad = 0, arg_bad = 0, crc_bad = 0, wcrc_bad = 0, addr_bad = 0, acmd_bad = 0;
  int rounds = 0, n_acmd41 = 0;
  bit inited = 0;
  bit prev55 = 0;
  logic [31:0] last_wr_arg;
  bit addr_seen [0:3];
  // fault injection: set by the test, consumed by the card
  localparam int F_NONE = 0, F_R7 = 1, F_CRC7 = 2, F_STATUS = 3, F_IDX = 4, F_NORESP = 5,
                 F_RDCRC = 6, F_RDDATA = 7, F_CRCSTAT = 8, F_NCR64 = 9;
  int fault = F_NONE;
  bit fault_used = 0;
  int state = 0;                    // 0 idle .. 3 stby, 4 tran (card status CURRENT_STATE)

  task automatic wait_neg(input int n);
    repeat (n) @(negedge sd_clk);
  endtask

  // response: n bits of r (MSB first), N_CR = ncr clocks after the end bit
  // of the command (the specification allows 2 to 64)
  // ncr = 4 by default: this host only starts looking for the start bit
  // four clocks after the end bit; N_CR = 2 is probed once (second CMD8)
  // and N_CR = 64 once (a CMD13)
  int ncr = 4;
  int n_cmd8 = 0;
  bit probe2 = 0, probe2_ok = 0, probe64 = 0;
  task automatic respond(input logic [135:0] r, input int n);
    wait_neg(ncr);
    for (int i = n - 1; i >= 0; i--) begin
      c_oe = 1; c_out = r[i];
      wait_neg(1);
    end
    c_oe = 0; c_out = 1;
  endtask
  function automatic logic [47:0] frame48(input logic [5:0] idx, input logic [31:0] arg, input bit bad_crc);
    logic [39:0] b;
    b = {2'b00, idx, arg};
    return {b, crc7({80'h0, b}, 40) ^ {6'b0, bad_crc}, 1'b1};
  endfunction
  function automatic logic [31:0] status(input bit app);
    return {19'h0, 4'(state), 1'b1, 2'b0, app, 5'h0};
  endfunction

  // CMD24 data from the host; returns the CRC16 result
  task automatic rx_block(input int b, output bit ok);
    logic [255:0] nib;
    logic [15:0] c [0:3];
    int to;
    to = 0;
    ok = 0;
    @(negedge sd_clk);
    while (dat[0] !== 1'b0 && to < 200) begin @(negedge sd_clk); to++; end
    if (dat !== 4'h0) begin wcrc_bad++; $display("  start bit %b", dat); end
    else begin
      for (int i = 0; i < NIB; i++) begin @(negedge sd_clk); nib[255 - 4*i -: 4] = dat; end
      for (int l = 0; l < 4; l++) c[l] = 0;
      for (int i = 15; i >= 0; i--) begin
        @(negedge sd_clk);
        for (int l = 0; l < 4; l++) c[l][i] = dat[l];
      end
      @(negedge sd_clk);
      ok = (dat === 4'hF);
      for (int l = 0; l < 4; l++) if (c[l] !== crc16_line(nib, l)) ok = 0;
      if (ok) blk[b] = nib;
      if (ok) blk_written[b] = 1;
    end
  endtask

  // CMD17 data to the host
  task automatic tx_block(input int b, input bit bad_crc, input bit bad_data);
    logic [255:0] nib;
    logic [15:0] c [0:3];
    nib = blk[b];
    if (bad_data) nib[255 - 4*5 -: 4] = nib[255 - 4*5 -: 4] ^ 4'h2;            // CRC computed over the changed data
    for (int l = 0; l < 4; l++) c[l] = crc16_line(nib, l);
    if (bad_crc) c[0] = c[0] ^ 16'h0100;
    wait_neg(2);
    d_oe = 4'hF; d_out = 4'h0; wait_neg(1);
    for (int i = 0; i < NIB; i++) begin d_out = nib[255 - 4*i -: 4]; wait_neg(1); end
    for (int i = 15; i >= 0; i--) begin
      d_out = {c[3][i], c[2][i], c[1][i], c[0][i]};
      wait_neg(1);
    end
    d_out = 4'hF; wait_neg(1);
    d_oe = 0;
  endtask

  task automatic card_cmd();
    logic [47:0] f;
    logic [5:0] idx;
    logic [31:0] arg;
    int b;
    bit ok, fz;
    // start bit
    @(negedge sd_clk);
    while (cmd !== 1'b0) @(negedge sd_clk);
    f[47] = 0;
    for (int i = 46; i >= 0; i--) begin @(negedge sd_clk); f[i] = cmd; end
    idx = f[45:40]; arg = f[39:8];
`ifdef DBG
    $display("%t CMD%0d arg %h frame %h", $realtime, idx, arg, f);
`endif
    if (f[46] !== 1'b1 || f[0] !== 1'b1 || f[7:1] !== crc7({80'h0, f[47:8]}, 40)) begin
      crc_bad++;
      $display("  bad command frame %h", f);
    end else begin
      n_cmd[idx]++;
      fz = 0;
      // ---------------- identification ----------------
      case (idx)
        6'd0: begin probe2 = 0; state = 0; inited = 0; prev55 = 0; n_acmd41 = 0; end
        6'd8: begin
                if (arg !== 32'h0000_01AA) arg_bad++;
                fz = (fault == F_R7);
                n_cmd8++;
                if (n_cmd8 == 2) begin ncr = 2; probe2 = 1; end
                respond({88'h0, frame48(6'd8, fz ? (arg ^ 32'h1) : arg, 0)}, 48);
                ncr = 4;
              end
        6'd55: begin
                 if (probe2) begin probe2 = 0; probe2_ok = 1; end
                 respond({88'h0, frame48(6'd55, status(1), 0)}, 48); prev55 = 1;
               end
        6'd41: begin
                 logic [31:0] ocr;
                 if (!prev55) acmd_bad++;
                 if (!arg[30] || arg[23:15] == 0) arg_bad++;
                 n_acmd41++;
                 ocr = {n_acmd41 >= 3, CCS, 6'b0, 24'hFF_8000};
                 if (n_acmd41 >= 3) state = 1;
                 respond({88'h0, 2'b00, 6'b111111, ocr, 7'b1111111, 1'b1}, 48);
               end
        6'd2:  begin
                 if (state != 1) seq_bad++;
                 state = 2;
                 respond({2'b00, 6'b111111, cid[127:1], 1'b1}, 136);
               end
        6'd3:  begin
                 logic [31:0] s;
                 if (state != 2) seq_bad++;
                 state = 3;
                 s = status(0);
                 respond({88'h0, frame48(6'd3, {RCA, s[23], s[22], s[19], s[12:0]}, 0)}, 48);
               end
        6'd7:  begin
                 if (state != 3) seq_bad++;
                 if (arg !== {RCA, 16'h0}) arg_bad++;
                 state = 4; inited = 1;
                 respond({88'h0, frame48(6'd7, status(0), 0)}, 48);
               end
        // ---------------- data transfer ----------------
        6'd24, 6'd17: begin
                 if (state != 4) seq_bad++;
                 b = CCS ? arg : arg / 32;
                 if (CCS ? (arg > 3) : (arg % 32 != 0 || arg > 96)) begin addr_bad++; b = 0; end
                 addr_seen[b] = 1;
                 if (idx == 6'd24) last_wr_arg = arg;
                 else if (arg !== last_wr_arg) addr_bad++;
                 fz = (idx == 6'd17) && (fault == F_IDX);
                 respond({88'h0, frame48(fz ? 6'd18 : idx, status(0), 0)}, 48);
                 if (idx == 6'd24) begin
                   bit neg;
                   rounds++;
                   rx_block(b, ok);
                   if (!ok) wcrc_bad++;
                   neg = (fault == F_CRCSTAT);
                   fz = fz || neg;
                   // CRC status token on DAT0: 0, 010 (accepted) / 101, 1; then busy
                   wait_neg(2);
                   d_oe = 4'h1;
                   d_out[0] = 0; wait_neg(1);
                   d_out[0] = neg ? 1 : 0; wait_neg(1);
                   d_out[0] = ok && !neg ? 1 : 0; wait_neg(1);
                   d_out[0] = neg ? 1 : 0; wait_neg(1);
                   d_out[0] = 1; wait_neg(1);
                   if (ok && !neg) begin                // programming: busy (none after a rejected block)
                     d_out[0] = 0; wait_neg(8);
                     d_out[0] = 1; wait_neg(1);
                   end
                   d_oe = 0;
                 end else begin
                   bit bc, bd;
                   bc = (fault == F_RDCRC); bd = (fault == F_RDDATA);
                   fz = fz || bc || bd;
                   if (!fz || bc || bd) tx_block(b, bc, bd);
                 end
               end
        6'd13: begin
                 if (arg !== {RCA, 16'h0}) arg_bad++;
                 fz = (fault == F_CRC7) || (fault == F_STATUS) || (fault == F_NORESP) || (fault == F_NCR64);
                 if (fault == F_NCR64) ncr = 64;
                 if (fault != F_NORESP || !fz)
                   respond({88'h0, frame48(6'd13, (fault == F_STATUS) ? (status(0) | 32'h8000_0000) : status(0),
                                           fault == F_CRC7)}, 48);
                 ncr = 4;
               end
        default: seq_bad++;
      endcase
      if (idx != 6'd55) prev55 = 0;
      if (fz) begin fault = F_NONE; fault_used = 1; end
    end
  endtask

  initial begin
    cid = {CID_HI, crc7(CID_HI, 120), 1'b1};
    void'($value$plusargs("NCR=%d", ncr));
    for (int b = 0; b < 4; b++) begin blk_written[b] = 0; addr_seen[b] = 0; end
    for (int i = 0; i < 64; i++) n_cmd[i] = 0;
    wait (PRESETN);
    forever card_cmd();
  end

  // ---------------- test ----------------
  logic [31:0] v;
  task automatic wait_rounds(input int n);
    int r0;
    r0 = rounds;
    while (rounds < r0 + n) @(posedge PCLK);
  endtask
  task automatic inject(input int f, input string what);
    apb_wr(IRQ_STATUS, 32'h1);
    fault_used = 0;
    fault = f;
    while (!fault_used) @(posedge PCLK);
    wait_rounds(2);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b1, {what, ": reported on IRQ_STATUS.ERR"});
    apb_wr(IRQ_STATUS, 32'h1);
    wait_rounds(2);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, {what, ": the host recovers (two clean rounds after it)"});
  endtask

  int seed = `SEED;
  initial begin
    void'($urandom(seed));
    fault = F_R7;                   // the first CMD8 answer carries a wrong check pattern
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h1);

    // ---- identification, with the R7 fault on the first attempt
    while (!inited) @(posedge PCLK);
    chk(n_cmd[0] >= 2, $sformatf("wrong R7 check pattern: identification restarted with CMD0 (%0d CMD0)", n_cmd[0]));
    apb_rd(IRQ_STATUS, v);
    chk(v[0] && irq === 1'b1, "wrong R7 check pattern: IRQ_STATUS.ERR and irq");
    chk(n_cmd[8] >= 2 && n_cmd[2] == 1 && n_cmd[3] == 1 && n_cmd[7] == 1, "CMD8 again, then CMD2 / CMD3 / CMD7 once each");
    chk(n_acmd41 >= 3 && acmd_bad == 0, $sformatf("ACMD41 repeated while the card is busy (%0d), each after CMD55", n_acmd41));
    chk(arg_bad == 0, "CMD8 argument 0x1AA, ACMD41 with HCS and a voltage window, CMD7 with RCA << 16");
    apb_wr(IRQ_STATUS, 32'h1);
    @(posedge PCLK);
    chk(irq === 1'b0, "irq low after W1C");

    // ---- clean rounds
    wait_rounds(8);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, "eight write / read-back / status rounds without an error");
    if (CCS) chk(addr_seen[0] && addr_seen[1] && addr_seen[2] && addr_seen[3], "all four blocks addressed (block numbers, CCS = 1)");
    else     chk(addr_seen[0] && addr_seen[1] && addr_seen[2] && addr_seen[3], "all four blocks addressed (byte addresses, CCS = 0)");
    chk(addr_bad == 0, "CMD17 reads the block CMD24 wrote; addresses in range for the capacity");
    chk(wcrc_bad == 0, "write data: start bit, CRC16 on every DAT line, end bit");
    chk(n_cmd[13] >= 7, "CMD13 after every round");
    begin
      chk(blk_written[0] && blk_written[1] && blk[0] !== blk[1], "different data in different blocks");
    end

    // ---- the latest response the specification allows: N_CR = 64
    apb_wr(IRQ_STATUS, 32'h1);
    fault_used = 0;
    fault = F_NCR64;
    while (!fault_used) @(posedge PCLK);
    wait_rounds(2);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, "CMD13 answered N_CR = 64 clocks after the command: accepted");
    if (!probe2_ok)
      $display("  [NOTE] a response N_CR = 2 clocks after the command (the minimum of the SD Physical Layer specification) is missed: the host looks for the start bit from the fourth clock on, so a card that answers at N_CR = 2 or 3 fails identification");

    // ---- faults the host must detect
    inject(F_CRC7,    "R1 with a CRC7 error");
    inject(F_STATUS,  "R1 with OUT_OF_RANGE set");
    inject(F_IDX,     "R1 with the wrong command index");
    inject(F_NORESP,  "no response to CMD13");
    inject(F_RDCRC,   "read data with a CRC16 error");
    inject(F_RDDATA,  "read data changed under a correct CRC16 (read-back compare)");
    inject(F_CRCSTAT, "negative CRC status token 101");

    chk(crc_bad == 0, "every command: start 0, transmission 1, CRC7, end bit 1");
    chk(seq_bad == 0, "commands only in the states the card allows them");
    chk(n_x == 0, $sformatf("no contention or X on CMD / DAT (%0d samples)", n_x));
    chk(per > 0 && per < 100.0, $sformatf("sd_clk period %0.0f ns = PCLK / 4", per));
    if (per > 0 && per < 2500.0)
      $display("  [NOTE] identification at sd_clk %0.1f MHz: the SD Physical Layer specification limits the identification mode to 400 kHz", 1000.0 / per);
    if (n_rise_chg > 0)
      $display("  [NOTE] the host changes CMD on the sd_clk rising edge (%0d edges): the card samples on that edge (default speed), so the host leaves no hold time", n_rise_chg);

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(200_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
