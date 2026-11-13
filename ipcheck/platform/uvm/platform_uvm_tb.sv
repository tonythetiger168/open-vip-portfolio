// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module platform_uvm_tb;
  import uvm_pkg::*;
  import platform_apb_pkg::*;
  logic pclk=0;
  always #5 pclk=~pclk;
  platform_apb_if bus(pclk);
  platform_apb_slice dut(.pclk(pclk),.rst_n(bus.rst_n),.psel(bus.psel),.penable(bus.penable),
    .pwrite(bus.pwrite),.paddr(bus.paddr),.pwdata(bus.pwdata),.pstrb(bus.pstrb),.pprot(bus.pprot),
    .prdata(bus.prdata),.pready(bus.pready),.pslverr(bus.pslverr),.irq(bus.irq));
  initial begin repeat(3) @(negedge pclk); bus.rst_n=1; end
  initial begin
    uvm_config_db#(virtual platform_apb_if)::set(null,"*","vif",bus);
    run_test("platform_apb_test");
  end
  initial begin #200000; $fatal(1,"TIMEOUT"); end
endmodule
