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
// can_driver.svh -- CAN 2.0/FD frame driver: serializes full frames
// (SOF / arbitration / control / data / CRC-15 / ACK / EOF) onto can_rx
// with bit stuffing and a configurable bit time.  This abstract model
// carries up to 8 data bytes per frame (classic payload); FD frames
// exercise the FDF/BRS/ESI control bits.

class can_driver extends uvm_driver #(can_transaction);
  `uvm_component_utils(can_driver)
  virtual can_if vif;
  can_config cfg;
  uvm_analysis_port #(can_transaction) drv_ap;  // expected items for scoreboard

  localparam int BIT_CLKS = 8;   // clock cycles per CAN bit (bit timing)

  function new(string name, uvm_component parent);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual can_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "CAN virtual interface not found")
    if (!uvm_config_db#(can_config)::get(this, "", "cfg", cfg))
      cfg = can_config::type_id::create("cfg");
  endfunction

  // ---- low-level bit output (one bit = BIT_CLKS clocks) ----
  task send_bit(bit b);
    vif.drv_cb.can_rx <= b;
    repeat (BIT_CLKS) @(vif.drv_cb);
  endtask

  // legacy API: drive a single item (kept for backward compatibility)
  task drive_item(can_transaction tx);
    send_frame(tx);
  endtask

  // ---- frame serializer with bit stuffing ----
  task send_frame(can_transaction tx);
    bit raw[$];        // destuffed bits: SOF .. end of data
    bit stuffed[$];    // raw + stuff bits (SOF .. CRC)
    bit [14:0] crc;
    int nbytes;

    nbytes = (tx.data_len > 8) ? 8 : tx.data_len;

    // SOF + arbitration field
    raw.push_back(1'b0);                                       // SOF (dominant)
    if (!tx.ide) begin
      for (int i = 10; i >= 0; i--) raw.push_back(tx.id[i]);   // 11-bit ID
      raw.push_back(tx.rtr);                                   // RTR
      raw.push_back(1'b0);                                     // IDE = 0 (std)
    end else begin
      for (int i = 28; i >= 18; i--) raw.push_back(tx.id[i]);  // base ID
      raw.push_back(1'b1);                                     // SRR
      raw.push_back(1'b1);                                     // IDE = 1 (ext)
      for (int i = 17; i >= 0; i--) raw.push_back(tx.id[i]);   // extended ID
      raw.push_back(tx.rtr);                                   // RTR
      raw.push_back(1'b0);                                     // r1
    end
    // control field
    if (tx.fdf) begin
      raw.push_back(1'b1);                                     // EDL/FDF
      raw.push_back(1'b0);                                     // r0
      raw.push_back(tx.brs);                                   // BRS
      raw.push_back(tx.esi);                                   // ESI
    end else begin
      raw.push_back(1'b0);                                     // r0
    end
    for (int i = 3; i >= 0; i--) raw.push_back(tx.dlc[i]);     // DLC
    // data field (absent for remote frames)
    if (!tx.rtr) begin
      for (int b = 0; b < nbytes; b++)
        for (int i = 7; i >= 0; i--) raw.push_back(tx.data[b*8 + i]);
    end
    // CRC sequence over destuffed SOF..data
    crc = can_crc15(raw);
    if (tx.with_error && tx.crc_error) crc = crc ^ 15'h1;      // corrupt CRC
    for (int i = 14; i >= 0; i--) raw.push_back(crc[i]);

    // bit stuffing (5 consecutive equal bits -> complement), unless injected off
    begin
      int run = 1;
      bit last;
      for (int i = 0; i < raw.size(); i++) begin
        stuffed.push_back(raw[i]);
        if (i == 0) begin last = raw[i]; run = 1; end
        else if (raw[i] == last) begin
          run++;
          if (run == 5 && !(tx.with_error && tx.stuff_error)) begin
            stuffed.push_back(!last);                          // stuff bit
            run = 0;
          end
        end else begin last = raw[i]; run = 1; end
      end
    end

    // ---- serialize ----
    vif.drv_cb.can_en <= 1;
    foreach (stuffed[i]) send_bit(stuffed[i]);
    // CRC delimiter + ACK slot + ACK delimiter (recessive on this node)
    if (tx.with_error && tx.form_error) send_bit(1'b0);        // form error
    else                                send_bit(1'b1);
    send_bit(1'b1);                                            // ACK slot
    send_bit(1'b1);                                            // ACK delimiter
    repeat (7) send_bit(1'b1);                                 // EOF
    repeat (3) send_bit(1'b1);                                 // intermission
    vif.drv_cb.can_en <= 0;
  endtask

  task run_phase(uvm_phase phase);
    can_transaction exp;
    vif.drv_cb.can_rx <= 1'b1;   // recessive idle
    vif.drv_cb.can_en <= 1'b0;
    wait (vif.rst_n === 1'b1);
    forever begin
      seq_item_port.get_next_item(req);
      `uvm_info("CAN_DRV", $sformatf("Driving: %s", req.convert2string()), UVM_MEDIUM)
      send_frame(req);
      // publish what was actually put on the wire (DLC clamped to 8)
      exp = can_transaction::type_id::create("exp");
      exp.copy(req);
      if (exp.data_len > 8) begin exp.data_len = 8; exp.dlc = 8; end
      drv_ap.write(exp);
      seq_item_port.item_done();
    end
  endtask
endclass
