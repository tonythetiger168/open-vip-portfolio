// SPDX-License-Identifier: Apache-2.0
interface platform_apb_if(input logic pclk);
  logic rst_n=0, psel=0, penable=0, pwrite=0;
  logic [31:0] paddr=0, pwdata=0, prdata;
  logic [3:0] pstrb=4'hf;
  logic [2:0] pprot=0;
  logic pready, pslverr;
  logic [1:0] irq;
endinterface
