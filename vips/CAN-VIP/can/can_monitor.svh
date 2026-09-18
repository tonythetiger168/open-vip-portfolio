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
// can_monitor.svh -- CAN monitor: decodes frames bit-by-bit from the
// can_tx waveform (SOF/arbitration/control/data/CRC/ACK/EOF), removes
// stuff bits, verifies CRC-15, and publishes reconstructed transactions.

class can_monitor extends uvm_monitor;
  `uvm_component_utils(can_monitor)
  virtual can_if vif;
  uvm_analysis_port #(can_transaction) ap;
  can_config cfg;
  int unsigned txn_count = 0;

  localparam int BIT_CLKS = 8;   // must match transmitter bit timing

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual can_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "CAN virtual interface not found")
    if (!uvm_config_db#(can_config)::get(this, "", "cfg", cfg))
      cfg = can_config::type_id::create("cfg");
  endfunction

  // sample one bit at the bit center; caller aligns the first sample
  task sample_bit(output bit b);
    repeat (BIT_CLKS/2) @(posedge vif.clk);
    b = vif.can_tx;
    repeat (BIT_CLKS - BIT_CLKS/2) @(posedge vif.clk);
  endtask

  // receive a destuffed frame body; sets err on stuff/CRC/form errors
  task decode_frame(output can_transaction tx, output bit is_error);
    bit raw[$];
    bit b, last;
    int run;
    int nbytes;
    bit [14:0] crc_calc, crc_rx;

    is_error = 0;
    run = 1;
    // destuffed receive: after 5 equal bits, drop the following stuff bit
    forever begin
      sample_bit(b);
      if (run == 5 && b != last) begin
        run = 1;                       // stuff bit: skip it, keep counting
        sample_bit(b);
        if (b == last) begin
          // 6 equal bits in a row -> error/overload flag on the bus
          is_error = 1;
          return;
        end
      end
      raw.push_back(b);
      if (b == last) run++; else begin last = b; run = 1; end
      // stop condition: CRC delimiter is the first recessive bit after
      // the fixed-length header+data+CRC; we detect frame end by counting
      if (frame_complete(raw)) break;
    end

    tx = can_transaction::type_id::create("tx");
    parse(raw, tx, crc_calc, crc_rx);
    tx.with_error = (crc_calc != crc_rx);
    tx.crc_error  = (crc_calc != crc_rx);
  endtask

  // Determine when SOF..CRC fields are complete (CRC delim boundary)
  function bit frame_complete(const ref bit raw[$]);
    int idx;
    int dlc;
    int need;
    int nbytes;
    if (raw.size() < 15) return 0;
    idx = 1;                                       // skip SOF
    if (raw.size() < idx + 12) return 0;
    // std: 11 ID + RTR + IDE ; ext: 11 + SRR + IDE + 18 + RTR + r1
    if (raw[idx+12] == 1'b0) begin                 // IDE=0 -> standard
      idx += 12 + 1;                               // ID+RTR, IDE
    end else begin
      idx += 12 + 1 + 18 + 1 + 1;                  // +ext id, rtr, r1
      if (raw.size() < idx) return 0;
    end
    // control: fdf? (EDL) -- check position; conservative: assume classic
    if (raw.size() < idx + 1 + 4) return 0;
    // peek EDL for FD
    begin
      bit fdf;
      int cidx;
      fdf = raw[idx];
      if (fdf) begin cidx = idx + 4; end           // EDL,r0,BRS,ESI
      else     begin cidx = idx + 1; end           // r0
      if (raw.size() < cidx + 4) return 0;
      dlc = {raw[cidx], raw[cidx+1], raw[cidx+2], raw[cidx+3]};
      nbytes = (dlc > 8) ? 8 : dlc;
      // rtr=1 (remote): no data bytes
      need = cidx + 4 + nbytes*8 + 15;
      return (raw.size() >= need);
    end
  endfunction

  // parse destuffed bits into a transaction
  function void parse(const ref bit raw[$], can_transaction tx,
                      output bit [14:0] crc_calc, output bit [14:0] crc_rx);
    int idx = 1;
    bit rtr_local;
    int dlc, nbytes;
    tx.id = '0;
    for (int i = 10; i >= 0; i--) begin tx.id[i] = raw[idx]; idx++; end
    rtr_local = raw[idx]; idx++;
    tx.ide = raw[idx]; idx++;
    if (tx.ide) begin
      tx.id = {18'b0, tx.id[10:0]};
      idx++;                                        // SRR already in id stream
      // re-parse: ext layout = baseID,SRR,IDE,extID,RTR,r1
      // (handled below by shifting)
    end
    // NOTE: ext-frame layout re-walk
    if (tx.ide) begin
      int j = 1;
      bit [28:0] eid = '0;
      for (int i = 28; i >= 18; i--) begin eid[i] = raw[j]; j++; end
      j++;                                          // SRR
      j++;                                          // IDE
      for (int i = 17; i >= 0; i--) begin eid[i] = raw[j]; j++; end
      tx.id = eid;
      rtr_local = raw[j]; j++;
      j++;                                          // r1
      idx = j;
    end
    tx.rtr = rtr_local;
    tx.fdf = raw[idx];
    if (tx.fdf) begin
      idx++;                                        // EDL
      idx++;                                        // r0
      tx.brs = raw[idx]; idx++;
      tx.esi = raw[idx]; idx++;
    end else begin
      tx.fdf = 1'b0; tx.brs = 1'b0; tx.esi = 1'b0;
      idx++;                                        // r0
    end
    dlc = {raw[idx], raw[idx+1], raw[idx+2], raw[idx+3]}; idx += 4;
    tx.dlc = dlc;
    nbytes = (dlc > 8) ? 8 : dlc;
    tx.data_len = nbytes;
    tx.data = '0;
    if (!tx.rtr) begin
      for (int b = 0; b < nbytes; b++)
        for (int i = 7; i >= 0; i--) begin tx.data[b*8+i] = raw[idx]; idx++; end
    end
    crc_rx = '0;
    for (int i = 14; i >= 0; i--) begin crc_rx[i] = raw[idx]; idx++; end
    begin
      bit body[$];
      for (int k = 0; k < idx-15; k++) body.push_back(raw[k]);
      crc_calc = can_crc15(body);
    end
    tx.crc = crc_rx;
    tx.can_type = tx.fdf ? can_transaction::CAN_FD : can_transaction::CAN_2_0;
    tx.frame_type = tx.rtr ? can_transaction::REMOTE_FRAME : can_transaction::DATA_FRAME;
  endfunction

  task run_phase(uvm_phase phase);
    can_transaction tx;
    bit is_error;
    forever begin
      @(posedge vif.clk);
      if (!vif.rst_n) continue;
      // idle bus is recessive; a dominant bit outside a frame = SOF
      if (vif.can_tx === 1'b0) begin
        // align: we are 1 clk into the SOF bit; back off to bit center
        decode_frame(tx, is_error);
        if (is_error) begin
          can_transaction etx = can_transaction::type_id::create("etx");
          etx.frame_type = can_transaction::ERROR_FRAME;
          etx.with_error = 1;
          txn_count++;
          ap.write(etx);
          `uvm_info("CAN_MON", "Monitored: ERROR frame on bus", UVM_MEDIUM)
          // drain until bus idle (recessive) again
          do @(posedge vif.clk); while (vif.can_tx !== 1'b1);
          repeat (BIT_CLKS*10) @(posedge vif.clk);
        end else begin
          txn_count++;
          `uvm_info("CAN_MON", $sformatf("Monitored: %s", tx.convert2string()), UVM_MEDIUM)
          ap.write(tx);
          // skip ACK/EOF/intermission
          repeat (BIT_CLKS*12) @(posedge vif.clk);
        end
      end
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("CAN_MON", $sformatf("can monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
