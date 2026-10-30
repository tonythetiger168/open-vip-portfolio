// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// apb_bfm.svh -- APB4 requester and the register checks every open-ip
// peripheral wrapper documents (docs/ip/<IP>.md, "APB wrapper"): ID, W1C
// IRQ_STATUS, IRQ_ENABLE onto irq, SCRATCH with PSTRB lanes, PSLVERR on an
// unmapped or misaligned offset. Included inside a testbench module that
// declares PCLK, the APB signals, chk() and the localparams ID_VALUE and
// N_WORDS (mapped words from 0x000).
  task automatic apb_xfer(input bit w, input logic [11:0] a, input logic [31:0] d,
                          input logic [3:0] strb, output logic [31:0] rd, output bit err);
    @(negedge PCLK);
    PSEL = 1; PENABLE = 0; PWRITE = w; PADDR = a; PWDATA = d; PSTRB = w ? strb : 4'h0;
    @(negedge PCLK);
    PENABLE = 1;
    @(posedge PCLK);
    while (!PREADY) @(posedge PCLK);
    rd = PRDATA; err = PSLVERR;
    @(negedge PCLK);
    PSEL = 0; PENABLE = 0; PWRITE = 0;
  endtask
  task automatic apb_wr(input logic [11:0] a, input logic [31:0] d, input logic [3:0] strb = 4'hF);
    logic [31:0] rd; bit err;
    apb_xfer(1, a, d, strb, rd, err);
  endtask
  task automatic apb_rd(input logic [11:0] a, output logic [31:0] d);
    bit err;
    apb_xfer(0, a, 0, 0, d, err);
  endtask

  // the register checks shared by every wrapper
  task automatic apb_common_checks();
    logic [31:0] v; bit err;
    apb_xfer(0, 12'h000, 0, 0, v, err);
    chk(v == ID_VALUE && !err, $sformatf("ID reads %h", v));
    apb_xfer(1, 12'h010, 32'hA5A5_5A5A, 4'hF, v, err);
    apb_xfer(1, 12'h010, 32'h1234_5678, 4'b0101, v, err);
    apb_xfer(0, 12'h010, 0, 0, v, err);
    chk(v == 32'hA534_5A78 && !err, $sformatf("SCRATCH with PSTRB 0101 reads %h", v));
    apb_xfer(1, 12'h000, 32'hFFFF_FFFF, 4'hF, v, err);
    apb_xfer(0, 12'h000, 0, 0, v, err);
    chk(v == ID_VALUE, "ID ignores writes");
    apb_xfer(0, 12'(4 * N_WORDS), 0, 0, v, err);
    chk(err && v == 0, "first unmapped offset: PSLVERR, reads 0");
    apb_xfer(1, 12'hFFC, 32'h1, 4'hF, v, err);
    chk(err, "last offset 0xFFC: PSLVERR");
    apb_xfer(0, 12'h012, 0, 0, v, err);
    chk(err, "misaligned offset: PSLVERR");
    apb_xfer(0, 12'h008, 0, 0, v, err);
    chk(v == 0 && !err, "IRQ_ENABLE resets to 0");
  endtask
