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
//  MIPI Top-Level Testbench
//  Closed loop: mipi_driver (CSE) <-> mipi_dut (CSE command processor)
//  <-> mipi_monitor, plus the tiered SVA compliance checker.
//============================================================================
`ifndef TOP_TB_SV
`define TOP_TB_SV

`include "uvm_macros.svh"
import uvm_pkg::*;
import mipi_vip_pkg::*;

//----------------------------------------------------------------------------
// CSE command-processor DUT model
//   - generic lanes: ready/hs_rdy echo (original behavior)
//   - CSE lane: valid/ready command accept, 4-cycle processing, response
//     byte driven on cse_data while cse_irq is asserted (4 cycles)
//   - register file (16x8), memory (16x8), config register, sticky ERR
//----------------------------------------------------------------------------
module mipi_dut(mipi_vip_if vif);

  localparam logic [7:0] RESP_ERR = 8'hEE;
  localparam logic [7:0] RESP_RST = 8'hA5;

  typedef enum logic [1:0] {CSE_IDLE, CSE_BUSY, CSE_RESP} cse_state_e;

  cse_state_e cse_state = CSE_IDLE;
  logic [7:0] regfile [16];
  logic [7:0] mem     [16];
  logic [7:0] cfg_reg = 8'h00;
  logic       err_sticky = 1'b0;
  logic [3:0] cur_cmd;
  logic [7:0] cur_op;
  logic [7:0] resp_byte = 8'h00;
  int         busy_cnt = 0;
  int         resp_cnt = 0;

  // CSE target drives cse_data only during the response window
  assign vif.cse_data = (cse_state == CSE_RESP) ? resp_byte : 8'hzz;
  assign vif.cse_irq  = (cse_state == CSE_RESP);

  function automatic logic [7:0] compute_resp(logic [3:0] cmd, logic [7:0] op);
    case (cmd)
      4'd0: return 8'h00;                                   // NOP
      4'd1: return regfile[op[7:4]];                        // RD_REG
      4'd2: return {4'h0, op[3:0]};                         // WR_REG (echo)
      4'd3: return mem[op[7:4]];                            // RD_MEM
      4'd4: return {4'h0, op[3:0]};                         // WR_MEM (echo)
      4'd5: return {6'h00, err_sticky, 1'b1};               // GET_STATUS
      4'd6: return RESP_RST;                                // SOFT_RESET
      4'd7: return 8'h00;                                   // IRQ_ACK
      4'd8: return op;                                      // SET_CFG (echo)
      4'd9: return cfg_reg;                                 // GET_CFG
      default: return RESP_ERR;                             // reserved
    endcase
  endfunction

  always_ff @(posedge vif.clk or negedge vif.rst_n) begin
    if (!vif.rst_n) begin
      vif.ready         <= 1'b0;
      vif.dphy_hs_rdy   <= 1'b0;
      vif.mphy_ready    <= 1'b0;
      vif.unipro_ready  <= 1'b0;
      vif.hsi_ready     <= 1'b0;
      vif.cse_ready     <= 1'b0;
      cse_state         <= CSE_IDLE;
      busy_cnt          <= 0;
      resp_cnt          <= 0;
      resp_byte         <= 8'h00;
      cur_cmd           <= 4'h0;
      cur_op            <= 8'h00;
      cfg_reg           <= 8'h00;
      err_sticky        <= 1'b0;
      foreach (regfile[i]) regfile[i] <= 8'h00;
      foreach (mem[i])     mem[i]     <= 8'h00;
    end
    else begin
      // generic lane ready echo (original behavior)
      vif.ready         <= vif.valid;
      vif.dphy_hs_rdy   <= vif.dphy_hs_rqst;
      vif.mphy_ready    <= vif.mphy_hs_mode;
      vif.unipro_ready  <= vif.unipro_valid;
      vif.hsi_ready     <= vif.hsi_valid;

      // CSE command processor
      case (cse_state)
        CSE_IDLE: begin
          vif.cse_ready <= 1'b1;
          if (vif.cse_valid && vif.cse_ready) begin
            cur_cmd    <= vif.cse_cmd;
            cur_op     <= vif.cse_data;
            resp_byte  <= compute_resp(vif.cse_cmd, vif.cse_data);
            busy_cnt   <= 4;
            cse_state  <= CSE_BUSY;
            vif.cse_ready <= 1'b0;
            // side effects
            case (vif.cse_cmd)
              4'd2: regfile[vif.cse_data[7:4]] <= {4'h0, vif.cse_data[3:0]};
              4'd4: mem[vif.cse_data[7:4]]     <= {4'h0, vif.cse_data[3:0]};
              4'd6: begin
                foreach (regfile[i]) regfile[i] <= 8'h00;
                foreach (mem[i])     mem[i]     <= 8'h00;
                cfg_reg    <= 8'h00;
                err_sticky <= 1'b0;
              end
              4'd8: cfg_reg <= vif.cse_data;
              default: ;
            endcase
            if (vif.cse_cmd > 4'd9) err_sticky <= 1'b1;
          end
        end
        CSE_BUSY: begin
          vif.cse_ready <= 1'b0;
          if (busy_cnt > 0) busy_cnt <= busy_cnt - 1;
          else begin
            resp_cnt  <= 4;
            cse_state <= CSE_RESP;
          end
        end
        CSE_RESP: begin
          vif.cse_ready <= 1'b0;
          if (resp_cnt > 0) resp_cnt <= resp_cnt - 1;
          else cse_state <= CSE_IDLE;
        end
        default: cse_state <= CSE_IDLE;
      endcase
    end
  end
endmodule

//----------------------------------------------------------------------------
// Top-level testbench
//----------------------------------------------------------------------------
module top_tb;
  logic clk = 0, rst_n;

  always #2ns clk = ~clk;
  initial begin
    rst_n = 0;
    #100ns;
    rst_n = 1;
  end

  mipi_vip_if #(.DATA_WIDTH(32), .LANE_COUNT(4)) vif(clk, rst_n);

  mipi_dut dut(.vif(vif));

  // tiered SVA compliance checker bound to the CSE channel
  cse_compliance_checker cse_sva (
    .clk       (vif.clk),
    .rst_n     (vif.rst_n),
    .cse_data  (vif.cse_data),
    .cse_valid (vif.cse_valid),
    .cse_ready (vif.cse_ready),
    .cse_cmd   (vif.cse_cmd),
    .cse_irq   (vif.cse_irq)
  );

  initial begin
    uvm_config_db#(virtual mipi_vip_if)::set(null, "*", "vif", vif);
    run_test();
  end

  initial begin
    $dumpfile("mipi_uvm_vip.vcd");
    $dumpvars(0, top_tb);
  end

  initial begin
    #1000000;
    `uvm_fatal("TOP_TB", "Timeout!")
  end
endmodule

`endif // TOP_TB_SV
