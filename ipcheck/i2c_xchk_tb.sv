// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// i2c_xchk_tb.sv -- I2C_apb (open-ip-portfolio) through its documented
// register map (docs/ip/I2C.md) against an I2C controller written from the
// I2C-bus specification (UM10204): open-drain SDA with a pull-up, START /
// repeated START / STOP, 7-bit address + R/W, ACK / NACK in the ninth clock.
//   * a bus monitor flags any SDA change while SCL is high that the
//     controller did not make (only START and STOP may do that)
//   * writes with ACK per byte, reads with ACK then NACK, wrong address
//     (NACK, rest ignored), repeated START, STOP in the middle of a byte
//   * the register contract: RX pop, RX_AVAIL / RX_OVF / BYTE, STATUS.busy,
//     TX returned on reads
`ifndef SEED
`define SEED 1
`endif
module i2c_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h49430200;
  localparam int N_WORDS = 8;
  localparam logic [6:0] ADDR = 7'h50;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, FLAGS = 12'h00C,
                          TX = 12'h014, RX = 12'h018, STATUS = 12'h01C;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq;
  always #5 PCLK = ~PCLK;

  // open-drain bus with pull-up
  tri1 sda;
  logic scl = 1, m_low = 0;
  assign sda = m_low ? 1'b0 : 1'bz;

  I2C_apb #(.I2C_ADDR(ADDR)) dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA,
      .PSTRB, .PRDATA, .PREADY, .PSLVERR, .irq, .sda, .scl);

  `include "apb_bfm.svh"

  // ---------------- bus monitor ----------------
  bit m_edge = 0;               // the controller is making a START / STOP
  int sda_viol = 0;
  always @(sda) if (PRESETN && scl === 1'b1 && !m_edge) sda_viol++;
  int bytes_irq = 0;
  always @(posedge PCLK) if (dut.u_core.irq) bytes_irq++;

  // ---------------- controller ----------------
  localparam int Q = 4;         // PCLK clocks per quarter SCL period (SCL low / high = 2 Q)
  task automatic wq(input int n = 1); repeat (n * Q) @(negedge PCLK); endtask
  task automatic start();       // also a repeated START
    m_low = 0; wq();
    scl = 1; wq();
    m_edge = 1; m_low = 1; #1 m_edge = 0;
    wq();
    scl = 0; wq();
  endtask
  task automatic stop();
    m_low = 1; wq();
    scl = 1; wq();
    m_edge = 1; m_low = 0; #1 m_edge = 0;
    wq(2);
  endtask
  task automatic wbit(input bit b);
    m_low = !b; wq();
    scl = 1; wq(2);
    scl = 0; wq();
  endtask
  task automatic rbit(output bit b);
    m_low = 0; wq();
    scl = 1; wq();
    b = sda; wq();
    scl = 0; wq();
  endtask
  // byte out, returns 1 when the target ACKed
  task automatic wbyte(input logic [7:0] d, output bit ack);
    bit a;
    for (int i = 7; i >= 0; i--) wbit(d[i]);
    rbit(a);
    ack = !a;
  endtask
  task automatic rbyte(output logic [7:0] d, input bit ack);
    bit b;
    for (int i = 7; i >= 0; i--) begin rbit(b); d[i] = b; end
    wbit(!ack);
  endtask

  logic [31:0] v, st;
  int seed = `SEED;
  initial begin
    bit ack;
    logic [7:0] d;
    void'($urandom(seed));
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h7);
    apb_wr(IRQ_STATUS, 32'h7);
    apb_rd(STATUS, v);
    chk(v == 0 && sda === 1'b1, "idle: STATUS.busy 0, SDA released");

    // ---- write: address + 4 bytes, RX read between bytes
    begin
      int nack = 0, bad = 0, b0;
      logic [7:0] w;
      b0 = bytes_irq;
      start();
      wbyte({ADDR, 1'b0}, ack);
      chk(ack, "write: own address ACKed");
      apb_rd(STATUS, v);
      chk(v[0], "write: STATUS.busy after the address");
      for (int i = 0; i < 4; i++) begin
        w = 8'($urandom);
        wbyte(w, ack);
        if (!ack) nack++;
        apb_rd(FLAGS, v);
        if (!v[0]) bad++;
        apb_rd(RX, v);
        if (v[7:0] != w) begin bad++; $display("  rx %h exp %h", v[7:0], w); end
      end
      stop();
      chk(nack == 0, "write: every data byte ACKed");
      chk(bad == 0, "write: each byte in RX with FLAGS.RX_AVAIL");
      chk(bytes_irq == b0 + 4, "write: one BYTE interrupt per byte");
      apb_rd(STATUS, v);
      chk(v[0] == 0, "STOP: STATUS.busy clears");
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && st[1] && !st[2] && irq === 1'b1, "write: BYTE and RX_AVAIL set, no RX_OVF, irq high");
      apb_wr(IRQ_STATUS, 32'h7);
    end

    // ---- RX overflow: two bytes, RX not read
    begin
      start();
      wbyte({ADDR, 1'b0}, ack);
      wbyte(8'h4D, ack);
      wbyte(8'hB2, ack);
      stop();
      apb_rd(IRQ_STATUS, st);
      chk(st[2], "second byte with RX full sets RX_OVF");
      apb_rd(RX, v);
      chk(v[7:0] == 8'h4D, "RX keeps the first byte");
      apb_rd(FLAGS, v);
      chk(!v[0], "RX empty after the pop");
      apb_wr(IRQ_STATUS, 32'h7);
    end

    // ---- another address: NACK, the rest of the transfer ignored
    begin
      int b0;
      b0 = bytes_irq;
      start();
      wbyte({ADDR ^ 7'h01, 1'b0}, ack);
      chk(!ack, "other address 0x51: NACK");
      apb_rd(STATUS, v);
      chk(!v[0], "other address: STATUS.busy stays 0");
      wbyte(8'h00, ack);
      chk(!ack && bytes_irq == b0, "other address: following byte neither ACKed nor received");
      stop();
      start();
      wbyte({ADDR ^ 7'h40, 1'b1}, ack);
      chk(!ack, "other address 0x10 (read): NACK");
      stop();
    end

    // ---- read: TX returned, ACK, then NACK and STOP
    begin
      logic [7:0] r1, r2;
      apb_wr(TX, 32'h5C);
      start();
      wbyte({ADDR, 1'b1}, ack);
      chk(ack, "read: own address ACKed");
      rbyte(r1, 1);
      rbyte(r2, 0);
      chk(r1 == 8'h5C && r2 == 8'h5C, $sformatf("read: TX sent MSB first for each byte (%h %h)", r1, r2));
      chk(sda === 1'b1, "read: target releases SDA after the controller's NACK");
      stop();
      apb_rd(STATUS, v);
      chk(!v[0], "read: STATUS.busy clears");
    end

    // ---- every TX value, read one byte each
    begin
      int bad = 0;
      for (int i = 0; i < 12; i++) begin
        logic [7:0] t, r;
        t = i == 0 ? 8'h00 : i == 1 ? 8'hFF : i == 2 ? 8'h80 : i == 3 ? 8'h01 : 8'($urandom);
        apb_wr(TX, {24'h0, t});
        start();
        wbyte({ADDR, 1'b1}, ack);
        rbyte(r, 0);
        stop();
        if (!ack || r != t) begin bad++; $display("  read %h exp %h", r, t); end
      end
      chk(bad == 0, "read: 12 single-byte reads incl. 0x00 / 0xFF / 0x80 / 0x01");
    end

    // ---- repeated START: write one byte, then read without STOP
    begin
      logic [7:0] r;
      bit a1, a2;
      apb_wr(TX, 32'hE1);
      start();
      wbyte({ADDR, 1'b0}, a1);
      wbyte(8'h07, ack);
      start();                                   // Sr
      wbyte({ADDR, 1'b1}, a2);
      rbyte(r, 0);
      stop();
      apb_rd(RX, v);
      chk(a1 && ack && a2, "repeated START: address, byte and the read address ACKed");
      chk(v[7:0] == 8'h07 && r == 8'hE1, "repeated START: written byte in RX, read returns TX");
    end

    // ---- STOP after four bits of a byte: no byte, idle, next transfer fine
    begin
      int b0;
      apb_wr(IRQ_STATUS, 32'h7);
      b0 = bytes_irq;
      start();
      wbyte({ADDR, 1'b0}, ack);
      for (int i = 0; i < 4; i++) wbit(1'b1);
      stop();
      apb_rd(STATUS, v);
      chk(!v[0] && bytes_irq == b0, "STOP inside a byte: back to idle, no byte");
      start();
      wbyte({ADDR, 1'b0}, ack);
      wbyte(8'h6E, ack);
      stop();
      apb_rd(RX, v);
      chk(ack && v[7:0] == 8'h6E, "transfer after the aborted one");
    end

    chk(sda_viol == 0, $sformatf("target never changed SDA while SCL was high (%0d times)", sda_viol));
    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(50_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
