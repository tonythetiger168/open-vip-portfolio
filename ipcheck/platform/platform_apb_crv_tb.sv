// SPDX-License-Identifier: Apache-2.0
// Seeded constrained campaign harness, not a UVM execution result.
`timescale 1ns/1ps
module platform_apb_crv_tb;
  logic pclk=0, rst_n=0, psel=0, penable=0, pwrite=0;
  logic [31:0] paddr=0, pwdata=0, prdata;
  logic [3:0] pstrb=4'hf;
  logic [2:0] pprot=0;
  logic pready, pslverr;
  logic [1:0] irq;
  logic [31:0] expected_mem [0:1][0:255];
  int unsigned rng, seed=1, transactions=200;
  integer product=0, errors=0, checks=0, completed=0;
  integer fast_hits=0, slow_hits=0, holes=0, unaligned=0, partial=0, reserved_hits=0;
  platform_apb_slice dut(.*);
  always #5 pclk=~pclk;
  function automatic logic [31:0] next_random();
    rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
    next_random=rng;
  endfunction
  task automatic check(input logic okay, input string message);
    checks++;
    if (okay !== 1'b1) begin errors++; $display("ERROR txn=%0d %s", completed,message); end
  endtask
  task automatic reset_all();
    @(negedge pclk); rst_n=0; psel=0; penable=0;
    repeat (2) @(negedge pclk);
    for(int b=0;b<2;b++) for(int w=0;w<256;w++) expected_mem[b][w]=0;
    rst_n=1;
    @(negedge pclk);
  endtask
  task automatic transfer(input logic [31:0] a, input logic write_op,
                          input logic [31:0] d, input logic [3:0] strobes);
    logic expect_error;
    integer bank, index, wait_cycles;
    bank=(a>=32'h10001000 && a<32'h10002000) ? 1 : 0;
    index=(a % 1024)/4;
    expect_error=(a<32'h10000000 || a>=32'h10002000 ||
                  a%4!=0 || (a%4096)>=2048 || (write_op && strobes!=4'hf));
    @(negedge pclk);
    psel=1; penable=0; paddr=a; pwrite=write_op; pwdata=d; pstrb=strobes;
    #1; check(!pready && !pslverr,"no setup completion");
    @(negedge pclk); penable=1; #1;
    wait_cycles=0;
    while (!pready && wait_cycles<8) begin
      @(negedge pclk); wait_cycles++; #1;
    end
    check(pready,"bounded completion");
    check(pslverr===expect_error,"response matches independent address policy");
    if (!expect_error) begin
      if (!write_op) check(prdata===expected_mem[bank][index],"independent memory scoreboard");
      check(wait_cycles==(((a%4096)>=1024)?1:0),"documented wait count");
      if (write_op) expected_mem[bank][index]=d;
      if ((a%4096)>=1024) slow_hits++; else fast_hits++;
    end else begin
      if (a<32'h10000000 || a>=32'h10002000) holes++;
      if(a%4!=0) unaligned++;
      if(write_op && strobes!=4'hf) partial++;
      if((a%4096)>=2048) reserved_hits++;
    end
    @(posedge pclk); #1; completed++;
    @(negedge pclk); psel=0; penable=0;
  endtask
  initial begin
    logic [31:0] r,a,d;
    logic [3:0] s;
    logic wr;
    if ($value$plusargs("SEED=%d",seed)) begin end
    if ($value$plusargs("PRODUCT=%d",product)) begin end
    rng=(seed==0)?32'h1:seed;
    reset_all();
    // Mandatory witnesses are separate from random traffic.
    transfer(32'h10000000,1,32'h12345678,4'hf);
    transfer(32'h10000400,0,0,4'hf); // alias read through slow region
    transfer(32'h10000000,1,32'hffffffff,4'h3); // reject, no side effect
    transfer(32'h10000000,0,0,4'hf);
    transfer(32'h10001000,0,0,4'hf);
    transfer(32'h20000000,0,0,4'hf);
    transfer(32'h10000001,0,0,4'hf);
    transfer(32'h10000800,1,32'hbad,4'hf);
    for (int n=0;n<200;n++) begin
      r=next_random(); d=next_random(); wr=r[0]; s=4'hf;
      a=32'h10000000+((r>>1)%2)*4096+((r>>2)%256)*4;
      case((r>>10)%6)
        0: a=a+1024;
        1: a=32'h20000000;
        2: a=a+1;
        3: begin wr=1; s=4'h5; end
        4: a=a+2048;
        default: ;
      endcase
      transfer(a,wr,d,s);
      if (n==99) begin reset_all(); transfer(32'h10000000,0,0,4'hf); end
    end
    check(fast_hits>0 && slow_hits>0 && holes>0 && unaligned>0 && partial>0 && reserved_hits>0,
          "all mandatory coarse campaign bins witnessed");
    $display("COUNTS fast=%0d slow=%0d hole=%0d unaligned=%0d partial=%0d reserved=%0d",fast_hits,slow_hits,holes,unaligned,partial,reserved_hits);
    if(errors==0) $display("TEST PASSED: PLATFORM_SLICE product=%0d seed=%0d transactions=%0d checks=%0d",product,seed,completed,checks);
    else begin $display("TEST FAILED: %0d errors",errors); $fatal(1); end
    $finish;
  end
  initial begin #100000; $fatal(1,"TIMEOUT"); end
endmodule
