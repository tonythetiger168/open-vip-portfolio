// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mipi_vip_pkg.sv -- MIPI Protocol Verification IP (VIP) Package
// Protocols: CSI-2, DSI, D-PHY, C-PHY, M-PHY, UniPro, DigRFv4, HSI, CSE 2.0
// This instance is deepened for: C-PHY
//
// MAC + PHY Layer Coverage-Driven Random Regression Suite
//============================================================================

`ifndef MIPI_VIP_PKG_SV
`define MIPI_VIP_PKG_SV

package mipi_vip_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  typedef enum int {
    MIPI_CSI2=0, MIPI_DSI=1, MIPI_DPHY=2, MIPI_CPHY=3, MIPI_MPHY=4,
    MIPI_UNIPRO=5, MIPI_DIGRF=6, MIPI_HSI=7, MIPI_CSE=8, MIPI_MAX=9
  } mipi_protocol_e;

  typedef enum int {
    SPEED_DPHY_1G5=1500, SPEED_DPHY_2G5=2500, SPEED_DPHY_4G5=4500,
    SPEED_CPHY_2G=2000, SPEED_CPHY_4G=4000,
    SPEED_MPHY_G1=1248, SPEED_MPHY_G2=2496, SPEED_MPHY_G3=4992,
    SPEED_MPHY_G4=9984, SPEED_MPHY_G5=19968,
    SPEED_UNIPRO_1G=1000,
    SPEED_HSI_150M=150
  } mipi_speed_e;

  // Aliases kept out of the enum: IEEE 1800 requires unique enumeration values
  localparam mipi_speed_e SPEED_UNIPRO_2G  = SPEED_CPHY_2G;   // 2000
  localparam mipi_speed_e SPEED_UNIPRO_4G  = SPEED_CPHY_4G;   // 4000
  localparam mipi_speed_e SPEED_DIGRF_150M = SPEED_HSI_150M;  // 150
  localparam mipi_speed_e SPEED_CSE_1G     = SPEED_UNIPRO_1G; // 1000

  typedef enum logic [3:0] {
    ST_STOP=4'h0, ST_HS_REQ=4'h1, ST_HS_ZERO=4'h2, ST_HS_SYNC=4'h3,
    ST_HS_DATA=4'h4, ST_HS_TRAIL=4'h5, ST_HS_EXIT=4'h6, ST_LP11=4'h7,
    ST_LP00=4'h8, ST_LP01=4'h9, ST_LP10=4'hA, ST_TA_REQ=4'hB,
    ST_TA_GRANT=4'hC, ST_ULPS=4'hD
  } mipi_lane_state_e;

  typedef enum logic [5:0] {
    PKT_FS=6'h00, PKT_FE=6'h01, PKT_LS=6'h02, PKT_LE=6'h03,
    PKT_RGB565=6'h0E, PKT_RGB666=6'h1E, PKT_RGB888=6'h2E,
    PKT_RAW6=6'h28, PKT_RAW7=6'h29, PKT_RAW8=6'h2A, PKT_RAW10=6'h2B,
    PKT_RAW12=6'h2C, PKT_RAW14=6'h2D,
    PKT_YUV422_8B=6'h18, PKT_YUV422_10B=6'h1F,
    PKT_USER_0=6'h30, PKT_USER_1=6'h31, PKT_USER_2=6'h32, PKT_USER_3=6'h33,
    PKT_USER_4=6'h34, PKT_USER_5=6'h35, PKT_USER_6=6'h36, PKT_USER_7=6'h37,
    PKT_NULL=6'h3A, PKT_BLANK=6'h3B, PKT_EMBEDDED=6'h3C
  } mipi_pkt_type_e;

  typedef enum logic [2:0] {
    VC_0=3'd0, VC_1=3'd1, VC_2=3'd2, VC_3=3'd3,
    VC_4=3'd4, VC_5=3'd5, VC_6=3'd6, VC_7=3'd7
  } mipi_vc_e;

  // Protocol this VIP instance is specialized for
  localparam mipi_protocol_e VIP_PROTOCOL = MIPI_CPHY;

  //--------------------------------------------------------------------------
  // MIPI packet ECC (Hamming-based, allows 1-bit correction / 2-bit detect)
  // computed over {word_count[15:0], vc[1:0], data_type[5:0]} (24 bits)
  //--------------------------------------------------------------------------
  function automatic logic [7:0] mipi_calc_ecc(logic [23:0] d);
    logic [7:0] p;
    p[0] = d[0]^d[1]^d[2]^d[4]^d[5]^d[7]^d[10]^d[11]^d[13]^d[16]^d[20]^d[21]^d[22]^d[23];
    p[1] = d[0]^d[1]^d[3]^d[4]^d[6]^d[8]^d[10]^d[12]^d[14]^d[17]^d[20]^d[21]^d[22]^d[23];
    p[2] = d[0]^d[2]^d[3]^d[5]^d[6]^d[9]^d[11]^d[12]^d[15]^d[18]^d[20]^d[21]^d[22];
    p[3] = d[1]^d[2]^d[3]^d[7]^d[8]^d[9]^d[13]^d[14]^d[15]^d[19]^d[20]^d[21]^d[23];
    p[4] = d[4]^d[5]^d[6]^d[7]^d[8]^d[9]^d[16]^d[17]^d[18]^d[19]^d[20]^d[22]^d[23];
    p[5] = d[10]^d[11]^d[12]^d[13]^d[14]^d[15]^d[16]^d[17]^d[18]^d[19]^d[21]^d[22]^d[23];
    p[6] = 1'b0;
    p[7] = 1'b0;
    return p;
  endfunction

  //--------------------------------------------------------------------------
  // MIPI packet CRC-16 (poly 0x1021 reflected -> 0x8408, init 0xFFFF)
  //--------------------------------------------------------------------------
  function automatic logic [15:0] mipi_calc_crc16(const ref logic [31:0] words[]);
    logic [15:0] crc;
    logic [7:0]  cur;
    crc = 16'hFFFF;
    foreach (words[i]) begin
      for (int b = 0; b < 4; b++) begin
        cur = words[i][b*8 +: 8];
        for (int k = 0; k < 8; k++) begin
          if ((crc[0] ^ cur[0]) == 1'b1) crc = (crc >> 1) ^ 16'h8408;
          else                           crc = (crc >> 1);
          cur = cur >> 1;
        end
      end
    end
    return crc;
  endfunction

  // C-PHY 3-phase wire state encoder: next legal triplet (must change every
  // symbol, wires are 3-level; simplified model excludes 000/111 repeats)
  function automatic logic [2:0] mipi_cphy_next_triplet(logic [2:0] prev, logic [2:0] sym_low);
    logic [2:0] t;
    t = sym_low;
    if (t == prev) t = t + 3'd1;
    return t;
  endfunction

  //==========================================================================
  // Transaction
  //==========================================================================
  class mipi_txn extends uvm_object;
    `uvm_object_utils(mipi_txn)
    rand mipi_protocol_e protocol;
    rand mipi_pkt_type_e pkt_type;
    rand mipi_vc_e vc;
    rand logic [15:0] word_count;
    rand logic [31:0] data[];
    rand logic [15:0] ecc;
    rand logic [31:0] crc;
    rand int lane_count;
    rand int data_rate;
    rand bit lp_mode;
    rand bit hs_mode;
    rand bit ulps;
    rand bit inject_err;
    rand int delay;
    // Deepened: link/PHY state observed with this transaction + error flags
    mipi_lane_state_e state = ST_STOP;
    bit        ecc_err = 0;
    bit        crc_err = 0;
    // UniPro specific
    rand logic [3:0] cport;
    rand logic [2:0] tc;
    rand logic [7:0] credit;

    constraint c_wc { word_count inside {[1:4095]}; }
    constraint c_data { data.size() == ((word_count+1)/2); }
    constraint c_lane {
      if (protocol==MIPI_DPHY) lane_count inside {1,2,4};
      else if (protocol==MIPI_CPHY) lane_count inside {1,2,3};
      else if (protocol==MIPI_MPHY) lane_count inside {1,2};
      else lane_count inside {1,2,4};
    }
    constraint c_mode { lp_mode != hs_mode; }
    constraint c_err { inject_err dist {0:=90, 1:=10}; }
    constraint c_delay { delay inside {[0:20]}; }

    function new(string name="mipi_txn"); super.new(name); endfunction

    // Recompute ECC over the packet header (short packets: WC=0)
    function void compute_ecc();
      ecc = {8'h00, mipi_calc_ecc({word_count, vc[1:0], pkt_type})};
      if (inject_err) ecc = ecc ^ 16'h0001;   // single-bit error injection
    endfunction

    // Recompute CRC-16 over the payload
    function void compute_crc();
      crc = {16'h0000, mipi_calc_crc16(data)};
      if (inject_err) crc = crc ^ 32'h00000001; // payload CRC error injection
    endfunction

    virtual function string convert2string();
      return $sformatf("%s pkt=%s vc=%0d wc=%0d",protocol.name(),pkt_type.name(),vc,word_count);
    endfunction

    // Field-level compare for the end-to-end scoreboard
    virtual function bit compare(mipi_txn o);
      return (protocol  == o.protocol) &&
             (pkt_type  == o.pkt_type) &&
             (vc        == o.vc) &&
             (word_count== o.word_count) &&
             (data.size()== o.data.size());
    endfunction
  endclass

  class mipi_seq_item extends uvm_sequence_item;
    `uvm_object_utils(mipi_seq_item)
    rand mipi_txn txn;
    function new(string name="mipi_seq_item");
      super.new(name);
      txn=mipi_txn::type_id::create("txn");
    endfunction
  endclass

  `uvm_analysis_imp_decl(_exp)
  `uvm_analysis_imp_decl(_obs)

  class mipi_sequencer extends uvm_sequencer #(mipi_seq_item);
    `uvm_component_utils(mipi_sequencer)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
  endclass

  //==========================================================================
  // Driver: serializes a mipi_txn onto the MAC bus (sop/eop/valid/ready
  // handshake, header with ECC, payload, CRC footer) and performs the
  // protocol-specific PHY/LP-HS/symbol/credit signaling around it.
  //==========================================================================
  class mipi_driver extends uvm_driver #(mipi_seq_item);
    `uvm_component_utils(mipi_driver)
    virtual mipi_vip_if vif;
    uvm_analysis_port #(mipi_seq_item) drv_ap;  // expected items for scoreboard

    function new(string name, uvm_component parent);
      super.new(name, parent);
      drv_ap = new("drv_ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "mipi driver: virtual interface not set")
    endfunction

    task run_phase(uvm_phase phase);
      mipi_seq_item item;
      vif.drv_cb.valid <= 0; vif.drv_cb.sop <= 0; vif.drv_cb.eop <= 0;
      vif.drv_cb.dphy_hs_rqst <= 0; vif.drv_cb.cphy_symbol_valid <= 0;
      vif.drv_cb.unipro_valid <= 0; vif.drv_cb.hsi_valid <= 0;
      vif.drv_cb.cse_valid <= 0; vif.drv_cb.digrf_valid <= 0;
      wait (vif.rst_n === 1'b1);
      forever begin
        seq_item_port.get_next_item(item);
        item.txn.protocol = VIP_PROTOCOL;
        `uvm_info("DRV", {"drive: ", item.txn.convert2string()}, UVM_HIGH)
        repeat (item.txn.delay) @(vif.drv_cb);
        drive_phy_preamble(item.txn);
        drive_mac_packet(item.txn);
        drive_phy_postamble(item.txn);
        drv_ap.write(item);            // broadcast expected transaction
        seq_item_port.item_done();
      end
    endtask

    // ---- MAC layer packet: header (ECC) / payload / CRC footer ----
    task drive_mac_packet(mipi_txn t);
      t.compute_ecc();
      t.compute_crc();
      t.state = ST_HS_DATA;
      // CSI-2/DSI style header mirrors (data type / word count / active lanes)
      vif.data_type   = t.pkt_type;
      vif.wc          = t.word_count;
      vif.lane_active = '1;
      // header beat
      vif.drv_cb.pkt_type   <= t.pkt_type;
      vif.drv_cb.vc         <= t.vc;
      vif.drv_cb.word_count <= t.word_count;
      vif.drv_cb.ecc        <= t.ecc;
      vif.drv_cb.data       <= (t.data.size() > 0) ? t.data[0] : 32'h0;
      vif.drv_cb.sop        <= 1'b1;
      vif.drv_cb.eop        <= (t.data.size() <= 1);
      if (t.data.size() <= 1) vif.drv_cb.crc <= t.crc;
      vif.drv_cb.valid      <= 1'b1;
      do @(vif.drv_cb); while (!vif.drv_cb.ready);
      vif.drv_cb.sop <= 1'b0;
      // payload beats
      for (int i = 1; i < t.data.size(); i++) begin
        vif.drv_cb.data <= t.data[i];
        vif.drv_cb.eop  <= (i == t.data.size()-1);
        if (i == t.data.size()-1) vif.drv_cb.crc <= t.crc;
        do @(vif.drv_cb); while (!vif.drv_cb.ready);
      end
      vif.drv_cb.valid <= 1'b0;
      vif.drv_cb.eop   <= 1'b0;
    endtask

    // ---- protocol-specific PHY signaling before the packet ----
    task drive_phy_preamble(mipi_txn t);
      case (VIP_PROTOCOL)
        MIPI_CSI2, MIPI_DPHY, MIPI_DSI: begin
          // LP-11 -> LP-01 -> LP-00 (HS request) -> HS sync 0xB8 -> HS data
          vif.lane_state = ST_LP11;
          vif.drv_cb.dphy_lp_dir <= 1'b0;
          @(vif.drv_cb);
          vif.lane_state = ST_LP01;
          @(vif.drv_cb);
          vif.lane_state = ST_HS_REQ;
          vif.drv_cb.dphy_hs_rqst <= 1'b1;
          do @(vif.drv_cb); while (!vif.drv_cb.dphy_hs_rdy);
          vif.lane_state = ST_HS_SYNC;
          @(vif.drv_cb);
          vif.lane_state = ST_HS_DATA;
        end
        MIPI_CPHY: begin
          // 3-phase symbol stream preamble on C-PHY lanes
          vif.lane_state = ST_HS_SYNC;
          vif.drv_cb.cphy_symbol <= {{57{1'b0}}, 7'b0101010};
          vif.drv_cb.cphy_symbol_valid <= 1'b1;
          @(vif.drv_cb);
        end
        MIPI_MPHY: begin
          // M-PHY: SYNC burst (DIF-P) then HS burst in configured gear
          vif.lane_state = ST_HS_SYNC;
          vif.drv_cb.mphy_series_a <= 1'b1;
          vif.drv_cb.mphy_gear     <= 4'd3;
          vif.drv_cb.mphy_pwm_mode <= t.lp_mode;
          @(vif.drv_cb);
          vif.lane_state = ST_HS_DATA;
        end
        MIPI_UNIPRO: begin
          // UniPro: CPort addressed data frame on TC with credit flow control
          vif.lane_state = ST_HS_DATA;
          vif.drv_cb.unipro_cport <= t.cport;
          vif.drv_cb.unipro_tc    <= t.tc;
          vif.drv_cb.unipro_data  <= 8'h01;   // SOF marker
          vif.drv_cb.unipro_valid <= 1'b1;
          do @(vif.drv_cb); while (!vif.drv_cb.unipro_ready);
        end
        default: @(vif.drv_cb);
      endcase
    endtask

    // ---- protocol-specific PHY signaling after the packet ----
    task drive_phy_postamble(mipi_txn t);
      logic [2:0] tri_v;
      logic [6:0] enc;
      tri_v = 3'b001;
      case (VIP_PROTOCOL)
        MIPI_CSI2, MIPI_DPHY, MIPI_DSI: begin
          // HS trail -> HS exit -> LP-11; optional ULPS entry
          vif.lane_state = ST_HS_TRAIL;
          @(vif.drv_cb);
          vif.drv_cb.dphy_hs_rqst <= 1'b0;
          vif.lane_state = ST_HS_EXIT;
          @(vif.drv_cb);
          if (t.ulps) begin
            vif.lane_state = ST_ULPS;
            repeat (4) @(vif.drv_cb);
          end
          vif.lane_state = ST_LP11;
          repeat (2) @(vif.drv_cb);
        end
        MIPI_CPHY: begin
          // map payload to 7-bit symbols, 3-phase encoded triplets
          for (int i = 0; i < t.data.size() && i < 4; i++) begin
            tri_v = mipi_cphy_next_triplet(tri_v, t.data[i][2:0]);
            enc = t.data[i][6:0] ^ {4'b0, tri_v};
            vif.drv_cb.cphy_symbol <= {{57{1'b0}}, enc};
            @(vif.drv_cb);
          end
          vif.drv_cb.cphy_symbol_valid <= 1'b0;
          vif.lane_state = ST_LP11;
          repeat (2) @(vif.drv_cb);
        end
        MIPI_MPHY: begin
          vif.lane_state = ST_HS_TRAIL;
          @(vif.drv_cb);
          vif.drv_cb.mphy_pwm_mode <= 1'b0;
          vif.lane_state = ST_STOP;
          repeat (2) @(vif.drv_cb);
        end
        MIPI_UNIPRO: begin
          vif.drv_cb.unipro_data  <= 8'h02;   // EOF marker
          do @(vif.drv_cb); while (!vif.drv_cb.unipro_ready);
          vif.drv_cb.unipro_valid <= 1'b0;
          vif.lane_state = ST_STOP;
        end
        default: @(vif.drv_cb);
      endcase
    endtask
  endclass

  //==========================================================================
  // Monitor: decodes MAC packets (header/payload/CRC) from the bus waveform
  // and re-publishes reconstructed transactions on the analysis port.
  //==========================================================================
  class mipi_monitor extends uvm_monitor;
    `uvm_component_utils(mipi_monitor)
    virtual mipi_vip_if vif;
    uvm_analysis_port #(mipi_seq_item) ap;
    int unsigned txn_count = 0;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "mipi monitor: virtual interface not set")
    endfunction

    task run_phase(uvm_phase phase);
      mipi_seq_item item;
      forever begin
        @(vif.mon_cb);
        if (!vif.rst_n) continue;
        // packet start: valid & sop & accepted
        if (vif.mon_cb.valid && vif.mon_cb.sop && vif.mon_cb.ready) begin
          item = mipi_seq_item::type_id::create("item");
          item.txn.protocol   = VIP_PROTOCOL;
          item.txn.pkt_type   = mipi_pkt_type_e'(vif.mon_cb.pkt_type);
          item.txn.vc         = mipi_vc_e'(vif.mon_cb.vc);
          item.txn.word_count = vif.mon_cb.word_count;
          item.txn.ecc        = vif.mon_cb.ecc;
          item.txn.state      = vif.lane_state;
          item.txn.data       = new[(vif.mon_cb.word_count+1)/2];
          item.txn.data[0]    = vif.mon_cb.data;
          // payload beats until eop
          for (int i = 1; i < item.txn.data.size(); i++) begin
            do @(vif.mon_cb); while (!(vif.mon_cb.valid && vif.mon_cb.ready));
            item.txn.data[i] = vif.mon_cb.data;
          end
          if (item.txn.data.size() > 1) begin
            do @(vif.mon_cb); while (!(vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.eop));
          end
          item.txn.crc = vif.mon_cb.crc;
          // local integrity flags
          item.txn.ecc_err = (vif.mon_cb.ecc != {8'h00, mipi_calc_ecc({vif.mon_cb.word_count, vif.mon_cb.vc[1:0], vif.mon_cb.pkt_type})});
          item.txn.crc_err = (vif.mon_cb.crc[15:0] != mipi_calc_crc16(item.txn.data));
          txn_count++;
          `uvm_info("MON", {"mon: ", item.txn.convert2string()}, UVM_HIGH)
          ap.write(item);
        end
      end
    endtask

    function void report_phase(uvm_phase phase);
      `uvm_info("MON", $sformatf("mipi monitor observed %0d transactions", txn_count), UVM_LOW)
    endfunction
  endclass

  //==========================================================================
  // Agent
  //==========================================================================
  class mipi_agent extends uvm_agent;
    `uvm_component_utils(mipi_agent)
    mipi_sequencer sqr;
    mipi_driver    drv;
    mipi_monitor   mon;
    uvm_analysis_port #(mipi_seq_item) ap;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      mon = mipi_monitor::type_id::create("mon", this);
      if (get_is_active() == UVM_ACTIVE) begin
        sqr = mipi_sequencer::type_id::create("sqr", this);
        drv = mipi_driver::type_id::create("drv", this);
      end
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (get_is_active() == UVM_ACTIVE)
        drv.seq_item_port.connect(sqr.seq_item_export);
      mon.ap.connect(ap);
    endfunction
  endclass

  //==========================================================================
  // Functional coverage: protocol config / lane FSM transitions / data pattern
  //==========================================================================
  class mipi_cov extends uvm_component;
    `uvm_component_utils(mipi_cov)

    // Coverpoint sample variables (declared before the covergroups that
    // reference them, per IEEE 1800 declaration-before-use rules)
    mipi_protocol_e txn_protocol; mipi_pkt_type_e txn_pkt; mipi_vc_e txn_vc;
    int txn_lane; int txn_mode; logic [15:0] txn_wc;
    mipi_lane_state_e txn_state; logic [31:0] txn_d0; bit txn_ecc_err; bit txn_crc_err;
    uvm_analysis_imp #(mipi_seq_item, mipi_cov) cov_ap;

    covergroup cg_mipi;
      option.per_instance=1;
      cp_prot: coverpoint txn_protocol { bins csi2={MIPI_CSI2}; bins dsi={MIPI_DSI}; bins dphy={MIPI_DPHY}; bins cphy={MIPI_CPHY}; bins mphy={MIPI_MPHY}; bins unipro={MIPI_UNIPRO}; bins digrf={MIPI_DIGRF}; bins hsi={MIPI_HSI}; bins cse={MIPI_CSE}; }
      cp_pkt: coverpoint txn_pkt { bins fs={PKT_FS}; bins fe={PKT_FE}; bins ls={PKT_LS}; bins le={PKT_LE}; bins rgb={PKT_RGB565,PKT_RGB666,PKT_RGB888}; bins raw={PKT_RAW6,PKT_RAW8,PKT_RAW10,PKT_RAW12}; bins yuv={PKT_YUV422_8B,PKT_YUV422_10B}; bins user={[PKT_USER_0:PKT_USER_7]}; bins null_b={PKT_NULL,PKT_BLANK}; }
      cp_vc: coverpoint txn_vc { bins vc0={VC_0}; bins vc1={VC_1}; bins vc2={VC_2}; bins vc3={VC_3}; bins vc4_7={[VC_4:VC_7]}; }
      cp_lane: coverpoint txn_lane { bins x1={1}; bins x2={2}; bins x3={3}; bins x4={4}; }
      cp_mode: coverpoint txn_mode { bins lp={0}; bins hs={1}; bins ulps={2}; }
      cp_wc: coverpoint txn_wc { bins wc_min={1}; bins wc_small={[2:255]}; bins wc_med={[256:1023]}; bins wc_large={[1024:4095]}; }
      cross_pkt_vc: cross cp_pkt, cp_vc;
      cross_prot_lane: cross cp_prot, cp_lane;
      cross_mode_wc: cross cp_mode, cp_wc;
    endgroup

    covergroup cg_fsm;
      option.per_instance=1;
      cp_state: coverpoint txn_state {
        bins lp11={ST_LP11}; bins hs_req={ST_HS_REQ}; bins hs_sync={ST_HS_SYNC}; bins hs_data={ST_HS_DATA}; bins trail={ST_HS_TRAIL}; bins exit={ST_HS_EXIT}; bins ulps={ST_ULPS}; bins stop={ST_STOP};
      }
      cp_trans: coverpoint txn_state {
        bins hs_entry = (ST_LP11 => ST_LP01 => ST_HS_REQ => ST_HS_SYNC => ST_HS_DATA);
        bins hs_exit  = (ST_HS_DATA => ST_HS_TRAIL => ST_HS_EXIT => ST_LP11);
        bins ulps_seq = (ST_LP11 => ST_ULPS => ST_LP11);
      }
    endgroup

    covergroup cg_data;
      option.per_instance=1;
      cp_d0: coverpoint txn_d0 {
        bins zero={32'h0}; bins ones={32'hFFFFFFFF}; bins low={[32'h1:32'h0000FFFF]}; bins high={[32'hFFFF0000:32'hFFFFFFFE]};
      }
      cp_ecc_err: coverpoint txn_ecc_err { bins ok={0}; bins err={1}; }
      cp_crc_err: coverpoint txn_crc_err { bins ok={0}; bins err={1}; }
      cross_d0_ecc: cross cp_d0, cp_ecc_err;
    endgroup


    function new(string name="mipi_cov", uvm_component parent=null);
      super.new(name,parent);
      cov_ap = new("cov_ap", this);
      cg_mipi=new(); cg_fsm=new(); cg_data=new();
    endfunction

    virtual function void write(mipi_seq_item item); sample(item.txn); endfunction

    function void sample(mipi_txn t);
      txn_protocol=t.protocol; txn_pkt=t.pkt_type; txn_vc=t.vc;
      txn_lane=t.lane_count; txn_mode=t.lp_mode?0:(t.hs_mode?1:2);
      txn_wc=t.word_count; txn_state=t.state;
      txn_d0=(t.data.size()>0)?t.data[0]:32'h0;
      txn_ecc_err=t.ecc_err; txn_crc_err=t.crc_err;
      cg_mipi.sample(); cg_fsm.sample(); cg_data.sample();
    endfunction

    function real get_cov();
      return (cg_mipi.get_coverage()+cg_fsm.get_coverage()+cg_data.get_coverage())/3.0;
    endfunction
  endclass

  //==========================================================================
  // Scoreboard: end-to-end compare of driver-issued (expected) vs
  // monitor-decoded (observed) transactions.
  //==========================================================================
  class mipi_sb extends uvm_scoreboard;
    `uvm_component_utils(mipi_sb)
    uvm_analysis_imp #(mipi_seq_item,mipi_sb) analysis_imp;
    uvm_analysis_imp_exp #(mipi_seq_item,mipi_sb) exp_ap;
    uvm_analysis_imp_obs #(mipi_seq_item,mipi_sb) obs_ap;
    int txn_cnt, err_cnt;
    mipi_seq_item exp_q[$], obs_q[$];
    int unsigned n_matches = 0, n_mismatches = 0;

    function new(string name="mipi_sb", uvm_component parent=null);
      super.new(name,parent);
      analysis_imp=new("analysis_imp",this);
      exp_ap=new("exp_ap",this);
      obs_ap=new("obs_ap",this);
    endfunction

    virtual function void write(mipi_seq_item item);
      txn_cnt++; if(item.txn.inject_err) err_cnt++;
    endfunction

    virtual function void write_exp(mipi_seq_item item);
      exp_q.push_back(item); check();
    endfunction

    virtual function void write_obs(mipi_seq_item item);
      obs_q.push_back(item); check();
    endfunction

    function void check();
      while (exp_q.size() && obs_q.size()) begin
        mipi_seq_item e = exp_q.pop_front();
        mipi_seq_item o = obs_q.pop_front();
        bit exp_err = e.txn.inject_err;
        bit obs_err = o.txn.ecc_err || o.txn.crc_err;
        // fields must match AND error-injected packets must be flagged by the
        // monitor's ECC/CRC re-computation (clean packets must not be flagged)
        if (e.txn.compare(o.txn) && (exp_err == obs_err))
          n_matches++;
        else begin
          n_mismatches++;
          `uvm_error("SB", $sformatf("mismatch exp{%s} obs{%s} ecc_err=%0b crc_err=%0b",
                     e.txn.convert2string(), o.txn.convert2string(), o.txn.ecc_err, o.txn.crc_err))
        end
      end
    endfunction

    virtual function void report_phase(uvm_phase phase);
      `uvm_info("SB",$sformatf("TXN:%0d ERR:%0d",txn_cnt,err_cnt),UVM_LOW);
      `uvm_info("SB",$sformatf("mipi scoreboard: n_matches=%0d n_mismatches=%0d",n_matches,n_mismatches),UVM_LOW);
      if (n_mismatches) `uvm_error("SB","end-to-end n_mismatches detected")
    endfunction
  endclass

  //==========================================================================
  // Sequence library (directed + regression)
  //==========================================================================
  class mipi_base_sequence extends uvm_sequence #(mipi_seq_item);
    `uvm_object_utils(mipi_base_sequence)
    int num_txns = 20;
    function new(string name="mipi_base_sequence"); super.new(name); endfunction
    task body();
      mipi_seq_item item;
      repeat (num_txns) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol == VIP_PROTOCOL; });
        finish_item(item);
      end
    endtask
  endclass

  // Directed: normal frame traffic (long packets on VC0, HS mode)
  class mipi_normal_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_normal_seq)
    function new(string name="mipi_normal_seq"); super.new(name); endfunction
    task body();
      mipi_seq_item item;
      // frame start
      item = mipi_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.pkt_type==PKT_FS;
                                    txn.vc==VC_0; txn.inject_err==0; });
      finish_item(item);
      // long data packets
      repeat (num_txns) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol==VIP_PROTOCOL;
                                      txn.pkt_type inside {PKT_RGB888,PKT_RAW8,PKT_RAW10,PKT_YUV422_8B};
                                      txn.vc==VC_0; txn.hs_mode==1; txn.lp_mode==0; txn.inject_err==0; });
        finish_item(item);
      end
      // frame end
      item = mipi_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.pkt_type==PKT_FE;
                                    txn.vc==VC_0; txn.inject_err==0; });
      finish_item(item);
    endtask
  endclass

  // Error injection: corrupted ECC/CRC packets
  class mipi_error_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_error_seq)
    function new(string name="mipi_error_seq"); super.new(name); endfunction
    task body();
      mipi_seq_item item;
      repeat (num_txns) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.inject_err==1; });
        finish_item(item);
      end
    endtask
  endclass

  // Reset behavior: one transfer issued right after reset release
  class mipi_reset_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_reset_seq)
    function new(string name="mipi_reset_seq"); super.new(name); endfunction
    task body();
      mipi_seq_item item = mipi_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.word_count==1;
                                    txn.inject_err==0; });
      finish_item(item);
    endtask
  endclass

  // Back-to-back: minimum inter-packet gap
  class mipi_back_to_back_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_back_to_back_seq)
    function new(string name="mipi_back_to_back_seq"); super.new(name); endfunction
    task body();
      mipi_seq_item item;
      repeat (num_txns) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.delay==0;
                                      txn.word_count inside {[1:4]}; txn.inject_err==0; });
        finish_item(item);
      end
    endtask
  endclass

  // Stress: long bursts, many transactions, all VCs
  class mipi_stress_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_stress_seq)
    function new(string name="mipi_stress_seq"); super.new(name); num_txns=100; endfunction
    task body();
      mipi_seq_item item;
      repeat (num_txns) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol==VIP_PROTOCOL;
                                      txn.word_count inside {[512:4095]};
                                      txn.inject_err==0; });
        finish_item(item);
      end
    endtask
  endclass

  // Corner cases: min/max word count, ULPS entry, null/blank packets, LP mode
  class mipi_corner_seq extends mipi_base_sequence;
    `uvm_object_utils(mipi_corner_seq)
    function new(string name="mipi_corner_seq"); super.new(name); endfunction
    task body();
      mipi_seq_item item;
      int unsigned wc_list[$] = '{1, 2, 4094, 4095};
      foreach (wc_list[i]) begin
        item = mipi_seq_item::type_id::create("item");
        start_item(item);
        void'(item.randomize() with { txn.protocol==VIP_PROTOCOL;
                                      txn.word_count==wc_list[i]; txn.inject_err==0; });
        finish_item(item);
      end
      // ULPS entry/exit
      item = mipi_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.ulps==1; txn.inject_err==0; });
      finish_item(item);
      // NULL / BLANKING / EMBEDDED short packets
      begin
        mipi_pkt_type_e short_pkts[$] = '{PKT_NULL, PKT_BLANK, PKT_EMBEDDED, PKT_LS, PKT_LE};
        foreach (short_pkts[i]) begin
          item = mipi_seq_item::type_id::create("item");
          start_item(item);
          void'(item.randomize() with { txn.protocol==VIP_PROTOCOL; txn.pkt_type==short_pkts[i];
                                        txn.lp_mode==1; txn.hs_mode==0; txn.inject_err==0; });
          finish_item(item);
        end
      end
    endtask
  endclass

  class mipi_random_sequence extends mipi_base_sequence;
    `uvm_object_utils(mipi_random_sequence)
    function new(string name="mipi_random_sequence"); super.new(name); num_txns=50; endfunction
  endclass

  // Regression: weighted mix of all directed sequences
  class mipi_regression_sequence extends mipi_base_sequence;
    `uvm_object_utils(mipi_regression_sequence)
    function new(string name="mipi_regression_sequence"); super.new(name); endfunction
    task body();
      mipi_normal_seq      nrm = mipi_normal_seq::type_id::create("nrm");
      mipi_error_seq       err = mipi_error_seq::type_id::create("err");
      mipi_reset_seq       rst = mipi_reset_seq::type_id::create("rst");
      mipi_back_to_back_seq b2b = mipi_back_to_back_seq::type_id::create("b2b");
      mipi_stress_seq      str = mipi_stress_seq::type_id::create("str");
      mipi_corner_seq      cor = mipi_corner_seq::type_id::create("cor");
      nrm.num_txns=8; err.num_txns=4; b2b.num_txns=8; str.num_txns=8;
      nrm.start(m_sequencer); b2b.start(m_sequencer); cor.start(m_sequencer);
      str.start(m_sequencer); rst.start(m_sequencer); err.start(m_sequencer);
    endtask
  endclass

endpackage
`endif
