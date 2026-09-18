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
// AMBA Testbench -- top with a functional AXI4 slave DUT model (memory)
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
  axi_compliance_checker_sva u_axi_sva_chk (.vif(vif));

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
// Functional AXI4 slave: single-outstanding memory model.
//   - AW/W/AR always ready; B and R channels generated per burst
//   - SLVERR (2'b10) for the error region addr[31:24] == 8'hEE
//   - 4 KiB word-addressed data memory (WSTRB byte enables)
//----------------------------------------------------------------------------
module amba_dut(amba_vip_if vif);

  logic [63:0] mem [0:511];
  initial for (int i = 0; i < 512; i++) mem[i] = 64'h0;

  // -------- write channel state --------
  logic [31:0] wr_addr;
  logic [7:0]  wr_len;
  logic [1:0]  wr_burst;
  logic        wr_active;
  logic        wr_error;
  logic [7:0]  wr_beat;

  wire wr_error_region = (vif.awaddr[31:24] == 8'hEE);

  // -------- read channel state --------
  logic [31:0] rd_addr;
  logic [7:0]  rd_len;
  logic [1:0]  rd_burst;
  logic        rd_active;
  logic        rd_error;
  logic [7:0]  rd_beat;

  wire rd_error_region = (vif.araddr[31:24] == 8'hEE);

  function automatic logic [31:0] next_addr(logic [31:0] a, logic [1:0] b,
                                            logic [7:0] len, logic [31:0] base);
    if (b == 2'b10) begin                 // WRAP
      int unsigned wrap_bytes = (int'(len) + 1) * 8;
      logic [31:0] wbase = base - (base % wrap_bytes);
      return wbase + ((a + 8) % wrap_bytes);
    end
    else if (b == 2'b00) return a;        // FIXED
    else return a + 8;                    // INCR
  endfunction

  assign vif.awready = 1'b1;
  assign vif.wready  = wr_active;
  assign vif.arready = !rd_active;

  always_ff @(posedge vif.aclk or negedge vif.aresetn) begin
    if (!vif.aresetn) begin
      vif.bvalid <= 1'b0;
      vif.bresp  <= 2'b00;
      wr_active  <= 1'b0;
      wr_error   <= 1'b0;
      wr_addr    <= 32'h0;
      wr_len     <= 8'h0;
      wr_burst   <= 2'b01;
      wr_beat    <= 8'h0;
    end
    else begin
      // AW accept
      if (vif.awvalid && vif.awready) begin
        wr_active <= 1'b1;
        wr_error  <= wr_error_region;
        wr_addr   <= vif.awaddr;
        wr_len    <= vif.awlen;
        wr_burst  <= vif.awburst;
        wr_beat   <= 8'h0;
      end
      // W accept
      if (vif.wvalid && vif.wready) begin
        if (!wr_error)
          for (int b = 0; b < 8; b++)
            if (vif.wstrb[b]) mem[wr_addr[11:3]][b*8 +: 8] <= vif.wdata[b*8 +: 8];
        wr_addr <= next_addr(wr_addr, wr_burst, wr_len, wr_addr);
        wr_beat <= wr_beat + 8'h1;
        if (vif.wlast) begin
          wr_active <= 1'b0;
          vif.bvalid <= 1'b1;
          vif.bresp  <= wr_error ? 2'b10 : 2'b00;
        end
      end
      // B accept
      if (vif.bvalid && vif.bready) begin
        vif.bvalid <= 1'b0;
      end
    end
  end

  // -------- read channel --------
  assign vif.rvalid = rd_active;
  assign vif.rdata  = rd_error ? 64'h0 : mem[rd_addr[11:3]];
  assign vif.rresp  = rd_error ? 2'b10 : 2'b00;
  assign vif.rlast  = rd_active && (rd_beat == rd_len);

  always_ff @(posedge vif.aclk or negedge vif.aresetn) begin
    if (!vif.aresetn) begin
      rd_active <= 1'b0;
      rd_error  <= 1'b0;
      rd_addr   <= 32'h0;
      rd_len    <= 8'h0;
      rd_burst  <= 2'b01;
      rd_beat   <= 8'h0;
    end
    else begin
      // AR accept
      if (vif.arvalid && vif.arready) begin
        rd_active <= 1'b1;
        rd_error  <= rd_error_region;
        rd_addr   <= vif.araddr;
        rd_len    <= vif.arlen;
        rd_burst  <= vif.arburst;
        rd_beat   <= 8'h0;
      end
      // R beat accept
      if (vif.rvalid && vif.rready) begin
        if (vif.rlast) rd_active <= 1'b0;
        else begin
          rd_addr <= next_addr(rd_addr, rd_burst, rd_len, rd_addr);
          rd_beat <= rd_beat + 8'h1;
        end
      end
    end
  end

  // Tie off unused protocol outputs (AHB/APB/stream) so no X propagates
  initial begin
    vif.tready = 1'b0;
    vif.hreadyout = 1'b0; vif.hrdata = 64'h0; vif.hresp = 1'b0;
    vif.pready = 1'b0; vif.prdata = 32'h0; vif.pslverr = 1'b0;
  end
endmodule
`endif
