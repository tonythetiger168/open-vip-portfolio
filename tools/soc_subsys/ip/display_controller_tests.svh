// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// display_controller_tests.svh -- Display_Controller-UVM-VIP functional tests
// (included by display_controller_pkg.sv).
// Reference model (open-ip-portfolio specs/Display_Controller.json features):
//   reads LEN RGBA8888 pixels (one per word) at SRC and sends them on
//   pix_valid / pix_data / pix_ready;
//   pix_hsync with the last pixel of each line (LINE_WORDS pixels; 0: every
//   pixel) and with the last pixel of the frame; pix_vsync with the last
//   pixel of the frame;
//   FRAME_CRC = CRC-32 (IEEE 802.3) of the pixels sent, bytes little-endian;
//   UNDERRUNS = clocks with pix_ready high, the frame not finished and no
//   pixel available.
// display_panel_sink plays the panel: it drives pix_ready (always, or with a
// random duty), takes every pixel with its sync flags, checks that a shown
// pixel is held until taken, and counts the underrun clocks itself.
// Frame geometry is LEN / LINE_WORDS, so any resolution works; the tests
// scan 1080p and 8K (7680-pixel) lines.
/* TEST PLAN
- `display_controller_scan_test`: 20 frames: LINE_WORDS 0, 1, 7, 640, 1920
  and 7680 (8K), frames of 1..3 lines plus a partial line; panel always
  ready, 70 % and 30 % ready; four AXI back-pressure settings. Every pixel in
  order, hsync / vsync on exactly the right pixels, FRAME_CRC, UNDERRUNS =
  the panel's own count, no AXI write at all, reads inside SRC only, AXI ID 4.
- `display_controller_err_test`: a frame read across a SLVERR region (those
  pixels arrive as 0 and enter the CRC as 0): DONE + ERR, STATUS.err; a clean
  frame clears it.
*/

class display_panel_sink extends uvm_component;
  `uvm_component_utils(display_panel_sink)
  virtual display_controller_pins_if pins;
  virtual ssv_apb_if apb;
  int unsigned ready_pct = 100;
  bit [31:0]   px[$];
  bit          hs[$], vs[$];
  bit [11:0]   cmd_addr;
  int          in_frame_from = -1;     // clock from which the frame counts underruns
  longint      cyc;
  int unsigned underruns;
  bit          frame_open;
  int unsigned hold_errors;
  int unsigned left;             // pixels of the frame still to take

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void arm(int unsigned n_pixels);
    px.delete(); hs.delete(); vs.delete();
    underruns = 0;
    left = n_pixels;
  endfunction

  task run_phase(uvm_phase phase);
    bit [32:0] shown; bit was_shown = 0;
    pins.pix_ready = 1;
    forever begin
      @(posedge pins.clk);
      cyc++;
      // the CMD write that starts the frame: the core sees it two edges later
      if (apb.psel && apb.penable && apb.pready && apb.pwrite && apb.paddr == cmd_addr && apb.pwdata[0])
        begin in_frame_from = cyc + 2; frame_open = 1; end
      if (was_shown && !(pins.pix_valid && {pins.pix_hsync, pins.pix_data} == shown))
        hold_errors++;
      was_shown = 0;
      if (pins.pix_valid && pins.pix_ready) begin
        px.push_back(pins.pix_data); hs.push_back(pins.pix_hsync); vs.push_back(pins.pix_vsync);
        if (left > 0) left--;
        if (left == 0) frame_open = 0;
      end else if (pins.pix_valid) begin
        was_shown = 1; shown = {pins.pix_hsync, pins.pix_data};
      end else if (pins.pix_ready && frame_open && cyc >= in_frame_from && left != 0)
        underruns++;
      @(negedge pins.clk);
      pins.pix_ready = axim_pct(ready_pct);
    end
  endtask
endclass

class display_controller_job_base_test extends display_controller_base_test;
  `uvm_component_utils(display_controller_job_base_test)
  display_panel_sink panel;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    panel = display_panel_sink::type_id::create("panel", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    panel.pins = pins; panel.apb = apb_vif;
    panel.cmd_addr = r("CMD").get_address();
  endfunction

  static function bit [31:0] crc32_words(bit [31:0] w[$]);
    bit [31:0] c = 32'hFFFF_FFFF;
    foreach (w[i])
      for (int b = 0; b < 4; b++) begin
        c ^= {24'h0, w[i][8*b +: 8]};
        for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
      end
    return ~c;
  endfunction

  task frame(string tag, bit [31:0] src, int unsigned len, int unsigned line_words);
    bit [31:0] in[$], exp[$], v; bit rerr;
    job_input(src, len, in, rerr);
    wr("LINE", line_words);
    panel.arm(len);
    run_job(tag, src, 0, len, exp, rerr);
    clocks(5);
    sb_check(panel.px.size() == len, $sformatf("%s: %0d pixels sent, LEN %0d", tag, panel.px.size(), len));
    foreach (in[i]) begin
      bit h = (line_words == 0) || (i % line_words == line_words - 1) || (i == len - 1);
      if (i >= panel.px.size()) break;
      if (panel.px[i] != in[i] || panel.hs[i] != h || panel.vs[i] != (i == len - 1)) begin
        sb_check(0, $sformatf("%s pixel %0d: %08h hs=%0d vs=%0d, expected %08h hs=%0d vs=%0d", tag, i,
                           panel.px[i], panel.hs[i], panel.vs[i], in[i], h, i == len - 1));
        break;
      end
      checks++;
    end
    rd("FRAME_CRC", v);
    check_eq(v, crc32_words(in), {tag, " FRAME_CRC"});
    rd("UNDERRUNS", v);
    check_eq(v, panel.underruns, {tag, " UNDERRUNS"});
    sb_check(panel.hold_errors == 0, $sformatf("%s: a pixel changed or vanished before pix_ready", tag));
  endtask
endclass

// testlist: display_controller_scan_test 3
class display_controller_scan_test extends display_controller_job_base_test;
  `uvm_component_utils(display_controller_scan_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lws[$] = '{0, 1, 7, 640, 1920, 7680};
    int unsigned rdy[$] = '{100, 70, 30};
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 20; i++) begin
      int unsigned lw = lws[i % lws.size()];
      int unsigned len = (lw >= 640) ? lw * $urandom_range(1, 2) + $urandom_range(1, lw - 1) : $urandom_range(1, 600);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0008_0000, len);
      backpressure(i);
      panel.ready_pct = rdy[i % 3];
      fill_random(src, len, w);
      frame($sformatf("frame %0d lw=%0d len=%0d ready=%0d%%", i, lw, len, panel.ready_pct), src, len, lw);
    end
    sb_check(env.axi.mon.n_wr == 0, "the display controller issued a write");
    phase.drop_objection(this);
  endtask
endclass

// testlist: display_controller_err_test 2
class display_controller_err_test extends display_controller_job_base_test;
  `uvm_component_utils(display_controller_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0080, 32'h1000_00C0, AXI_SLVERR);
    fill_random(32'h1000_0000, 512, w);
    frame("read error", 32'h1000_0000, 120, 40);
    frame("clean", 32'h1000_0400, 64, 16);
    phase.drop_objection(this);
  endtask
endclass
