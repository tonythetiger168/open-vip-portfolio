// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_axi_mgr_bfm.svh -- AXI4 manager BFM. The AXI4 master-port kit's
// self-test uses it in place of an IP to prove the subordinate and the
// checkers: legal traffic of every shape the checker accepts, and one
// injection per rule (inject_e) that the checker must catch.
//
// write() / read() are blocking; one write and one read may run in parallel
// (separate processes), so up to one of each is outstanding. Signals change
// on the falling edge; handshakes are sampled on the rising edge.

typedef enum int {
  INJ_NONE,
  INJ_4K,            // INCR burst crossing a 4 KB page         -> TXN_4K
  INJ_LEN,           // more beats than cfg.max_beats            -> TXN_LEN
  INJ_SIZE,          // transfer size not allowed                -> TXN_SIZE
  INJ_BURST,         // burst type not allowed (or reserved)     -> TXN_BURST
  INJ_ALIGN,         // unaligned address                        -> TXN_ALIGN
  INJ_WLAST_EARLY,   // WLAST on the beat before the last        -> TXN_WLAST
  INJ_WLAST_MISSING, // no WLAST on the last beat                -> TXN_WLAST
  INJ_STRB,          // partial strobe where full words promised -> TXN_STRB
  INJ_AW_DROP,       // AWVALID withdrawn before AWREADY         -> CHK_STABLE_AW
  INJ_AW_CHANGE,     // AWADDR changed while waiting             -> CHK_STABLE_AW
  INJ_W_CHANGE,      // WDATA changed while waiting              -> CHK_STABLE_W
  INJ_AR_DROP,       // ARVALID withdrawn before ARREADY         -> CHK_STABLE_AR
  INJ_WINDOW         // write outside the allowed windows        -> TXN_WINDOW
} inject_e;

class ssv_axi_mgr_bfm extends uvm_object;
  `uvm_object_utils(ssv_axi_mgr_bfm)
  virtual axim_if vif;
  int unsigned wvalid_gap_pct = 0;   // chance of an idle clock between W beats
  int unsigned bready_pct = 100, rready_pct = 100;
  int unsigned timeout = 5000;

  function new(string name = "ssv_axi_mgr_bfm");
    super.new(name);
  endfunction

  task init();
    vif.awvalid = 0; vif.awid = 0; vif.awaddr = 0; vif.awlen = 0; vif.awsize = 0; vif.awburst = 0; vif.awprot = 0;
    vif.wvalid = 0; vif.wdata = 0; vif.wstrb = 0; vif.wlast = 0;
    vif.bready = 0;
    vif.arvalid = 0; vif.arid = 0; vif.araddr = 0; vif.arlen = 0; vif.arsize = 0; vif.arburst = 0; vif.arprot = 0;
    vif.rready = 0;
  endtask

  task wait_hs(string what);
    int unsigned n = 0;
    forever begin
      @(posedge vif.aclk);
      if (what == "AW" && vif.awready === 1'b1) break;
      if (what == "W"  && vif.wready  === 1'b1) break;
      if (what == "AR" && vif.arready === 1'b1) break;
      if (++n > timeout) begin
        `uvm_error("BFM_TIMEOUT", {what, " handshake timed out"})
        break;
      end
    end
  endtask

  // a write of len+1 beats; data/strb hold one entry per beat
  task write(bit [3:0] id, bit [31:0] addr, bit [7:0] len, bit [2:0] size, bit [1:0] burst,
             bit [31:0] data[$], bit [3:0] strb[$], output bit [1:0] resp, input inject_e inj = INJ_NONE);
    int unsigned n;
    fork
      begin : aw_ch
        @(negedge vif.aclk);
        vif.awid = id; vif.awaddr = addr; vif.awlen = len; vif.awsize = size; vif.awburst = burst; vif.awprot = 3'b000;
        vif.awvalid = 1;
        if (inj inside {INJ_AW_DROP, INJ_AW_CHANGE}) begin
          // the test holds AWREADY low; wait one rising edge, then misbehave
          @(negedge vif.aclk);
          if (inj == INJ_AW_DROP) begin
            vif.awvalid = 0;
            @(negedge vif.aclk);
            vif.awvalid = 1;
          end else
            vif.awaddr = addr + 32'h4;
        end
        wait_hs("AW");
        @(negedge vif.aclk);
        vif.awvalid = 0;
      end
      begin : w_ch
        for (int unsigned b = 0; b <= len; b++) begin
          @(negedge vif.aclk);
          while (wvalid_gap_pct != 0 && axim_pct(wvalid_gap_pct)) begin
            vif.wvalid = 0;
            @(negedge vif.aclk);
          end
          vif.wdata = data[b]; vif.wstrb = strb[b];
          vif.wlast = (b == len);
          if (inj == INJ_WLAST_EARLY)   vif.wlast = (len > 0 && b == len - 1) || (len == 0);
          if (inj == INJ_WLAST_MISSING) vif.wlast = 0;
          vif.wvalid = 1;
          if (inj == INJ_W_CHANGE && b == 0) begin
            @(negedge vif.aclk);
            vif.wdata = ~data[b];
          end
          wait_hs("W");
        end
        @(negedge vif.aclk);
        vif.wvalid = 0; vif.wlast = 0;
      end
    join
    // response
    n = 0;
    forever begin
      @(negedge vif.aclk);
      vif.bready = axim_pct(bready_pct);
      @(posedge vif.aclk);
      if (vif.bvalid === 1'b1 && vif.bready) break;
      if (++n > timeout) begin
        `uvm_error("BFM_TIMEOUT", $sformatf("no B for write at %08h", addr))
        break;
      end
    end
    resp = vif.bresp;
    if (vif.bid !== id)
      `uvm_error("BFM_BID", $sformatf("B id %0d for a write with id %0d", vif.bid, id))
    @(negedge vif.aclk);
    vif.bready = 0;
  endtask

  task read(bit [3:0] id, bit [31:0] addr, bit [7:0] len, bit [2:0] size, bit [1:0] burst,
            output bit [31:0] data[$], output bit [1:0] resp[$], input inject_e inj = INJ_NONE);
    int unsigned n = 0;
    data.delete(); resp.delete();
    @(negedge vif.aclk);
    vif.arid = id; vif.araddr = addr; vif.arlen = len; vif.arsize = size; vif.arburst = burst; vif.arprot = 3'b000;
    vif.arvalid = 1;
    if (inj == INJ_AR_DROP) begin
      @(negedge vif.aclk);
      vif.arvalid = 0;
      @(negedge vif.aclk);
      vif.arvalid = 1;
    end
    wait_hs("AR");
    @(negedge vif.aclk);
    vif.arvalid = 0;
    while (data.size() <= len) begin
      vif.rready = axim_pct(rready_pct);
      @(posedge vif.aclk);
      if (vif.rvalid === 1'b1 && vif.rready) begin
        data.push_back(vif.rdata);
        resp.push_back(vif.rresp);
        if (vif.rid !== id)
          `uvm_error("BFM_RID", $sformatf("R id %0d for a read with id %0d", vif.rid, id))
        if (vif.rlast !== (data.size() == len + 1))
          `uvm_error("BFM_RLAST", $sformatf("RLAST=%0d on beat %0d of %0d", vif.rlast, data.size() - 1, len + 1))
      end
      if (++n > timeout + 16 * (len + 1)) begin
        `uvm_error("BFM_TIMEOUT", $sformatf("read at %08h stalled after %0d beats", addr, data.size()))
        break;
      end
      @(negedge vif.aclk);
    end
    vif.rready = 0;
  endtask
endclass
