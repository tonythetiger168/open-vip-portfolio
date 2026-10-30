// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// emmc_xchk_tb.sv -- eMMC_apb (open-ip-portfolio, docs/ip/eMMC.md) against an
// e*MMC device model written from JEDEC JESD84 (e*MMC 5.1), not from the RTL:
//   * 48-bit commands (start 0, transmission 1, index, argument, CRC7
//     x^7 + x^3 + 1, end 1) checked bit by bit; responses R1 (card status,
//     CURRENT_STATE of the state the command arrived in) / R2 (CID with its
//     own CRC7) / R3 (OCR, busy for the first two CMD1, sector access mode)
//   * device states idle -> ready -> ident -> stby -> tran, the CMD1 voltage
//     window and access mode, the host-assigned RCA of CMD3, sector
//     addresses on CMD24 / CMD17
//   * CMD24 data on DAT0 (start bit, 256 bits, CRC16 x^16 + x^12 + x^5 + 1,
//     end bit), CRC status token two clocks later, then DAT0 busy; CMD17
//     returns the stored block with its CRC16; DAT[7:1] stay released (1-bit)
//   * the wrapper has no bus clock pin: its core runs the bus on PCLK, so the
//     device here is clocked by PCLK, samples mid bit (falling edge) and
//     drives on the falling edge
//   * faults the host has to report on IRQ_STATUS.ERR and recover from:
//     during identification R3 framing, R2 CID CRC7 and an R1 error bit
//     (each restarts at CMD0); in transfer R1 CRC7 / error bit / wrong index,
//     no response, read-data CRC16, read data changed under a correct CRC16,
//     no read data, negative CRC status token
`ifndef SEED
`define SEED 1
`endif
module emmc_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h654D0200;
  localparam int N_WORDS = 5;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008;
  localparam int NBITS = 256;      // 32-byte blocks (documented slice of 512)

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq;
  logic emmc_rst_n = 1;
  tri1 cmd;
  tri1 [7:0] dat;
  always #10 PCLK = ~PCLK;          // 50 MHz

  eMMC_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
                .PRDATA, .PREADY, .PSLVERR, .irq, .cmd, .dat, .emmc_rst_n);

  `include "apb_bfm.svh"

  // ---------------- device drivers ----------------
  logic c_oe = 0, c_out = 1, d_oe = 0, d_out = 1;
  assign cmd = c_oe ? c_out : 1'bz;
  assign dat[0] = d_oe ? d_out : 1'bz;

  // ---------------- CRCs (JESD84, 8.2) ----------------
  function automatic logic [6:0] crc7(input logic [119:0] d, input int n);   // MSB first, n bits
    logic [6:0] c;
    c = 0;
    for (int i = n - 1; i >= 0; i--) c = {c[5:0], 1'b0} ^ ((d[i] ^ c[6]) ? 7'h09 : 7'h00);
    return c;
  endfunction
  function automatic logic [15:0] crc16(input logic [255:0] b);              // bit 255 first
    logic [15:0] c;
    c = 0;
    for (int i = 255; i >= 0; i--) c = {c[14:0], 1'b0} ^ ((b[i] ^ c[15]) ? 16'h1021 : 16'h0);
    return c;
  endfunction

  // ---------------- pin observations ----------------
  int n_x = 0, n_hi_drv = 0;
  always @(negedge PCLK) if (PRESETN) begin
    if ($isunknown(cmd) || $isunknown(dat[0])) n_x++;
    if (dat[7:1] !== 7'h7F) n_hi_drv++;
  end

  // ---------------- device model ----------------
  localparam logic [119:0] CID_HI = 120'h15_0100_4F50_454E_4950_10_1234_5678_A5;
  // device states (JESD84 CURRENT_STATE)
  localparam int S_IDLE = 0, S_READY = 1, S_IDENT = 2, S_STBY = 3, S_TRAN = 4;
  logic [127:0] cid;
  logic [255:0] blk [0:3];
  bit blk_written [0:3];
  int n_cmd [0:63];
  int seq_bad = 0, arg_bad = 0, crc_bad = 0, wcrc_bad = 0, addr_bad = 0, no_sel = 0;
  int rounds = 0, reads = 0, n_cmd1 = 0;
  bit inited = 0;
  logic [15:0] rca = 0;
  logic [31:0] last_wr_arg;
  bit addr_seen [0:3];
  localparam int F_NONE = 0,
                 F_R3 = 1, F_CID = 2, F_INITST = 3,                       // identification
                 F_CRC7 = 4, F_STATUS = 5, F_IDX = 6, F_NORESP = 7,       // transfer
                 F_RDCRC = 8, F_RDDATA = 9, F_RDNONE = 10, F_CRCSTAT = 11,
                 F_NCR2 = 12, F_NCR64 = 13, F_BUSY = 14, F_NAC = 15;      // timing probes
  int fault = F_NONE;
  bit resync = 0;
  bit fault_used = 0;
  int state = S_IDLE;

  task automatic wait_neg(input int n);
    repeat (n) @(negedge PCLK);
  endtask

  // response N_CR clocks after the end bit of the command (JESD84: 2..64)
  int ncr = 4;
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
  function automatic logic [31:0] status(input int st);
    return {19'h0, 4'(st), 1'b1, 8'h0};    // CURRENT_STATE, READY_FOR_DATA
  endfunction

  // CMD24 data from the host (1-bit bus)
  task automatic rx_block(input int b, output bit ok);
    logic [255:0] d;
    logic [15:0] c;
    int to;
    to = 0;
    ok = 0;
    @(negedge PCLK);
    while (dat[0] !== 1'b0 && to < 200) begin @(negedge PCLK); to++; end
    if (dat[0] !== 1'b0) $display("  no write start bit");
    else begin
      for (int i = 255; i >= 0; i--) begin @(negedge PCLK); d[i] = dat[0]; end
      for (int i = 15; i >= 0; i--) begin @(negedge PCLK); c[i] = dat[0]; end
      @(negedge PCLK);
      ok = (dat[0] === 1'b1) && (c === crc16(d));
      if (ok) begin blk[b] = d; blk_written[b] = 1; end
    end
  endtask

  // CMD17 data to the host, N_AC clocks after the response
  task automatic tx_block(input int b, input bit bad_crc, input bit bad_data, input int nac);
    logic [255:0] d;
    logic [15:0] c;
    d = blk[b];
    if (bad_data) d[200] = ~d[200];                 // CRC computed over the changed data
    c = crc16(d);
    if (bad_crc) c = c ^ 16'h0100;
    wait_neg(nac);
    d_oe = 1; d_out = 0; wait_neg(1);
    for (int i = 255; i >= 0; i--) begin d_out = d[i]; wait_neg(1); end
    for (int i = 15; i >= 0; i--) begin d_out = c[i]; wait_neg(1); end
    d_out = 1; wait_neg(1);
    d_oe = 0;
  endtask

  // identification faults, one per attempt, in this order
  int init_faults [3];
  int init_fi = 0;
  bit init_fault_hit [3];

  task automatic card_cmd();
    logic [47:0] f;
    logic [5:0] idx;
    logic [31:0] arg;
    int b, st0;
    bit ok, fz;
    if (resync) begin                // wait for a gap: CMD high for 60 clocks
      int hi;
      hi = 0;
      while (hi < 60) begin @(negedge PCLK); hi = (cmd === 1'b1) ? hi + 1 : 0; end
      resync = 0;
    end
    @(negedge PCLK);
    while (cmd !== 1'b0) @(negedge PCLK);
    f[47] = 0;
    for (int i = 46; i >= 0; i--) begin @(negedge PCLK); f[i] = cmd; end
    idx = f[45:40]; arg = f[39:8];
`ifdef DBG
    $display("%t CMD%0d arg %h state %0d", $realtime, idx, arg, state);
`endif
    if (f[46] !== 1'b1 || f[0] !== 1'b1 || f[7:1] !== crc7({80'h0, f[47:8]}, 40)) begin
      crc_bad++;
      $display("  bad command frame %h", f);
    end else begin
    n_cmd[idx]++;
    fz = 0;
    st0 = state;
    case (idx)
      // ---------------- identification ----------------
      6'd0:  begin
               if (arg !== 32'h0) arg_bad++;      // GO_IDLE_STATE (not pre-idle / boot)
               state = S_IDLE; n_cmd1 = 0; inited = 0;
             end
      6'd1:  begin
               logic [31:0] ocr;
               bit bad;
               if (state != S_IDLE) seq_bad++;
               // host capacity: sector mode [30:29] = 10, a voltage window in [23:7]
               if (arg[30:29] !== 2'b10 || arg[23:7] == 0) arg_bad++;
               n_cmd1++;
               ocr = {n_cmd1 >= 3, 2'b10, 5'b0, 24'hFF_8080};
               if (n_cmd1 >= 3) state = S_READY;
               bad = (init_fi < 3) && (init_faults[init_fi] == F_R3) && n_cmd1 >= 3;
               if (bad) begin init_fault_hit[init_fi] = 1; init_fi++; end
               respond({88'h0, 2'b00, 6'b111111, ocr, bad ? 7'b1111110 : 7'b1111111, 1'b1}, 48);
             end
      6'd2:  begin
               logic [127:0] c;
               if (state != S_READY) seq_bad++;
               state = S_IDENT;
               c = cid;
               if (init_fi < 3 && init_faults[init_fi] == F_CID) begin
                 c[3] = ~c[3]; init_fault_hit[init_fi] = 1; init_fi++;
               end
               respond({2'b00, 6'b111111, c[127:1], 1'b1}, 136);
             end
      6'd3:  begin
               logic [31:0] s;
               if (state != S_IDENT) seq_bad++;
               if (arg[31:16] == 16'h0 || arg[15:0] !== 16'h0) arg_bad++;
               rca = arg[31:16];
               state = S_STBY;
               s = status(S_IDENT);
               if (init_fi < 3 && init_faults[init_fi] == F_INITST) begin
                 s[22] = 1; init_fault_hit[init_fi] = 1; init_fi++;       // ILLEGAL_COMMAND
               end else inited = 1;
               respond({88'h0, frame48(6'd3, s, 0)}, 48);
             end
      6'd7:  begin
               if (state != S_STBY || arg[31:16] !== rca) seq_bad++;
               state = S_TRAN;
               respond({88'h0, frame48(6'd7, status(st0), 0)}, 48);
             end
      // ---------------- data transfer ----------------
      6'd24, 6'd17: begin
               bit nr;
               // JESD84: the device must be selected (CMD7, stby -> tran) first;
               // a device that honours that does not answer and the host
               // times out for ever, so this model answers and counts it
               if (state == S_STBY) begin no_sel++; state = S_TRAN; st0 = S_TRAN; end
               else if (state != S_TRAN) seq_bad++;
               b = arg;
               if (arg > 3) begin addr_bad++; b = 0; end
               addr_seen[b] = 1;
               if (idx == 6'd24) last_wr_arg = arg;
               else if (arg !== last_wr_arg) addr_bad++;
               nr = (idx == 6'd24 && fault == F_NORESP);
               fz = nr || (idx == 6'd24 && (fault == F_CRC7 || fault == F_NCR64)) ||
                    (idx == 6'd17 && (fault == F_STATUS || fault == F_IDX || fault == F_NCR2));
               if (fz && fault == F_NCR2)  ncr = 2;
               if (fz && fault == F_NCR64) ncr = 64;
               if (!nr)
                 respond({88'h0, frame48((fz && fault == F_IDX) ? 6'd18 : idx,
                                         (fz && fault == F_STATUS) ? (status(st0) | 32'h8000_0000) : status(st0),
                                         fz && fault == F_CRC7)}, 48);
               ncr = 4;
               if (idx == 6'd24 && !(fz && fault != F_NCR64)) begin
                 bit neg, lb;
                 rounds++;
                 rx_block(b, ok);
                 if (!ok) wcrc_bad++;
                 neg = (fault == F_CRCSTAT);
                 lb = (fault == F_BUSY);
                 fz = fz || neg || lb;
                 // CRC status token on DAT0 N_CRC = 2 clocks after the end bit:
                 // 0, 010 (accepted) / 101 (CRC error), 1; then busy while programming
                 wait_neg(1);
                 d_oe = 1;
                 d_out = 0; wait_neg(1);
                 d_out = neg ? 1 : 0; wait_neg(1);
                 d_out = ok && !neg ? 1 : 0; wait_neg(1);
                 d_out = neg ? 1 : 0; wait_neg(1);
                 d_out = 1; wait_neg(1);
                 if (ok && !neg) begin
                   d_out = 0; wait_neg(lb ? 1000 : 8);
                   d_out = 1; wait_neg(1);
                 end
                 d_oe = 0;
               end else if (idx == 6'd17) begin
                 bit bc, bd, bn, ln;
                 bc = (fault == F_RDCRC); bd = (fault == F_RDDATA); bn = (fault == F_RDNONE); ln = (fault == F_NAC);
                 if (!fz) fz = bc || bd || bn || ln;
                 if (!(bn || (fz && fault == F_IDX))) begin
                   tx_block(b, bc, bd, ln ? 100 : 2);
                   reads++;
                   // a host that dropped the transfer after OUT_OF_RANGE (irq)
                   // may have sent commands meanwhile: wait for a gap
                   if (fz && fault == F_STATUS && irq) resync = 1;
                 end
               end
             end
      default: seq_bad++;
    endcase
    if (fz) begin fault = F_NONE; fault_used = 1; end
    end
  endtask

  initial begin
    cid = {CID_HI, crc7(CID_HI, 120), 1'b1};
    for (int b = 0; b < 4; b++) begin blk_written[b] = 0; addr_seen[b] = 0; end
    for (int i = 0; i < 64; i++) n_cmd[i] = 0;
    for (int i = 0; i < 3; i++) init_fault_hit[i] = 0;
    init_faults[0] = F_R3; init_faults[1] = F_CID; init_faults[2] = F_INITST;
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
  task automatic arm(input int f);
    apb_wr(IRQ_STATUS, 32'h1);
    fault_used = 0;
    fault = f;
    while (!fault_used) @(posedge PCLK);
    wait_rounds(2);
    apb_rd(IRQ_STATUS, v);
  endtask
  task automatic inject(input int f, input string what);
    arm(f);
    chk(v[0] == 1'b1, {what, ": reported on IRQ_STATUS.ERR"});
    apb_wr(IRQ_STATUS, 32'h1);
    wait_rounds(2);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, {what, ": the host recovers (two clean rounds after it)"});
  endtask

  int seed = `SEED;
  initial begin
    void'($urandom(seed));
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h1);

    // ---- identification: three attempts fail (R3 framing, CID CRC7, R1 error bit)
    while (!inited) @(posedge PCLK);
    chk(init_fault_hit[0] && init_fault_hit[1] && init_fault_hit[2], "R3 / R2 / R1 identification faults each reached the host");
    chk(n_cmd[0] == 4, $sformatf("each identification fault restarts at CMD0 (%0d CMD0, expected 4)", n_cmd[0]));
    apb_rd(IRQ_STATUS, v);
    chk(v[0] && irq === 1'b1, "identification faults: IRQ_STATUS.ERR and irq");
    chk(n_cmd[2] == 3 && n_cmd[3] == 2, $sformatf("CMD2 after each ready OCR (%0d), CMD3 after each good CID (%0d)", n_cmd[2], n_cmd[3]));
    chk(n_cmd[1] >= 12, $sformatf("CMD1 repeated while the OCR reports busy (%0d)", n_cmd[1]));
    chk(arg_bad == 0, "CMD0 argument 0, CMD1 sector mode with a voltage window, CMD3 RCA in [31:16]");
    apb_wr(IRQ_STATUS, 32'h1);
    @(posedge PCLK);
    chk(irq === 1'b0, "irq low after W1C");

    // ---- clean rounds
    wait_rounds(8);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, "eight write / read-back rounds without an error");
    chk(addr_seen[0] && addr_seen[1] && addr_seen[2] && addr_seen[3], "all four sectors addressed");
    chk(addr_bad == 0, "CMD17 reads the sector CMD24 wrote; sector addresses in range");
    chk(wcrc_bad == 0, "write data: start bit, CRC16, end bit");
    chk(reads >= 7, $sformatf("a CMD17 after every write (%0d)", reads));
    chk(blk_written[0] && blk_written[1] && blk[0] !== blk[1], "different data in different sectors");
    chk(n_hi_drv == 0, "DAT[7:1] released in 1-bit mode");

    // ---- response timing: N_CR = 64 is the latest JESD84 allows
    arm(F_NCR64);
    chk(v[0] == 1'b0, "R1 N_CR = 64 clocks after CMD24: accepted");

    // ---- faults the host must detect
    inject(F_CRC7,    "R1 with a CRC7 error");
    inject(F_STATUS,  "R1 with OUT_OF_RANGE set");
    inject(F_IDX,     "R1 with the wrong command index");
    inject(F_NORESP,  "no response to CMD24");
    inject(F_RDCRC,   "read data with a CRC16 error");
    inject(F_RDDATA,  "read data changed under a correct CRC16 (read-back compare)");
    inject(F_RDNONE,  "no read data after CMD17");
    inject(F_CRCSTAT, "negative CRC status token 101");

    chk(crc_bad == 0, "every command: start 0, transmission 1, CRC7, end bit 1");
    chk(seq_bad == 0, "commands only in the states the device allows them");
    chk(n_x == 0, $sformatf("no contention or X on CMD / DAT0 (%0d samples)", n_x));

    // ---- timing a real e*MMC uses; the device may miss host commands
    // while the host has given up, so these only report
    arm(F_NCR2);
    if (v[0]) $display("  [NOTE] an R1 N_CR = 2 clocks after the command (the JESD84 minimum) is missed: the host looks for the start bit from the fourth clock on, so a device answering at N_CR = 2 or 3 never completes identification");
    arm(F_NAC);
    if (v[0]) $display("  [NOTE] read data 100 clocks after the CMD17 response is reported as an error: the host waits 64 clocks, while a device may take up to its read access time (TAAC + NSAC, typically milliseconds)");
    arm(F_BUSY);
    if (v[0]) $display("  [NOTE] programming busy of 1000 clocks after a write is reported as an error: the host waits 64 clocks, while a device stays busy for its write timeout (milliseconds)");

    if (no_sel > 0)
      $display("  [NOTE] CMD24 / CMD17 sent in stand-by state without CMD7 (SELECT_CARD) %0d times: a JESD84 device ignores them there, so this host never completes a transfer with a real device", no_sel);
    $display("  [NOTE] the wrapper has no CLK output: the bus runs on PCLK, which the board has to route to the device; identification then runs at 50 MHz instead of at most 400 kHz");
    $display("  [NOTE] emmc_rst_n is an input that resets the host; JESD84 RST_n is a host output to the device");

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(200_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
