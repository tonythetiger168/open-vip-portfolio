// SPDX-License-Identifier: Apache-2.0
// Independent directed contract bench. Does not instantiate portfolio APB_top.
`timescale 1ns/1ps
module apb_window_router_tb;
  logic rst_n=0, psel=0, penable=0, pwrite=0;
  logic [31:0] paddr=0, pwdata=0, prdata;
  logic [3:0] pstrb=0;
  logic [2:0] pprot=0;
  logic pready, pslverr;
  logic [1:0] s_psel;
  logic s_penable, s_pwrite;
  logic [11:0] s_paddr;
  logic [31:0] s_pwdata;
  logic [3:0] s_pstrb;
  logic [2:0] s_pprot;
  logic [31:0] s0_prdata=32'h01234567, s1_prdata=32'h89abcdef;
  logic s0_pready=1, s1_pready=0, s0_pslverr=0, s1_pslverr=0;
  logic [1:0] overlap_select;
  logic overlap_ready, overlap_error;
  integer checks=0, errors=0;
  apb_window_router dut(.*);
  apb_window_router #(.PAGE1(20'h10000)) overlap (
    .rst_n(rst_n), .psel(psel), .penable(penable), .pwrite(pwrite),
    .paddr(paddr), .pwdata(pwdata), .pstrb(pstrb), .pprot(pprot),
    .prdata(), .pready(overlap_ready), .pslverr(overlap_error),
    .s_psel(overlap_select), .s_penable(), .s_pwrite(), .s_paddr(),
    .s_pwdata(), .s_pstrb(), .s_pprot(),
    .s0_prdata(s0_prdata), .s1_prdata(s1_prdata),
    .s0_pready(s0_pready), .s1_pready(s1_pready),
    .s0_pslverr(s0_pslverr), .s1_pslverr(s1_pslverr)
  );
  task automatic check(input logic okay, input string message);
    checks=checks+1;
    if (okay !== 1'b1) begin errors=errors+1; $display("ERROR %s", message); end
  endtask
  initial begin
    #2; check(s_psel===0 && !pready && !pslverr, "reset gates selects and response");
    rst_n=1; psel=1; paddr=32'h10000020; pwrite=1;
    pwdata=32'hcafebabe; pstrb=4'b0101; pprot=3'b101;
    #2; check(s_psel===1 && !s_penable && !pready, "page0 setup");
    check(s_paddr===12'h020 && s_pwrite && s_pwdata===32'hcafebabe && s_pstrb===5 && s_pprot===5, "attributes forwarded unchanged");
    penable=1; #2;
    check(pready && !pslverr && prdata===32'h01234567, "page0 access");
    check(overlap_ready && overlap_error && overlap_select===0, "overlapping windows fail closed");
    penable=0; paddr=32'h10001ffc; pwrite=0; #2;
    check(s_psel===2 && !pready && !s_penable, "back to back page1 setup");
    penable=1; s1_pslverr=1; #2;
    check(!pready && !pslverr && s_psel===2 && s_penable, "wait does not report premature error");
    repeat (3) begin #2; check(!pready && s_psel===2 && s_paddr===12'hffc, "wait keeps selection"); end
    s1_pready=1; #2;
    check(pready && pslverr && prdata===32'h89abcdef, "downstream error completion");
    penable=0; paddr=32'h20000000; #2;
    check(s_psel===0 && !pready, "hole setup has no select");
    penable=1; #2;
    check(pready && pslverr && prdata===0 && s_psel===0, "hole error completion");
    penable=0; paddr=32'h10000001; #2; penable=1; #2;
    check(pready && pslverr && s_psel===0, "misalignment no side effects");
    rst_n=0; #2;
    check(!pready && !pslverr && s_psel===0 && !s_penable, "reset during access");
    rst_n=1; psel=0; #2;
    check(!pready && !pslverr && s_psel===0, "idle isolates response");
    if (errors==0) $display("TEST PASSED: PLATFORM_APB checks=%0d",checks);
    else begin $display("TEST FAILED: %0d errors",errors); $fatal(1); end
    $finish;
  end
  initial begin #1000; $fatal(1,"TIMEOUT"); end
endmodule
