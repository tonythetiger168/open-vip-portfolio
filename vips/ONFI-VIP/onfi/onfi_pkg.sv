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
//------------------------------------------------------------------------------
// ONFI (Open NAND Flash Interface) UVM VIP Package
//
// Deepened VIP: protocol-accurate driver (ONFI 1.0 command/address/data
// cycles with CE#/CLE/ALE/WE#/RE# handshake, tWB/tRC/tR/tPROG/tBERS timing),
// bus-decoding monitor, end-to-end expected/observed analysis ports, and a
// directed + regression sequence library.
//------------------------------------------------------------------------------
`ifndef ONFI_PKG_SV
`define ONFI_PKG_SV

package onfi_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"

  //============================================================================
  // ONFI Sequence Item
  //============================================================================
  class onfi_seq_item extends uvm_sequence_item;
    `uvm_object_utils(onfi_seq_item)

    typedef enum {
      READ_ID, READ_STATUS, READ_PAGE, READ_PAGE_CONFIRM,
      PROGRAM_PAGE, PROGRAM_CONFIRM, ERASE_BLOCK, ERASE_CONFIRM,
      RESET, READ_PARAMETER, SET_FEATURES, GET_FEATURES,
      READ_MULTI_PLANE, PROGRAM_MULTI_PLANE
    } cmd_type_e;

    rand cmd_type_e     cmd_type;
    rand bit [15:0]     addr;           // legacy column/row address field
    rand bit [7:0]      data;           // legacy single-byte data field
    rand bit [7:0]      feature_addr;   // SET/GET_FEATURES sub-address
    rand bit [7:0]      feature_val;    // SET_FEATURES value
    rand bit [15:0]     block_addr;     // target block (row address high)
    rand bit [15:0]     page_addr;      // target page  (row address low)
    rand bit [7:0]      data_payload[]; // page program payload
    rand int unsigned   num_bytes;      // bytes to program / read

    // response / observation fields (driven by driver/DUT, filled by monitor)
    bit [7:0]           status;         // status register readback
    bit [7:0]           read_data;      // last read byte (legacy)
    bit [7:0]           read_payload[]; // read data captured from the bus
    bit                 ready;          // R/B# observed ready at end of op
    bit                 expect_fail;    // error injection: op expected to fail

    // Constraints
    constraint c_addr_align { addr[3:0] == 4'b0000; }
    // REACHABILITY: READ_PARAMETER (0xEC) is a legal ONFI command handled by
    // both the driver and the DUT model; add it to the dist so the
    // onfi_cfg_cg read_param bin is generatable.
    constraint c_cmd_dist {
      cmd_type dist { READ_PAGE := 25, PROGRAM_PAGE := 25, READ_STATUS := 10,
                      ERASE_BLOCK := 10, RESET := 5, READ_ID := 5,
                      READ_PARAMETER := 5,
                      SET_FEATURES := 5, GET_FEATURES := 5,
                      READ_MULTI_PLANE := 5, PROGRAM_MULTI_PLANE := 5 };
    }
    constraint c_mem_range {
      block_addr inside {[0:63]};
      page_addr  inside {[0:63]};
    }
    constraint c_payload {
      num_bytes inside {[1:16]};
      data_payload.size() == num_bytes;
    }

    function new(string name = "onfi_seq_item");
      super.new(name);
    endfunction

    function void copy_from(onfi_seq_item rhs);
      cmd_type     = rhs.cmd_type;
      addr         = rhs.addr;
      data         = rhs.data;
      feature_addr = rhs.feature_addr;
      feature_val  = rhs.feature_val;
      block_addr   = rhs.block_addr;
      page_addr    = rhs.page_addr;
      num_bytes    = rhs.num_bytes;
      data_payload = new[rhs.data_payload.size()];
      foreach (rhs.data_payload[i]) data_payload[i] = rhs.data_payload[i];
      read_payload = new[rhs.read_payload.size()];
      foreach (rhs.read_payload[i]) read_payload[i] = rhs.read_payload[i];
      status       = rhs.status;
      read_data    = rhs.read_data;
      ready        = rhs.ready;
      expect_fail  = rhs.expect_fail;
    endfunction

    function string convert2string();
      return $sformatf("ONFI %s: blk=0x%0h page=0x%0h n=%0d data=0x%0h status=0x%0h",
                       cmd_type.name(), block_addr, page_addr, num_bytes, data, status);
    endfunction
  endclass : onfi_seq_item

  //============================================================================
  // ONFI Configuration
  //============================================================================
  class onfi_cfg extends uvm_object;
    `uvm_object_utils(onfi_cfg)

    uvm_active_passive_enum is_active = UVM_ACTIVE;
    bit has_coverage = 1;

    // ONFI timing parameters (in controller clock cycles)
    int tRead  = 25;    // tR    - page read array access
    int tProg  = 200;   // tPROG - page program time
    int tErase = 2000;  // tBERS - block erase time
    int tReset = 10;    // tRST  - device reset time
    int tWHR   = 60;    // tWHR  - WE# high to RE# low
    int tRR    = 20;    // tRR   - ready to RE# low
    int tWB    = 4;     // tWB   - WE# high to R/B# low
    int tRC    = 2;     // tRC   - RE# cycle time
    int tWC    = 2;     // tWC   - WE# cycle time
    int tADL   = 2;     // tADL  - ALE to data start

    // device geometry (must match DUT model)
    int num_blocks      = 64;
    int pages_per_block = 64;
    int page_size       = 256;

    function new(string name = "onfi_cfg");
      super.new(name);
    endfunction
  endclass : onfi_cfg

  //============================================================================
  // ONFI Sequencer
  //============================================================================
  class onfi_sequencer extends uvm_sequencer #(onfi_seq_item);
    `uvm_component_utils(onfi_sequencer)
    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction
  endclass : onfi_sequencer

  //============================================================================
  // ONFI Driver -- protocol-accurate bus cycles + expected-item publishing
  //============================================================================
  class onfi_driver extends uvm_driver #(onfi_seq_item);
    `uvm_component_utils(onfi_driver)

    virtual onfi_if vif;
    onfi_cfg cfg;
    uvm_analysis_port #(onfi_seq_item) drv_ap;  // expected items for scoreboard

    // driver-side mirror of the NAND array (erased = 0xFF)
    protected bit [7:0] mirror [longint unsigned];

    function new(string name, uvm_component parent);
      super.new(name, parent);
      drv_ap = new("drv_ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual onfi_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "ONFI virtual interface not found")
      if (!uvm_config_db#(onfi_cfg)::get(this, "", "cfg", cfg))
        cfg = onfi_cfg::type_id::create("cfg");
    endfunction

    // ---- low-level ONFI bus cycle helpers --------------------------------
    protected task bus_idle();
      vif.drv_cb.ce_n <= 1'b1;
      vif.drv_cb.cle  <= 1'b0;
      vif.drv_cb.ale  <= 1'b0;
      vif.drv_cb.we_n <= 1'b1;
      vif.drv_cb.re_n <= 1'b1;
      vif.drv_cb.wp_n <= 1'b1;
      vif.drv_cb.io   <= 8'hzz;
      @(vif.drv_cb);
    endtask

    // Command latch cycle: CE#=0 CLE=1, WE# pulse with command on IO
    protected task cmd_cycle(bit [7:0] cmd);
      vif.drv_cb.ce_n <= 1'b0;
      vif.drv_cb.cle  <= 1'b1;
      vif.drv_cb.ale  <= 1'b0;
      vif.drv_cb.io   <= cmd;
      @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b0;
      repeat (cfg.tWC) @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b1;
      @(vif.drv_cb);
      vif.drv_cb.cle  <= 1'b0;
    endtask

    // Address latch cycle: CE#=0 ALE=1, WE# pulse with address byte on IO
    protected task addr_cycle(bit [7:0] abyte);
      vif.drv_cb.ce_n <= 1'b0;
      vif.drv_cb.cle  <= 1'b0;
      vif.drv_cb.ale  <= 1'b1;
      vif.drv_cb.io   <= abyte;
      @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b0;
      repeat (cfg.tWC) @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b1;
      @(vif.drv_cb);
      vif.drv_cb.ale  <= 1'b0;
    endtask

    // Row address = {col(1B), page(1B), block(1B)}
    protected task row_addr_cycles(bit [15:0] blk, bit [15:0] pg);
      addr_cycle(8'h00);          // column address byte
      addr_cycle(pg[7:0]);        // page address byte
      addr_cycle(blk[7:0]);       // block address byte
    endtask

    // Data input cycle (host -> flash): WE# pulse, IO driven by host
    protected task data_in_cycle(bit [7:0] d);
      vif.drv_cb.ce_n <= 1'b0;
      vif.drv_cb.cle  <= 1'b0;
      vif.drv_cb.ale  <= 1'b0;
      vif.drv_cb.io   <= d;
      @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b0;
      repeat (cfg.tWC) @(vif.drv_cb);
      vif.drv_cb.we_n <= 1'b1;
      @(vif.drv_cb);
    endtask

    // Data output cycle (flash -> host): RE# pulse, IO sampled from flash
    protected task data_out_cycle(output bit [7:0] d);
      vif.drv_cb.ce_n <= 1'b0;
      vif.drv_cb.cle  <= 1'b0;
      vif.drv_cb.ale  <= 1'b0;
      vif.drv_cb.io   <= 8'hzz;   // host releases the bus
      @(vif.drv_cb);
      vif.drv_cb.re_n <= 1'b0;
      repeat (cfg.tRC) @(vif.drv_cb);
      d = vif.drv_cb.io;
      vif.drv_cb.re_n <= 1'b1;
      @(vif.drv_cb);
    endtask

    // Wait for R/B# ready (tWB then poll R/B# high)
    protected task wait_ready();
      repeat (cfg.tWB) @(vif.drv_cb);
      do @(vif.drv_cb); while (vif.drv_cb.rb_n !== 1'b1);
    endtask

    protected function longint unsigned mkey(bit [15:0] blk, bit [15:0] pg, int idx);
      return (longint'(blk) * cfg.pages_per_block * cfg.page_size)
           + (longint'(pg) * cfg.page_size) + idx;
    endfunction

    protected function bit [7:0] mirror_read(bit [15:0] blk, bit [15:0] pg, int idx);
      longint unsigned k = mkey(blk, pg, idx);
      if (mirror.exists(k)) return mirror[k];
      return 8'hFF;  // erased state
    endfunction

    // ---- top-level item execution -----------------------------------------
    task run_phase(uvm_phase phase);
      bus_idle();
      forever begin
        seq_item_port.get_next_item(req);
        drive_item(req);
        seq_item_port.item_done();
      end
    endtask

    protected task drive_item(onfi_seq_item item);
      onfi_seq_item exp;
      bit [7:0] rd;
      exp = onfi_seq_item::type_id::create("exp");
      exp.copy_from(item);

      case (item.cmd_type)
        onfi_seq_item::READ_ID: begin
          cmd_cycle(8'h90);
          addr_cycle(8'h00);
          repeat (cfg.tWHR) @(vif.drv_cb);
          exp.read_payload = new[5];
          for (int i = 0; i < 5; i++) begin
            data_out_cycle(rd);
            exp.read_payload[i] = rd;
          end
          exp.read_data = exp.read_payload[0];
          item.read_data = exp.read_data;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::READ_STATUS: begin
          cmd_cycle(8'h70);
          repeat (cfg.tRR) @(vif.drv_cb);
          data_out_cycle(rd);
          item.status = rd;
          exp.status  = rd;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::READ_PAGE, onfi_seq_item::READ_PAGE_CONFIRM, onfi_seq_item::READ_MULTI_PLANE: begin
          cmd_cycle(8'h00);
          row_addr_cycles(item.block_addr, item.page_addr);
          cmd_cycle(8'h30);          // read confirm
          wait_ready();              // tWB + tR (array -> page buffer)
          exp.read_payload = new[item.num_bytes];
          for (int i = 0; i < item.num_bytes; i++) begin
            data_out_cycle(rd);
            exp.read_payload[i] = rd;
          end
          exp.read_data = exp.read_payload[0];
          item.read_data = exp.read_data;
          item.ready = (vif.drv_cb.rb_n === 1'b1);
          exp.ready  = item.ready;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::PROGRAM_PAGE, onfi_seq_item::PROGRAM_CONFIRM, onfi_seq_item::PROGRAM_MULTI_PLANE: begin
          if (item.expect_fail) vif.drv_cb.wp_n <= 1'b0;  // WP# violation injection
          cmd_cycle(8'h80);
          row_addr_cycles(item.block_addr, item.page_addr);
          repeat (cfg.tADL) @(vif.drv_cb);
          for (int i = 0; i < item.data_payload.size(); i++)
            data_in_cycle(item.data_payload[i]);
          cmd_cycle(8'h10);          // program confirm
          wait_ready();              // tWB + tPROG
          // update mirror only if write is not protected
          if (!item.expect_fail) begin
            for (int i = 0; i < item.data_payload.size(); i++)
              mirror[mkey(item.block_addr, item.page_addr, i)] = item.data_payload[i];
          end
          item.ready = (vif.drv_cb.rb_n === 1'b1);
          exp.ready  = item.ready;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::ERASE_BLOCK, onfi_seq_item::ERASE_CONFIRM: begin
          cmd_cycle(8'h60);
          addr_cycle(item.page_addr[7:0]);
          addr_cycle(item.block_addr[7:0]);
          cmd_cycle(8'hD0);          // erase confirm
          wait_ready();              // tWB + tBERS
          if (!item.expect_fail) begin
            for (int p = 0; p < cfg.pages_per_block; p++)
              for (int i = 0; i < cfg.page_size; i++) begin
                longint unsigned k = mkey(item.block_addr, p[15:0], i);
                if (mirror.exists(k)) mirror.delete(k);  // back to 0xFF
              end
          end
          item.ready = (vif.drv_cb.rb_n === 1'b1);
          exp.ready  = item.ready;
          vif.drv_cb.wp_n <= 1'b1;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::RESET: begin
          cmd_cycle(8'hFF);
          repeat (cfg.tReset) @(vif.drv_cb);
          wait_ready();
          item.ready = (vif.drv_cb.rb_n === 1'b1);
          exp.ready  = item.ready;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::READ_PARAMETER: begin
          cmd_cycle(8'hEC);
          addr_cycle(8'h00);
          repeat (cfg.tWHR) @(vif.drv_cb);
          exp.read_payload = new[4];
          for (int i = 0; i < 4; i++) begin
            data_out_cycle(rd);
            exp.read_payload[i] = rd;
          end
          exp.read_data = exp.read_payload[0];
          item.read_data = exp.read_data;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::SET_FEATURES: begin
          cmd_cycle(8'hEF);
          addr_cycle(item.feature_addr);
          repeat (cfg.tADL) @(vif.drv_cb);
          data_in_cycle(item.feature_val);
          data_in_cycle(8'h00);
          data_in_cycle(8'h00);
          data_in_cycle(8'h00);
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        onfi_seq_item::GET_FEATURES: begin
          cmd_cycle(8'hEE);
          addr_cycle(item.feature_addr);
          repeat (cfg.tWHR) @(vif.drv_cb);
          exp.read_payload = new[4];
          for (int i = 0; i < 4; i++) begin
            data_out_cycle(rd);
            exp.read_payload[i] = rd;
          end
          exp.read_data = exp.read_payload[0];
          exp.feature_val = exp.read_payload[0];
          item.read_data = exp.read_data;
          vif.drv_cb.ce_n <= 1'b1;
          @(vif.drv_cb);
        end

        default: begin
          @(vif.drv_cb);
        end
      endcase

      // expected read data from the mirror model (end-to-end reference)
      if (item.cmd_type == onfi_seq_item::READ_PAGE || item.cmd_type == onfi_seq_item::READ_MULTI_PLANE) begin
        for (int i = 0; i < exp.read_payload.size(); i++)
          exp.read_payload[i] = mirror_read(item.block_addr, item.page_addr, i);
        exp.read_data = exp.read_payload[0];
      end
      drv_ap.write(exp);
    endtask
  endclass : onfi_driver

  //============================================================================
  // ONFI Monitor -- decodes transactions from bus waveforms
  //============================================================================
  class onfi_monitor extends uvm_monitor;
    `uvm_component_utils(onfi_monitor)

    virtual onfi_if vif;
    uvm_analysis_port #(onfi_seq_item) item_collected_port;

    typedef enum logic [3:0] {
      M_IDLE, M_CMD_SEEN, M_ADDR, M_DATA_IN, M_WAIT_CONFIRM,
      M_DATA_OUT, M_DONE
    } mon_state_e;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      item_collected_port = new("item_collected_port", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual onfi_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "ONFI virtual interface not found")
    endfunction

    task run_phase(uvm_phase phase);
      mon_state_e state = M_IDLE;
      onfi_seq_item item = null;
      bit [7:0]  pending_cmd = 8'h00;
      bit [7:0]  addr_bytes[$];
      bit [7:0]  dout_bytes[$];
      bit [7:0]  din_bytes[$];
      bit        prev_we_n = 1'b1;
      bit        prev_re_n = 1'b1;

      forever begin
        @(vif.mon_cb);

        if (vif.rst_n !== 1'b1) begin
          state = M_IDLE;
          item = null;
          addr_bytes.delete();
          dout_bytes.delete();
          din_bytes.delete();
          prev_we_n = 1'b1;
          prev_re_n = 1'b1;
          continue;
        end

        // NAND latches cmd/addr/data-in on the WE# rising edge
        if (!vif.mon_cb.ce_n && prev_we_n == 1'b0 && vif.mon_cb.we_n == 1'b1) begin
          if (vif.mon_cb.cle) begin
          bit [7:0] cmd = vif.mon_cb.io;
          // a new command while a read burst was open closes the read
          if (state == M_DATA_OUT && item != null) begin
            finish_obs(item, addr_bytes, dout_bytes);
            item_collected_port.write(item);
            item = null;
            dout_bytes.delete();
            addr_bytes.delete();
          end
          pending_cmd = cmd;
          case (cmd)
            8'h00: begin                       // page read setup
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::READ_PAGE;
              addr_bytes.delete();
              state = M_ADDR;
            end
            8'h30: begin                       // page read confirm
              if (item != null) state = M_DATA_OUT;
              dout_bytes.delete();
            end
            8'h80: begin                       // page program setup
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::PROGRAM_PAGE;
              addr_bytes.delete();
              din_bytes.delete();
              state = M_ADDR;
            end
            8'h10: begin                       // program confirm
              if (item != null) begin
                finish_pgm(item, addr_bytes, din_bytes);
                item_collected_port.write(item);
                item = null;
                addr_bytes.delete();
                din_bytes.delete();
              end
              state = M_IDLE;
            end
            8'h60: begin                       // block erase setup
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::ERASE_BLOCK;
              addr_bytes.delete();
              state = M_ADDR;
            end
            8'hD0: begin                       // erase confirm
              if (item != null) begin
                finish_erase(item, addr_bytes);
                item_collected_port.write(item);
                item = null;
                addr_bytes.delete();
              end
              state = M_IDLE;
            end
            8'hFF: begin                       // reset
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::RESET;
              item.ready = 1'b1;
              item_collected_port.write(item);
              item = null;
              state = M_IDLE;
            end
            8'h90: begin                       // read ID
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::READ_ID;
              addr_bytes.delete();
              dout_bytes.delete();
              state = M_ADDR;
            end
            8'h70: begin                       // read status
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::READ_STATUS;
              dout_bytes.delete();
              state = M_DATA_OUT;
            end
            8'hEC: begin                       // read parameter page
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::READ_PARAMETER;
              addr_bytes.delete();
              dout_bytes.delete();
              state = M_ADDR;
            end
            8'hEF: begin                       // set features
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::SET_FEATURES;
              addr_bytes.delete();
              din_bytes.delete();
              state = M_ADDR;
            end
            8'hEE: begin                       // get features
              item = onfi_seq_item::type_id::create("item");
              item.cmd_type = onfi_seq_item::GET_FEATURES;
              addr_bytes.delete();
              dout_bytes.delete();
              state = M_ADDR;
            end
            default: state = M_IDLE;
          endcase
          end
          // address latch (WE# rising edge, ALE high)
          else if (vif.mon_cb.ale) begin
            addr_bytes.push_back(vif.mon_cb.io);
            if (item != null && (item.cmd_type == onfi_seq_item::READ_ID ||
                                 item.cmd_type == onfi_seq_item::READ_PARAMETER ||
                                 item.cmd_type == onfi_seq_item::GET_FEATURES))
              state = M_DATA_OUT;
            else if (item != null && item.cmd_type == onfi_seq_item::SET_FEATURES)
              state = M_DATA_IN;
          end
          // data input, host -> flash (WE# rising edge, CLE/ALE low)
          else if (state == M_DATA_IN) begin
            din_bytes.push_back(vif.mon_cb.io);
          end
        end
        // data output, flash -> host: capture on RE# rising edge
        if (!vif.mon_cb.ce_n && prev_re_n == 1'b0 && vif.mon_cb.re_n == 1'b1 &&
            state == M_DATA_OUT) begin
          dout_bytes.push_back(vif.mon_cb.io);
        end
        // end of a read burst: CE# deasserts
        if (state == M_DATA_OUT && item != null && vif.mon_cb.ce_n &&
            dout_bytes.size() > 0) begin
          finish_obs(item, addr_bytes, dout_bytes);
          item_collected_port.write(item);
          item = null;
          dout_bytes.delete();
          addr_bytes.delete();
          state = M_IDLE;
        end
        // SET_FEATURES ends when CE# deasserts after data-in
        if (item != null && item.cmd_type == onfi_seq_item::SET_FEATURES &&
            vif.mon_cb.ce_n && din_bytes.size() > 0) begin
          finish_pgm(item, addr_bytes, din_bytes);
          item_collected_port.write(item);
          item = null;
          din_bytes.delete();
          addr_bytes.delete();
          state = M_IDLE;
        end
        prev_we_n = vif.mon_cb.we_n;
        prev_re_n = vif.mon_cb.re_n;
      end
    endtask

    protected function void finish_obs(onfi_seq_item it, ref bit [7:0] ab[$],
                                       ref bit [7:0] db[$]);
      if (ab.size() >= 3) begin
        it.page_addr  = {8'h00, ab[1]};
        it.block_addr = {8'h00, ab[2]};
      end
      it.read_payload = new[db.size()];
      foreach (db[i]) it.read_payload[i] = db[i];
      if (db.size() > 0) it.read_data = db[0];
      if (it.cmd_type == onfi_seq_item::READ_STATUS && db.size() > 0)
        it.status = db[0];
      it.num_bytes = db.size();
      it.ready = 1'b1;
    endfunction

    protected function void finish_pgm(onfi_seq_item it, ref bit [7:0] ab[$],
                                       ref bit [7:0] db[$]);
      if (ab.size() >= 3) begin
        it.page_addr  = {8'h00, ab[1]};
        it.block_addr = {8'h00, ab[2]};
      end
      if (ab.size() >= 1) it.feature_addr = ab[0];
      it.data_payload = new[db.size()];
      foreach (db[i]) it.data_payload[i] = db[i];
      if (db.size() > 0) begin
        it.data        = db[0];
        it.feature_val = db[0];
      end
      it.num_bytes = db.size();
      it.ready = 1'b1;
    endfunction

    protected function void finish_erase(onfi_seq_item it, ref bit [7:0] ab[$]);
      if (ab.size() >= 2) begin
        it.page_addr  = {8'h00, ab[0]};
        it.block_addr = {8'h00, ab[1]};
      end
      it.ready = 1'b1;
    endfunction
  endclass : onfi_monitor

  //============================================================================
  // ONFI Agent
  //============================================================================
  class onfi_agent extends uvm_agent;
    `uvm_component_utils(onfi_agent)

    onfi_sequencer sqr;
    onfi_driver    drv;
    onfi_monitor   mon;
    onfi_cfg       cfg;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(onfi_cfg)::get(this, "", "cfg", cfg))
        cfg = onfi_cfg::type_id::create("cfg");
      mon = onfi_monitor::type_id::create("mon", this);
      if (cfg.is_active == UVM_ACTIVE) begin
        sqr = onfi_sequencer::type_id::create("sqr", this);
        drv = onfi_driver::type_id::create("drv", this);
      end
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (cfg.is_active == UVM_ACTIVE)
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction
  endclass : onfi_agent

  //============================================================================
  // ONFI Sequences
  //============================================================================
  class onfi_base_seq extends uvm_sequence #(onfi_seq_item);
    `uvm_object_utils(onfi_base_seq)

    int num_blocks      = 64;
    int pages_per_block = 64;

    function new(string name = "onfi_base_seq");
      super.new(name);
    endfunction

    // helper: send one fully-specified item
    task send_item(onfi_seq_item item);
      start_item(item);
      finish_item(item);
    endtask

    // helper: build a directed item
    function onfi_seq_item mk_item(onfi_seq_item::cmd_type_e ct,
                                   bit [15:0] blk = 0, bit [15:0] pg = 0,
                                   int nbytes = 4);
      onfi_seq_item it = onfi_seq_item::type_id::create("it");
      it.cmd_type   = ct;
      it.block_addr = blk;
      it.page_addr  = pg;
      it.num_bytes  = nbytes;
      it.data_payload = new[nbytes];
      foreach (it.data_payload[i]) it.data_payload[i] = $urandom_range(0, 255);
      return it;
    endfunction
  endclass : onfi_base_seq

  // ---- 1. random read/program mix (normal traffic) ------------------------
  class onfi_rw_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_rw_seq)
    int num_trans = 20;

    function new(string name = "onfi_rw_seq");
      super.new(name);
    endfunction

    task body();
      onfi_seq_item it;
      repeat (num_trans) begin
        it = onfi_seq_item::type_id::create("it");
        if (!it.randomize() with {
              cmd_type inside {READ_PAGE, PROGRAM_PAGE, READ_STATUS, ERASE_BLOCK};
              block_addr inside {[0:num_blocks-1]};
              page_addr  inside {[0:pages_per_block-1]};
              num_bytes  inside {[1:8]};
            }) `uvm_error(get_type_name(), "onfi_rw_seq randomize failed")
        send_item(it);
      end
    endtask
  endclass : onfi_rw_seq

  // ---- 2. directed page program + readback (normal) ------------------------
  class onfi_program_read_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_program_read_seq)
    bit [15:0] block = 3;
    bit [15:0] page  = 5;
    int        len   = 8;

    function new(string name = "onfi_program_read_seq");
      super.new(name);
    endfunction

    task body();
      onfi_seq_item it;
      it = mk_item(onfi_seq_item::ERASE_BLOCK, block, 0, 0);
      send_item(it);
      it = mk_item(onfi_seq_item::PROGRAM_PAGE, block, page, len);
      foreach (it.data_payload[i]) it.data_payload[i] = 8'hA0 + i;
      send_item(it);
      it = mk_item(onfi_seq_item::READ_STATUS);
      send_item(it);
      it = mk_item(onfi_seq_item::READ_PAGE, block, page, len);
      send_item(it);
    endtask
  endclass : onfi_program_read_seq

  // ---- 3. erase + erased-state verify -------------------------------------
  class onfi_erase_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_erase_seq)
    bit [15:0] block = 7;

    function new(string name = "onfi_erase_seq");
      super.new(name);
    endfunction

    task body();
      send_item(mk_item(onfi_seq_item::PROGRAM_PAGE, block, 0, 8));
      send_item(mk_item(onfi_seq_item::ERASE_BLOCK, block, 0, 0));
      send_item(mk_item(onfi_seq_item::READ_STATUS));
      send_item(mk_item(onfi_seq_item::READ_PAGE, block, 0, 8));  // expect 0xFF
    endtask
  endclass : onfi_erase_seq

  // ---- 4. reset sequence (reset between and during ops) --------------------
  class onfi_reset_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_reset_seq)

    function new(string name = "onfi_reset_seq");
      super.new(name);
    endfunction

    task body();
      send_item(mk_item(onfi_seq_item::PROGRAM_PAGE, 1, 1, 4));
      send_item(mk_item(onfi_seq_item::RESET));
      send_item(mk_item(onfi_seq_item::READ_STATUS));
      send_item(mk_item(onfi_seq_item::READ_ID));
      send_item(mk_item(onfi_seq_item::PROGRAM_PAGE, 1, 2, 4));
      send_item(mk_item(onfi_seq_item::READ_PAGE, 1, 2, 4));
    endtask
  endclass : onfi_reset_seq

  // ---- 5. error sequence (write-protect violation + status check) ----------
  class onfi_error_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_error_seq)

    function new(string name = "onfi_error_seq");
      super.new(name);
    endfunction

    task body();
      onfi_seq_item it;
      // program with WP# asserted -> NAND must flag FAIL in status
      it = mk_item(onfi_seq_item::PROGRAM_PAGE, 2, 0, 4);
      it.expect_fail = 1'b1;
      send_item(it);
      send_item(mk_item(onfi_seq_item::READ_STATUS));
      // erase with WP# asserted
      it = mk_item(onfi_seq_item::ERASE_BLOCK, 2, 0, 0);
      it.expect_fail = 1'b1;
      send_item(it);
      send_item(mk_item(onfi_seq_item::READ_STATUS));
    endtask
  endclass : onfi_error_seq

  // ---- 6. back-to-back sequence (no idle gap between ops) ------------------
  class onfi_b2b_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_b2b_seq)
    int num_trans = 8;

    function new(string name = "onfi_b2b_seq");
      super.new(name);
    endfunction

    task body();
      for (int i = 0; i < num_trans; i++) begin
        send_item(mk_item(onfi_seq_item::PROGRAM_PAGE, 4, i[15:0], 4));
        send_item(mk_item(onfi_seq_item::READ_PAGE, 4, i[15:0], 4));
      end
    endtask
  endclass : onfi_b2b_seq

  // ---- 7. stress sequence (heavy random traffic) ---------------------------
  class onfi_stress_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_stress_seq)
    int num_trans = 64;

    function new(string name = "onfi_stress_seq");
      super.new(name);
    endfunction

    task body();
      onfi_rw_seq rw = onfi_rw_seq::type_id::create("rw");
      rw.num_trans = num_trans;
      rw.start(m_sequencer, null);
    endtask
  endclass : onfi_stress_seq

  // ---- 8. corner sequence (first/last block/page, extreme data) ------------
  class onfi_corner_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_corner_seq)

    function new(string name = "onfi_corner_seq");
      super.new(name);
    endfunction

    task body();
      onfi_seq_item it;
      bit [15:0] blks[$] = '{16'd0, 16'd63};
      bit [15:0] pgs[$]  = '{16'd0, 16'd63};
      foreach (blks[b]) begin
        foreach (pgs[p]) begin
          it = mk_item(onfi_seq_item::PROGRAM_PAGE, blks[b], pgs[p], 4);
          it.data_payload = '{8'h00, 8'hFF, 8'hA5, 8'h5A};
          send_item(it);
          send_item(mk_item(onfi_seq_item::READ_PAGE, blks[b], pgs[p], 4));
        end
        send_item(mk_item(onfi_seq_item::ERASE_BLOCK, blks[b], 0, 0));
      end
      // feature corner: SET then GET same feature address
      it = mk_item(onfi_seq_item::SET_FEATURES);
      it.feature_addr = 8'h01;
      it.feature_val  = 8'h55;
      send_item(it);
      it = mk_item(onfi_seq_item::GET_FEATURES);
      it.feature_addr = 8'h01;
      send_item(it);
    endtask
  endclass : onfi_corner_seq

  // ---- 9. coverage sequence: hit every command type ------------------------
  class onfi_cov_cmd_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_cov_cmd_seq)

    function new(string name = "onfi_cov_cmd_seq");
      super.new(name);
    endfunction

    task body();
      send_item(mk_item(onfi_seq_item::READ_ID));
      send_item(mk_item(onfi_seq_item::READ_STATUS));
      send_item(mk_item(onfi_seq_item::PROGRAM_PAGE, 0, 0, 4));
      send_item(mk_item(onfi_seq_item::READ_PAGE, 0, 0, 4));
      send_item(mk_item(onfi_seq_item::ERASE_BLOCK, 0, 0, 0));
      send_item(mk_item(onfi_seq_item::RESET));
      send_item(mk_item(onfi_seq_item::READ_PARAMETER));
      send_item(mk_item(onfi_seq_item::SET_FEATURES));
      send_item(mk_item(onfi_seq_item::GET_FEATURES));
      send_item(mk_item(onfi_seq_item::PROGRAM_MULTI_PLANE, 1, 0, 4));
      send_item(mk_item(onfi_seq_item::READ_MULTI_PLANE, 1, 0, 4));
    endtask
  endclass : onfi_cov_cmd_seq

  // ---- 10. regression mix: randomly weave all directed sequences -----------
  class onfi_regression_seq extends onfi_base_seq;
    `uvm_object_utils(onfi_regression_seq)
    int num_iters = 4;

    function new(string name = "onfi_regression_seq");
      super.new(name);
    endfunction

    task body();
      for (int i = 0; i < num_iters; i++) begin
        int pick = $urandom_range(0, 7);
        case (pick)
          0: begin onfi_program_read_seq s = onfi_program_read_seq::type_id::create("s"); s.start(m_sequencer, null); end
          1: begin onfi_erase_seq        s = onfi_erase_seq::type_id::create("s");        s.start(m_sequencer, null); end
          2: begin onfi_reset_seq        s = onfi_reset_seq::type_id::create("s");        s.start(m_sequencer, null); end
          3: begin onfi_error_seq        s = onfi_error_seq::type_id::create("s");        s.start(m_sequencer, null); end
          4: begin onfi_b2b_seq          s = onfi_b2b_seq::type_id::create("s");          s.start(m_sequencer, null); end
          5: begin onfi_stress_seq       s = onfi_stress_seq::type_id::create("s");       s.num_trans = 16; s.start(m_sequencer, null); end
          6: begin onfi_corner_seq       s = onfi_corner_seq::type_id::create("s");       s.start(m_sequencer, null); end
          7: begin onfi_cov_cmd_seq      s = onfi_cov_cmd_seq::type_id::create("s");      s.start(m_sequencer, null); end
        endcase
      end
    endtask
  endclass : onfi_regression_seq

endpackage : onfi_pkg

`endif // ONFI_PKG_SV
