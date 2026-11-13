// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_apb.svh -- APB4 requester agent for the <P>_apb register wrappers:
// item, driver, monitor, agent and the RAL adapter.
//
// Timing (no clocking block, see README "Verilator notes"): the driver
// changes signals on the falling edge and samples PREADY / PRDATA /
// PSLVERR on the rising edge; the monitor samples on the rising edge.

class ssv_apb_item extends uvm_sequence_item;
  `uvm_object_utils(ssv_apb_item)
  bit [11:0] addr;
  bit        write;
  bit [31:0] data;     // write data, or read data once the driver completes
  bit [3:0]  strb = 4'hF;
  bit        slverr;
  int unsigned idle = 0;   // idle clocks before the transfer

  function new(string name = "ssv_apb_item");
    super.new(name);
  endfunction

  virtual function string convert2string();
    return $sformatf("%s @%03h data=%08h strb=%h%s", write ? "WR" : "RD", addr, data, strb,
                     slverr ? " PSLVERR" : "");
  endfunction

  virtual function void do_copy(uvm_object rhs);
    ssv_apb_item r;
    super.do_copy(rhs);
    $cast(r, rhs);
    addr = r.addr; write = r.write; data = r.data; strb = r.strb; slverr = r.slverr; idle = r.idle;
  endfunction
endclass

typedef uvm_sequencer #(ssv_apb_item) ssv_apb_sequencer;

class ssv_apb_driver extends uvm_driver #(ssv_apb_item);
  `uvm_component_utils(ssv_apb_driver)
  virtual ssv_apb_if vif;
  int unsigned timeout = 64;   // clocks to wait for PREADY

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    if (!uvm_config_db #(virtual ssv_apb_if)::get(this, "", "apb_vif", vif))
      `uvm_fatal("NOVIF", "ssv_apb_driver: apb_vif not set")
  endfunction

  task run_phase(uvm_phase phase);
    vif.psel = 0; vif.penable = 0; vif.pwrite = 0; vif.paddr = 0; vif.pwdata = 0; vif.pstrb = 0;
    @(posedge vif.pclk);
    while (!vif.presetn) @(posedge vif.pclk);
    forever begin
      ssv_apb_item it;
      seq_item_port.get_next_item(it);
      xfer(it);
      seq_item_port.item_done();
    end
  endtask

  task xfer(ssv_apb_item it);
    int unsigned n = 0;
    repeat (it.idle) @(posedge vif.pclk);
    @(negedge vif.pclk);                       // setup phase
    vif.psel    = 1'b1;
    vif.penable = 1'b0;
    vif.pwrite  = it.write;
    vif.paddr   = it.addr;
    vif.pwdata  = it.write ? it.data : 32'h0;
    vif.pstrb   = it.write ? it.strb : 4'h0;   // APB4: PSTRB low on reads
    @(negedge vif.pclk);                       // access phase
    vif.penable = 1'b1;
    forever begin
      @(posedge vif.pclk);
      if (vif.pready === 1'b1) break;
      if (++n >= timeout) begin
        `uvm_error("APB_TIMEOUT", $sformatf("no PREADY within %0d clocks: %s", timeout, it.convert2string()))
        break;
      end
    end
    it.slverr = (vif.pslverr === 1'b1);
    if (!it.write) it.data = vif.prdata;
    @(negedge vif.pclk);
    vif.psel = 1'b0; vif.penable = 1'b0;
  endtask
endclass

class ssv_apb_monitor extends uvm_monitor;
  `uvm_component_utils(ssv_apb_monitor)
  virtual ssv_apb_if vif;
  uvm_analysis_port #(ssv_apb_item) ap;
  int unsigned n_wr, n_rd, n_err;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    if (!uvm_config_db #(virtual ssv_apb_if)::get(this, "", "apb_vif", vif))
      `uvm_fatal("NOVIF", "ssv_apb_monitor: apb_vif not set")
  endfunction

  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.pclk);
      if (vif.presetn && vif.psel && vif.penable && vif.pready === 1'b1) begin
        ssv_apb_item it = ssv_apb_item::type_id::create("apb_mon");
        it.addr   = vif.paddr;
        it.write  = vif.pwrite;
        it.strb   = vif.pstrb;
        it.data   = vif.pwrite ? vif.pwdata : vif.prdata;
        it.slverr = (vif.pslverr === 1'b1);
        if (it.write) n_wr++; else n_rd++;
        if (it.slverr) n_err++;
        ap.write(it);
      end
    end
  endtask

  function void check_phase(uvm_phase phase);
    if (vif.chk_errors != 0)
      `uvm_error("APB_CHK", $sformatf("%0d APB4 protocol errors (see APB_CHK_ERROR lines)", vif.chk_errors))
  endfunction
endclass

class ssv_apb_agent extends uvm_agent;
  `uvm_component_utils(ssv_apb_agent)
  ssv_apb_sequencer sqr;
  ssv_apb_driver    drv;
  ssv_apb_monitor   mon;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    mon = ssv_apb_monitor::type_id::create("mon", this);
    sqr = ssv_apb_sequencer::type_id::create("sqr", this);
    drv = ssv_apb_driver::type_id::create("drv", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    drv.seq_item_port.connect(sqr.seq_item_export);
  endfunction
endclass

// RAL adapter: one uvm_reg_bus_op <-> one APB transfer. The driver completes
// the request in place, so provides_responses = 0. Byte enables map to PSTRB.
class ssv_apb_reg_adapter extends uvm_reg_adapter;
  `uvm_object_utils(ssv_apb_reg_adapter)

  function new(string name = "ssv_apb_reg_adapter");
    super.new(name);
    supports_byte_enable = 1;
    provides_responses   = 0;
  endfunction

  virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
    ssv_apb_item it = ssv_apb_item::type_id::create("ral_apb");
    it.addr  = rw.addr[11:0];
    it.write = (rw.kind == UVM_WRITE);
    it.data  = rw.data[31:0];
    it.strb  = (rw.byte_en[3:0] == 4'h0) ? 4'hF : rw.byte_en[3:0];
    return it;
  endfunction

  virtual function void bus2reg(uvm_sequence_item bus_item, ref uvm_reg_bus_op rw);
    ssv_apb_item it;
    if (!$cast(it, bus_item)) begin
      `uvm_fatal("SSV_RAL", "bus2reg: not an ssv_apb_item")
      return;
    end
    rw.kind    = it.write ? UVM_WRITE : UVM_READ;
    rw.addr    = it.addr;
    rw.data    = it.data;
    rw.n_bits  = 32;
    rw.byte_en = it.strb;
    rw.status  = it.slverr ? UVM_NOT_OK : UVM_IS_OK;
  endfunction
endclass

// Raw register access outside the RAL (used for illegal-access probes and by
// tests that poll without disturbing the mirror).
class ssv_apb_rw_seq extends uvm_sequence #(ssv_apb_item);
  `uvm_object_utils(ssv_apb_rw_seq)
  bit [11:0] addr;
  bit        write;
  bit [31:0] data;
  bit [3:0]  strb = 4'hF;
  bit        slverr;

  function new(string name = "ssv_apb_rw_seq");
    super.new(name);
  endfunction

  task body();
    ssv_apb_item it = ssv_apb_item::type_id::create("it");
    start_item(it);
    it.addr = addr; it.write = write; it.data = data; it.strb = strb;
    finish_item(it);
    data = it.data; slverr = it.slverr;
  endtask
endclass
