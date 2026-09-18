// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//============================================================================
// AMBA Testbench -- top with a functional APB4 slave DUT model (register bank)
//============================================================================
`ifndef AMBA_TB_SV
`define AMBA_TB_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import amba_vip_pkg::*;

module top_tb;
  logic aclk = 0, aresetn;
  always #5ns aclk = ~aclk;

  initial begin
    aresetn = 0;
    #100ns;
    aresetn = 1;
  end

  amba_vip_if vif(aclk, aresetn);
  amba_dut dut(.vif(vif));

  // Tiered SVA compliance checker (module form)
  apb_compliance_checker_sva u_apb_sva_chk (.vif(vif));

  // Protocol checkers (module form)
  ahb_protocol_checker_sva u_ahb_proto_sva (.vif(vif));
  apb_protocol_checker_sva u_apb_proto_sva (.vif(vif));
  axi_protocol_checker_sva u_axi_proto_sva (.vif(vif));

  initial begin
    uvm_config_db#(virtual amba_vip_if)::set(null, "*", "vif", vif);
    run_test();
  end
endmodule

//----------------------------------------------------------------------------
// Functional APB4 slave: 64 x 32-bit register bank.
//   - zero wait-state for normal registers (PREADY combinational)
//   - 2 wait states for addresses with paddr[7:4] == 4'hF
//   - PSLVERR for the error region paddr[31:24] == 8'hEE
//   - PSTRB byte-enable write masking
//----------------------------------------------------------------------------
module amba_dut(amba_vip_if vif);

  logic [31:0] regbank [0:63];
  logic [1:0]  wait_cnt;

  initial for (int i = 0; i < 64; i++) regbank[i] = 32'h0;

  wire       access      = vif.psel && vif.penable;
  wire       wait_region = (vif.paddr[7:4] == 4'hF);
  wire       error_region = (vif.paddr[31:24] == 8'hEE);
  wire [5:0] reg_idx     = vif.paddr[7:2];

  // PREADY: immediate for normal region, 2 wait states for wait region
  assign vif.pready  = access ? (wait_region ? (wait_cnt >= 2) : 1'b1) : 1'b0;
  // PRDATA / PSLVERR are valid during the access phase
  assign vif.prdata  = access ? regbank[reg_idx] : 32'h0;
  assign vif.pslverr = access && error_region;

  always_ff @(posedge vif.aclk or negedge vif.aresetn) begin
    if (!vif.aresetn) begin
      wait_cnt <= 2'd0;
    end
    else begin
      // wait-state counter for the wait region
      if (!access)      wait_cnt <= 2'd0;
      else if (wait_cnt < 2'd2) wait_cnt <= wait_cnt + 2'd1;
      // register write with byte enables
      if (access && vif.pready && vif.pwrite && !error_region) begin
        for (int b = 0; b < 4; b++)
          if (vif.pstrb[b])
            regbank[reg_idx][b*8 +: 8] <= vif.pwdata[b*8 +: 8];
      end
    end
  end

  // Tie off unused protocol outputs (AXI/AHB) so no X propagates
  initial begin
    vif.awready = 1'b0; vif.wready = 1'b0; vif.bvalid = 1'b0; vif.bresp = 2'b00;
    vif.arready = 1'b0; vif.rvalid = 1'b0; vif.rdata = 64'h0;
    vif.rresp = 2'b00;  vif.rlast = 1'b0;  vif.tready = 1'b0;
    vif.hreadyout = 1'b0; vif.hrdata = 64'h0; vif.hresp = 1'b0;
  end
endmodule
`endif
