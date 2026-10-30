// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// usb_xchk_tb.sv -- USB_apb (open-ip-portfolio, docs/ip/USB.md, a USB
// full-speed device) against a host written from the USB 2.0 specification
// (chapters 7, 8 and 9), not from the RTL:
//   * the host transmitter: NRZI, bit stuffing after six ones, SYNC, PID with
//     its check nibble, CRC5 / CRC16 in their textbook (non-reflected) form,
//     EOP = SE0 for two bit times then J; its bit rate is 12 Mb/s +0.25 % for
//     the first half of the test and -0.25 % for the second (the 7.1.11 limit)
//   * the host receiver works from the line alone: it times every J / K / SE0
//     interval, so it checks the device's bit times, SYNC, PID, bit
//     stuffing, CRC16, the EOP width (SE0 160 .. 175 ns, then J) and the
//     inter-packet delay (2 .. 6.5 bit times after the host EOP, 7.1.18)
//   * the D+ device pull-up and the host D- pull-down give the J idle state
//   * chapter 9 enumeration: bus reset, GET_DESCRIPTOR(DEVICE) with wLength
//     64 and 8, SET_ADDRESS, GET / SET_CONFIGURATION, the default and
//     addressed states, a vendor request, an EP1 interrupt-IN endpoint
//   * chapter 8 rules: DATA0 / DATA1 toggles (SETUP data DATA0, data / status
//     stage DATA1 first), retransmission after a lost ACK, a duplicated OUT
//     ACKed and dropped, NAK while not configured, protocol STALL cleared by
//     the next SETUP, no answer to another address or to an SOF
//   * faults the device must drop and report on IRQ_STATUS.RXERR: CRC5,
//     CRC16 and bit-stuffing errors
//   The CRCs are anchored to two packets of the USB 2.0 specification era
//   captures: SETUP addr 0 endp 0 = 2D 00 10, and the GET_DESCRIPTOR SETUP
//   data 80 06 00 01 00 00 40 00 with CRC16 bytes DD 94.
`timescale 1ns/1ps
`ifndef SEED
`define SEED 1
`endif
module usb_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
`ifdef DBG
    $display("%t check %0d %s", $realtime, checks, msg);
`endif
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h55310200;
  localparam int N_WORDS = 5;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008;
  localparam real TB_NOM = 1000.0 / 12.0;      // 83.333 ns, the device's nominal bit time

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq;
  wire dp, dm;
  pullup (dp);                       // 1.5 kOhm device pull-up on D+ (full speed)
  pulldown (dm);                     // 15 kOhm host pull-down
  always #(500.0 / 48.0) PCLK = ~PCLK;   // 48 MHz: four clocks per bit

  USB_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
               .PRDATA, .PREADY, .PSLVERR, .irq, .dp, .dm);

  `include "apb_bfm.svh"

  // ---------------- host line drivers ----------------
  logic h_oe = 0, h_dp = 1, h_dm = 0;
  assign dp = h_oe ? h_dp : 1'bz;
  assign dm = h_oe ? h_dm : 1'bz;
  real tb = TB_NOM;                  // host bit time

  // ---------------- CRCs (USB 2.0, 8.3.5), textbook form ----------------
  // bits in transmission order; result transmitted MSB first
  bit cb [0:1023];
  function automatic logic [4:0] crc5(input int n);
    logic [4:0] c;
    c = 5'h1F;
    for (int i = 0; i < n; i++) c = {c[3:0], 1'b0} ^ ((cb[i] ^ c[4]) ? 5'h05 : 5'h00);
    return ~c;
  endfunction
  function automatic logic [15:0] crc16(input int n);
    logic [15:0] c;
    c = 16'hFFFF;
    for (int i = 0; i < n; i++) c = {c[14:0], 1'b0} ^ ((cb[i] ^ c[15]) ? 16'h8005 : 16'h0);
    return ~c;
  endfunction

  // ---------------- packet assembly ----------------
  // pkt[] holds the bits after SYNC (PID first), in transmission order
  bit pkt [0:1023];
  int np;
  logic [7:0] pay [0:63];
  task automatic put_byte(input logic [7:0] b);
    for (int i = 0; i < 8; i++) begin pkt[np] = b[i]; np++; end
  endtask
  task automatic put_pid(input logic [3:0] pid);
    np = 0;
    put_byte({~pid, pid});
  endtask
  // token: PID, ADDR[6:0], ENDP[3:0], CRC5
  task automatic build_token(input logic [3:0] pid, input logic [6:0] a, input logic [3:0] ep, input bit bad);
    logic [4:0] c;
    put_pid(pid);
    for (int i = 0; i < 7; i++) begin pkt[np] = a[i]; cb[i] = a[i]; np++; end
    for (int i = 0; i < 4; i++) begin pkt[np] = ep[i]; cb[7 + i] = ep[i]; np++; end
    c = crc5(11) ^ {4'b0, bad};
    for (int i = 4; i >= 0; i--) begin pkt[np] = c[i]; np++; end
  endtask
  task automatic build_sof(input logic [10:0] fr);
    logic [4:0] c;
    put_pid(4'h5);
    for (int i = 0; i < 11; i++) begin pkt[np] = fr[i]; cb[i] = fr[i]; np++; end
    c = crc5(11);
    for (int i = 4; i >= 0; i--) begin pkt[np] = c[i]; np++; end
  endtask
  task automatic build_data(input logic [3:0] pid, input int n, input bit bad);
    logic [15:0] c;
    put_pid(pid);
    for (int k = 0; k < n; k++)
      for (int i = 0; i < 8; i++) begin pkt[np] = pay[k][i]; cb[8*k + i] = pay[k][i]; np++; end
    c = crc16(8 * n) ^ {15'b0, bad};
    for (int i = 15; i >= 0; i--) begin pkt[np] = c[i]; np++; end
  endtask

  // ---------------- host transmitter ----------------
  realtime t_heop = 0;               // host EOP: the SE0 -> J transition
  bit tx_nostuff = 0;                // fault: leave out the stuffed bit
  int nostuff_at = -1;
  task automatic line(input logic p, input logic m, input real bits);
    h_dp = p; h_dm = m;
    #(bits * tb);
  endtask
  task automatic tx_packet();
    logic lvl;
    int ones;
    lvl = 1;                         // idle J
    h_oe = 1;
    for (int i = 0; i < 8; i++) begin     // SYNC 00000001, LSB first
      if (i < 7) lvl = ~lvl;
      line(lvl, ~lvl, 1);
    end
    ones = 1;                        // the SYNC ends in a one
    for (int i = 0; i < np; i++) begin
      if (!pkt[i]) lvl = ~lvl;
      line(lvl, ~lvl, 1);
      ones = pkt[i] ? ones + 1 : 0;
      if (ones == 6) begin
        if (!(tx_nostuff && i >= nostuff_at)) begin lvl = ~lvl; line(lvl, ~lvl, 1); end
        else tx_nostuff = 0;
        ones = 0;
      end
    end
    line(0, 0, 2);                   // EOP: SE0 two bit times
    t_heop = $realtime;
    line(1, 0, 1);                   // then J
    h_oe = 0;
  endtask

  // ---------------- host receiver ----------------
  // returns the bits after SYNC (unstuffed) in rx[], their count in nr
  bit rx [0:1023];
  int nr;
  bit rx_got, rx_sync_ok, rx_stuff_ok, rx_eop_ok;
  real rx_ipd;                       // inter-packet delay, bit times
  int n_jitter = 0, n_eop_bad = 0, n_sync_bad = 0, n_stuff_bad = 0, n_ipd_bad = 0;
  real ipd_min = 99, ipd_max = 0;
  task automatic rx_packet(input real to_bits);
    realtime t0, t_last, t;
    logic [1:0] st, pv;
    int ones, n, nraw;
    bit raw [0:1023];
    bit done;
    rx_got = 0; nr = 0; rx_sync_ok = 0; rx_stuff_ok = 1; rx_eop_ok = 0;
    t0 = $realtime;
    // start of packet: J -> K
    while ({dp, dm} !== 2'b01 && $realtime - t0 < to_bits * TB_NOM) #1;
    if ({dp, dm} === 2'b01) begin
    rx_got = 1;
    rx_ipd = ($realtime - t_heop) / TB_NOM;
    t_last = $realtime;
    pv = 2'b01;
    nraw = 1; raw[0] = 0;            // the first K is a transition: a zero
    done = 0;
    while (!done) begin
      while ({dp, dm} === pv && $realtime - t_last < 40 * TB_NOM) #1;
      t = $realtime;
      st = {dp, dm};
      n = $rtoi((t - t_last) / TB_NOM + 0.5);
      if ((t - t_last) - n * TB_NOM > 3.0 || n * TB_NOM - (t - t_last) > 3.0) n_jitter++;
      if (st === pv) begin done = 1; end            // stuck: no EOP
      else if (st === 2'b00) begin                   // EOP: the remaining bits are ones
        for (int k = 1; k < n; k++) begin raw[nraw] = 1; nraw++; end
        t_last = t;
        while ({dp, dm} === 2'b00 && $realtime - t_last < 10 * TB_NOM) #1;
        rx_eop_ok = ({dp, dm} === 2'b10) && ($realtime - t_last >= 159.0) && ($realtime - t_last <= 176.0);
        if (!rx_eop_ok) begin n_eop_bad++; $display("  EOP SE0 %0.1f ns then %b", $realtime - t_last, {dp, dm}); end
        // J for one bit time, then released to the pull-ups (still J)
        #(TB_NOM);
        done = 1;
      end else begin
        for (int k = 1; k < n; k++) begin raw[nraw] = 1; nraw++; end
        raw[nraw] = 0; nraw++;       // this transition
        t_last = t;
        pv = st;
      end
    end
    // SYNC, then unstuff
    rx_sync_ok = (nraw >= 8);
    for (int i = 0; i < 8 && i < nraw; i++) if (raw[i] !== (i == 7)) rx_sync_ok = 0;
    if (!rx_sync_ok) n_sync_bad++;
    ones = 1;
    for (int i = 8; i < nraw; i++) begin
      if (ones == 6) begin
        if (raw[i]) begin rx_stuff_ok = 0; end
        ones = 0;
      end else begin
        rx[nr] = raw[i]; nr++;
        ones = raw[i] ? ones + 1 : 0;
      end
    end
    if (!rx_stuff_ok) n_stuff_bad++;
    if (rx_ipd < ipd_min) ipd_min = rx_ipd;
    if (rx_ipd > ipd_max) ipd_max = rx_ipd;
    if (rx_ipd < 2.0 || rx_ipd > 6.5) n_ipd_bad++;
    end
  endtask
  function automatic logic [7:0] rx_byte(input int k);
    logic [7:0] b;
    for (int i = 0; i < 8; i++) b[i] = rx[8*k + i];
    return b;
  endfunction
  // classify what came back: PID nibble (or 0 = nothing), data bytes in pay[]
  int r_n;
  bit r_crc_ok;
  function automatic logic [3:0] rx_pid();
    logic [7:0] p;
    if (!rx_got || nr < 8) return 4'h0;
    p = rx_byte(0);
    if (p[7:4] !== ~p[3:0]) return 4'h0;
    return p[3:0];
  endfunction
  task automatic rx_data();
    logic [15:0] c, got;
    r_n = (nr - 8 - 16) / 8;
    r_crc_ok = (nr >= 24) && ((nr - 24) % 8 == 0);
    if (r_crc_ok) begin
      for (int i = 0; i < 8 * r_n; i++) cb[i] = rx[8 + i];
      c = crc16(8 * r_n);
      for (int i = 0; i < 16; i++) got[15 - i] = rx[8 + 8 * r_n + i];
      r_crc_ok = (c === got);
      for (int k = 0; k < r_n; k++) pay[k] = rx_byte(1 + k);
    end
  endtask

  // ---------------- transactions ----------------
  localparam logic [3:0] P_OUT = 4'h1, P_IN = 4'h9, P_SETUP = 4'hD, P_D0 = 4'h3, P_D1 = 4'hB,
                         P_ACK = 4'h2, P_NAK = 4'hA, P_STALL = 4'hE;
  task automatic gap(); #(3 * tb); endtask    // host inter-packet delay
  task automatic hs(input logic [3:0] pid);
    gap(); put_pid(pid); tx_packet();
  endtask
  // SETUP + DATA0 with 8 bytes; returns the device's handshake
  logic [3:0] got;
  task automatic setup(input logic [6:0] a, input logic [7:0] bm, input logic [7:0] rq,
                       input logic [15:0] val, input logic [15:0] idx, input logic [15:0] len,
                       input bit bad_crc = 0, input bit bad_stuff = 0);
    gap(); build_token(P_SETUP, a, 0, 0); tx_packet();
    pay[0] = bm; pay[1] = rq; pay[2] = val[7:0]; pay[3] = val[15:8];
    pay[4] = idx[7:0]; pay[5] = idx[15:8]; pay[6] = len[7:0]; pay[7] = len[15:8];
    gap(); build_data(P_D0, 8, bad_crc);
    if (bad_stuff) begin tx_nostuff = 1; nostuff_at = 0; end
    tx_packet();
    rx_packet(18);
    got = rx_pid();
  endtask
  // IN token; on data checks CRC16, and sends ACK unless told not to
  logic [3:0] in_pid;
  task automatic in_tok(input logic [6:0] a, input logic [3:0] ep, input bit ack = 1, input bit bad_crc = 0);
    gap(); build_token(P_IN, a, ep, bad_crc); tx_packet();
    rx_packet(18);
    in_pid = rx_pid();
    r_n = 0;
    if (in_pid == P_D0 || in_pid == P_D1) begin
      rx_data();
      if (r_crc_ok && ack) hs(P_ACK);
    end
  endtask
  task automatic out_zlp(input logic [6:0] a, input logic [3:0] pid);
    gap(); build_token(P_OUT, a, 0, 0); tx_packet();
    gap(); build_data(pid, 0, 0); tx_packet();
    rx_packet(18);
    got = rx_pid();
  endtask

  // control read: SETUP, IN data stage until a short packet or len, OUT status
  logic [7:0] cr [0:63];
  int cr_n, cr_tgl_bad, cr_crc_bad;
  bit cr_stall;
  task automatic control_read(input logic [6:0] a, input logic [7:0] bm, input logic [7:0] rq,
                              input logic [15:0] val, input logic [15:0] idx, input logic [15:0] len);
    logic [3:0] exp;
    bit fin;
    cr_n = 0; cr_tgl_bad = 0; cr_crc_bad = 0; cr_stall = 0;
    setup(a, bm, rq, val, idx, len);
    chk(got == P_ACK, $sformatf("SETUP %h/%h ACKed (%h)", bm, rq, got));
    exp = P_D1;
    fin = 0;
    for (int k = 0; k < 16 && !fin; k++) begin
      in_tok(a, 0);
      if (in_pid == P_STALL) begin cr_stall = 1; fin = 1; end
      else if (in_pid != P_D0 && in_pid != P_D1) begin cr_tgl_bad++; fin = 1; end
      else begin
        if (in_pid != exp) cr_tgl_bad++;
        if (!r_crc_ok) cr_crc_bad++;
        for (int i = 0; i < r_n; i++) begin cr[cr_n] = pay[i]; cr_n++; end
        exp = (exp == P_D1) ? P_D0 : P_D1;
        if (r_n < 8 || cr_n >= len) fin = 1;
      end
    end
    if (!cr_stall) begin
      out_zlp(a, P_D1);
      chk(got == P_ACK, "control read: status stage OUT DATA1 zero-length ACKed");
    end
  endtask
  // control write without data: SETUP, IN status stage (zero-length DATA1)
  task automatic control_nodata(input logic [6:0] a, input logic [7:0] bm, input logic [7:0] rq,
                                input logic [15:0] val, input logic [15:0] idx, output bit ok);
    setup(a, bm, rq, val, idx, 0);
    ok = (got == P_ACK);
    in_tok(a, 0);
    ok = ok && (in_pid == P_D1) && (r_n == 0) && r_crc_ok;
  endtask

  task automatic bus_reset(input real bits);
    h_oe = 1; h_dp = 0; h_dm = 0;
    #(bits * tb);
    h_dp = 1; #(tb);
    h_oe = 0;
    #(20 * tb);
  endtask

  // ---------------- line observation ----------------
  int n_x = 0, n_se1 = 0;
  always @(dp or dm) if (PRESETN) begin
    #1;
    if ((^{dp, dm}) === 1'bx) begin n_x++; if (n_x < 4) $display("  X %b at %t (host oe %b, device oe %b, after check %0d)", {dp, dm}, $realtime, h_oe, dut.u_core.tx_oe, checks); end
    if ({dp, dm} === 2'b11) begin n_se1++; if (n_se1 < 4) $display("  SE1 at %t", $realtime); end
  end

  // ---------------- test ----------------
  logic [31:0] v;
  int seed = `SEED;
  initial begin
    bit ok;
    logic [31:0] c0, c1;
    logic [7:0] dsc [0:17];
    void'($urandom(seed));

    // the references against the anchors
    build_token(P_SETUP, 0, 0, 0);
    begin
      logic [7:0] b1, b2;
      for (int i = 0; i < 8; i++) begin b1[i] = pkt[8 + i]; b2[i] = pkt[16 + i]; end
      chk(b1 == 8'h00 && b2 == 8'h10, $sformatf("CRC5 anchor: SETUP addr 0 endp 0 = 2D %h %h (00 10)", b1, b2));
    end
    pay[0] = 8'h80; pay[1] = 8'h06; pay[2] = 8'h00; pay[3] = 8'h01;
    pay[4] = 8'h00; pay[5] = 8'h00; pay[6] = 8'h40; pay[7] = 8'h00;
    build_data(P_D0, 8, 0);
    begin
      logic [7:0] b1, b2;
      for (int i = 0; i < 8; i++) begin b1[i] = pkt[72 + i]; b2[i] = pkt[80 + i]; end
      chk(b1 == 8'hDD && b2 == 8'h94, $sformatf("CRC16 anchor: GET_DESCRIPTOR SETUP data ends %h %h (DD 94)", b1, b2));
    end

    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h1);

    tb = TB_NOM * 1.0025;            // host 0.25 % slow
    #(10 * tb);
    chk({dp, dm} === 2'b10, "idle J: the device leaves the bus to the pull-ups");
    bus_reset(100);

    // ---- default state, address 0
    control_read(0, 8'h80, 8'h06, 16'h0100, 0, 64);
    for (int i = 0; i < 18; i++) dsc[i] = cr[i];
    chk(cr_n == 18 && cr_tgl_bad == 0 && cr_crc_bad == 0 && !cr_stall,
        $sformatf("GET_DESCRIPTOR(DEVICE, 64): 18 bytes in DATA1 / DATA0 / DATA1 packets of 8 / 8 / 2 (%0d bytes)", cr_n));
    chk(dsc[0] == 8'd18 && dsc[1] == 8'h01, "device descriptor: bLength 18, bDescriptorType DEVICE");
    chk(dsc[7] == 8 || dsc[7] == 16 || dsc[7] == 32 || dsc[7] == 64, $sformatf("bMaxPacketSize0 %0d", dsc[7]));
    chk(({dsc[3], dsc[2]} == 16'h0110 || {dsc[3], dsc[2]} == 16'h0200) && dsc[17] >= 1,
        $sformatf("bcdUSB %h, bNumConfigurations %0d", {dsc[3], dsc[2]}, dsc[17]));
    control_read(0, 8'h80, 8'h06, 16'h0100, 0, 8);
    chk(cr_n == 8 && cr_tgl_bad == 0, "GET_DESCRIPTOR(DEVICE, 8): one packet of 8 bytes, the first 8 descriptor bytes");
    in_tok(0, 1);
    chk(in_pid == P_NAK, $sformatf("EP1 IN while not configured: NAK (%h)", in_pid));

    // ---- SET_ADDRESS 5
    control_nodata(0, 8'h00, 8'h05, 16'd5, 0, ok);
    chk(ok, "SET_ADDRESS(5): SETUP ACKed, status stage zero-length DATA1");
    in_tok(0, 0);
    chk(!rx_got, "address 0 no longer answered after SET_ADDRESS");
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    chk(cr_n == 1 && cr[0] == 8'h00 && cr_tgl_bad == 0, "GET_CONFIGURATION at address 5: 0 (addressed state)");

    // ---- configuration descriptor (a host reads it before SET_CONFIGURATION)
    control_read(5, 8'h80, 8'h06, 16'h0200, 0, 9);
    if (cr_stall)
      $display("  [NOTE] GET_DESCRIPTOR(CONFIGURATION) is answered with STALL: the device has no configuration, interface or endpoint descriptor, so a USB host cannot enumerate it (chapter 9.4.3) and never learns that EP1 is an interrupt IN endpoint");

    // ---- SET_CONFIGURATION 1
    control_nodata(5, 8'h00, 8'h09, 16'd1, 0, ok);
    chk(ok, "SET_CONFIGURATION(1)");
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    chk(cr_n == 1 && cr[0] == 8'h01, "GET_CONFIGURATION: 1 (configured state)");

    // ---- EP1 interrupt IN: toggles, retransmission after a lost ACK
    in_tok(5, 1);
    c0 = {pay[3], pay[2], pay[1], pay[0]};
    chk(in_pid == P_D0 && r_n == 4 && r_crc_ok, $sformatf("EP1 IN after configuration: DATA0 with 4 bytes (%h, %0d)", in_pid, r_n));
    in_tok(5, 1, 0);                 // ACK lost
    c1 = {pay[3], pay[2], pay[1], pay[0]};
    chk(in_pid == P_D1 && c1 == c0 + 1, "next EP1 IN: DATA1, counter + 1");
    #(40 * tb);
    in_tok(5, 1);
    chk(in_pid == P_D1 && {pay[3], pay[2], pay[1], pay[0]} == c1, "after a lost ACK: the same DATA1 packet again");
    in_tok(5, 1);
    chk(in_pid == P_D0 && {pay[3], pay[2], pay[1], pay[0]} == c1 + 1, "after the ACK: DATA0, counter + 1");

    // ---- vendor request presets the counter
    control_nodata(5, 8'h40, 8'h01, 16'h5678, 16'h1234, ok);
    chk(ok, "vendor request 0x40 / 0x01");
    in_tok(5, 1);
    chk(r_n == 4 && {pay[3], pay[2], pay[1], pay[0]} == 32'h1234_5678, "EP1 counter preset to {wIndex, wValue}");

    // ---- protocol STALL, cleared by the next SETUP
    control_read(5, 8'h80, 8'h00, 0, 0, 2);     // GET_STATUS(device)
    if (cr_stall) $display("  [NOTE] GET_STATUS(DEVICE) is answered with STALL; chapter 9.4.5 requires the two status bytes in every state but default");
    setup(5, 8'h80, 8'h06, 16'h0300, 0, 8);   // a string descriptor: none
    chk(got == P_ACK, "SETUP is ACKed after a protocol STALL");
    in_tok(5, 0);
    chk(in_pid == P_STALL, "GET_DESCRIPTOR(STRING) with no strings: protocol STALL");
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    chk(cr_n == 1 && cr[0] == 8'h01, "the next SETUP clears the STALL");
    in_tok(5, 2);
    chk(in_pid == P_STALL || !rx_got, "IN to an endpoint the device does not have: STALL or no answer");

    // ---- duplicated status OUT (its ACK lost): ACKed again
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    out_zlp(5, P_D1);
    chk(got == P_ACK, "repeated status OUT DATA1: ACKed again");

    // ---- not for this device / SOF
    gap(); build_sof(11'h2A5); tx_packet(); rx_packet(18);
    chk(!rx_got, "no answer to an SOF");
    setup(9, 8'h80, 8'h08, 0, 0, 1);
    chk(!rx_got, "no answer to a SETUP for address 9");

    // ---- faults: dropped, reported, cleared by the next good token
    tb = TB_NOM * 0.9975;            // host 0.25 % fast from here
    apb_wr(IRQ_STATUS, 32'h1);
    in_tok(5, 1, 1, 1);
    chk(!rx_got, "IN with a CRC5 error: no answer");
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b1 && irq === 1'b1, "CRC5 error: IRQ_STATUS.RXERR and irq");
    in_tok(5, 1);
    chk(in_pid == P_D1 || in_pid == P_D0, "the next good IN is answered");
    apb_wr(IRQ_STATUS, 32'h1);
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b0, "RXERR clears after the next good token");

    setup(5, 8'h80, 8'h08, 0, 0, 1, 1);
    chk(!rx_got, "SETUP data with a CRC16 error: no handshake");
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b1, "CRC16 error: IRQ_STATUS.RXERR");
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    chk(cr_n == 1 && cr[0] == 8'h01, "SETUP again: accepted");
    apb_wr(IRQ_STATUS, 32'h1);

    setup(5, 8'h80, 8'h08, 16'hFFFF, 0, 1, 0, 1);   // wValue FFFF: a run of ones to stuff
    chk(!rx_got, "SETUP data with seven ones and no stuffed bit: no handshake");
    apb_rd(IRQ_STATUS, v);
    chk(v[0] == 1'b1, "bit-stuffing error: IRQ_STATUS.RXERR");
    control_read(5, 8'h80, 8'h08, 0, 0, 1);
    chk(cr_n == 1 && cr[0] == 8'h01, "SETUP again after the stuffing error: accepted");
    apb_wr(IRQ_STATUS, 32'h1);

    // ---- bus reset: back to the default state
    bus_reset(100);
    in_tok(5, 1);
    chk(!rx_got, "after a bus reset address 5 is not answered");
    in_tok(0, 1);
    chk(in_pid == P_NAK, "after a bus reset: address 0, not configured (EP1 NAK)");
    control_read(0, 8'h80, 8'h06, 16'h0100, 0, 18);
    chk(cr_n == 18 && cr_tgl_bad == 0, "enumeration again after the bus reset, host 0.25 % fast");

    // ---- line level
    chk(n_sync_bad == 0, "every device packet starts with SYNC KJKJKJKK");
    chk(n_stuff_bad == 0, "device bit stuffing: a zero after every six ones");
    chk(n_jitter == 0, $sformatf("device transitions on whole bit times (%0d off by > 3 ns)", n_jitter));
    chk(n_eop_bad == 0, "device EOP: SE0 160 .. 175 ns, then J");
    chk(n_ipd_bad == 0, $sformatf("device inter-packet delay %0.2f .. %0.2f bit times (2 .. 6.5)", ipd_min, ipd_max));
    chk(n_x == 0 && n_se1 == 0, "no contention, X or SE1 on D+ / D-");

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(50_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
