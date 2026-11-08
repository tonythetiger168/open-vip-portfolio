// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// dma_tests.svh -- DMA-UVM-VIP functional tests (included by dma_pkg.sv).
// Reference model: the spec's features (open-ip-portfolio specs/DMA.json):
//   COPY: DST word i = SRC word i; FILL: DST word i = FILLn, no reads;
//   CHECKSUM = 32-bit sum of the words written; queued channels are served
//   round robin from the channel after the last one served; DONEn per
//   channel, ERR when a job saw a non-OKAY response (the job still runs to
//   the end). With the kit's subordinate an errored read beat returns 0 and
//   an errored write beat leaves memory alone, so error jobs are predicted
//   word for word too.
/* TEST PLAN
- `dma_copy_test`: 40 COPY jobs on random channels: lengths 0, 1, 15, 16, 17,
  255 and random up to 600 words, addresses that start just below a 4 KB
  boundary or at random, four back-pressure settings. Checks every DST word,
  no write outside DST and no read outside SRC (address windows), CHECKSUM,
  STATUS.err = 0, the channel's DONE bit and nothing else, AXI ID 7, the
  burst rules, and that the IP read exactly LEN words and wrote LEN words.
- `dma_fill_test`: 24 FILL jobs: DST = FILL word, no read burst at all,
  CHECKSUM = LEN * FILL.
- `dma_rr_test`: all four channels queued with one CMD write (mixed COPY /
  FILL): served in the order 0, 1, 2, 3 (round robin after reset); then
  channels 1 and 3 queued after 3 was served: order 1, 3; then a channel queued
  while another runs. Order is taken from the AXI writes. STATUS.pending /
  busy seen while queued.
- `dma_err_test`: COPY from a SLVERR region (DST gets 0 for those words),
  COPY into a DECERR region (those words untouched), FILL across a SLVERR
  region: DONE + ERR, STATUS.err = 1, data as predicted; the next clean job
  clears STATUS.err.
*/

class dma_job_base_test extends dma_base_test;
  `uvm_component_utils(dma_job_base_test)
  int unsigned n_rd_before, n_wr_before;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function string ch_reg(string base, int ch);
    return $sformatf("%s%0d", base, ch);
  endfunction

  task set_mode(int ch, bit fill);
    uvm_status_e st;
    uvm_reg_field f = r("MODE").get_field_by_name($sformatf("mode%0d", ch));
    f.set(fill);
    r("MODE").update(st);
  endtask

  task program_ch(int ch, bit [31:0] src, bit [31:0] dst, int unsigned len, bit fill, bit [31:0] fillw);
    wr(ch_reg("SRC", ch), src);
    wr(ch_reg("DST", ch), dst);
    wr(ch_reg("LEN", ch), len);
    wr(ch_reg("FILL", ch), fillw);
    set_mode(ch, fill);
  endtask

  // expected DST words of a job given the memory as it is now
  function void predict(bit [31:0] src, bit [31:0] dst, int unsigned len, bit fill, bit [31:0] fillw,
                        ref bit [31:0] exp[$], output bit [31:0] sum, output bit err);
    exp.delete(); sum = 0; err = 0;
    for (int unsigned i = 0; i < len; i++) begin
      bit [31:0] w;
      if (fill) w = fillw;
      else if (env.axi_cfg.resp_for(src + 4 * i, 0) != AXI_OKAY) begin w = 0; err = 1; end
      else w = mem().rd32(src + 4 * i);
      if (env.axi_cfg.resp_for(dst + 4 * i, 1) != AXI_OKAY) err = 1;
      sum += w;
      exp.push_back(w);
    end
  endfunction

  // what DST should hold afterwards: errored write words keep their old value
  function void after_write(bit [31:0] dst, ref bit [31:0] exp[$]);
    foreach (exp[i])
      if (env.axi_cfg.resp_for(dst + 4 * i, 1) != AXI_OKAY) exp[i] = mem().rd32(dst + 4 * i);
  endfunction

  task one_job(int ch, bit [31:0] src, bit [31:0] dst, int unsigned len, bit fill, bit [31:0] fillw = 0);
    bit [31:0] exp[$], sum, st, v, cs; bit perr;
    int unsigned rd0 = env.axi.mon.n_rd, wr0 = env.axi.mon.n_wr;
    int unsigned rw0 = 0, ww0 = 0;
    string tag = $sformatf("ch%0d %s src=%08h dst=%08h len=%0d", ch, fill ? "FILL" : "COPY", src, dst, len);
    program_ch(ch, src, dst, len, fill, fillw);
    predict(src, dst, len, fill, fillw, exp, sum, perr);
    after_write(dst, exp);
    env.axi_cfg.clear_windows();
    if (!fill && len != 0) env.axi_cfg.add_window(src, src + 4 * len, 1, 0, "src");
    if (len != 0) env.axi_cfg.add_window(dst, dst + 4 * len, 0, 1, "dst");
    env.axi_cfg.check_windows = 1;
    env.axi.mon.clear();
    mem().clear_written();
    wr("IRQ_ENABLE", 32'h1F);
    wr("CMD", 32'h1 << ch);
    wait_irq(st, tag);
    sb_check(st[irq_bit($sformatf("DONE%0d", ch))], {tag, ": DONE not set"});
    sb_check(st[irq_bit("ERR")] == perr, $sformatf("%s: ERR=%0d, expected %0d", tag, st[irq_bit("ERR")], perr));
    sb_check((st & ~(32'h1 << irq_bit($sformatf("DONE%0d", ch))) & ~(32'h1 << irq_bit("ERR"))) == 0,
          $sformatf("%s: unexpected IRQ_STATUS %b", tag, st));
    clear_irq(st);
    clocks(4);
    check_words(dst, exp, tag);
    rd("CHECKSUM", cs);
    check_eq(cs, sum, {tag, " CHECKSUM"});
    rd_field("STATUS", "err", v);
    sb_check(v == perr, {tag, " STATUS.err"});
    rd_field("STATUS", "busy", v);
    sb_check(v == 0, {tag, " STATUS.busy after DONE"});
    rd_field("STATUS", "active_ch", v);
    sb_check(v == ch, {tag, " STATUS.active_ch"});
    sb_check(mem().written_outside(dst, dst + 4 * len) == 0, {tag, ": bytes written outside DST"});
    foreach (env.axi.mon.completed[i]) begin
      if (env.axi.mon.completed[i].write) ww0 += env.axi.mon.completed[i].beats();
      else rw0 += env.axi.mon.completed[i].beats();
    end
    sb_check(ww0 == len, $sformatf("%s: %0d words written, expected %0d", tag, ww0, len));
    sb_check(rw0 == (fill ? 0 : len), $sformatf("%s: %0d words read, expected %0d", tag, rw0, fill ? 0 : len));
    env.axi_cfg.check_windows = 0;
  endtask

endclass

// testlist: dma_copy_test 3
class dma_copy_test extends dma_job_base_test;
  `uvm_component_utils(dma_copy_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lens[$] = '{0, 1, 15, 16, 17, 255, 4};
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 40; i++) begin
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 600);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0001_0000, len);
      bit [31:0] dst = rand_addr(32'h2000_0000, 32'h0001_0000, len);
      backpressure(i);
      fill_random(src, len, w);
      one_job(i % 4, src, dst, len, 0);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: dma_fill_test 2
class dma_fill_test extends dma_job_base_test;
  `uvm_component_utils(dma_fill_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 24; i++) begin
      int unsigned len = (i == 0) ? 1 : (i == 1) ? 16 : $urandom_range(1, 400);
      backpressure(i);
      one_job($urandom_range(3), 32'h1000_0000, rand_addr(32'h3000_0000, 32'h0001_0000, len), len, 1, $urandom());
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: dma_rr_test 2
class dma_rr_test extends dma_job_base_test;
  `uvm_component_utils(dma_rr_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // channel of each write burst, in the order they completed
  function void order(ref int seq[$]);
    seq.delete();
    foreach (env.axi.mon.completed[i])
      if (env.axi.mon.completed[i].write) begin
        int ch = (env.axi.mon.completed[i].addr - 32'h4000_0000) >> 16;
        if (seq.size() == 0 || seq[$] != ch) seq.push_back(ch);
      end
  endfunction

  task queue_and_check(bit [3:0] chans, int exp_order[$], int unsigned len, bit mid_start = 0);
    bit [31:0] w[$], st, v; int seq[$]; bit [31:0] want = 0;
    env.axi.mon.clear();
    for (int ch = 0; ch < 4; ch++) if (chans[ch]) begin
      fill_random(32'h1000_0000 + (ch << 16), len, w);
      program_ch(ch, 32'h1000_0000 + (ch << 16), 32'h4000_0000 + (ch << 16), len, ch == 2, 32'hC0DE_0000 + ch);
      want |= 32'h1 << irq_bit($sformatf("DONE%0d", ch));
    end
    wr("IRQ_ENABLE", 32'h0);
    if (mid_start) begin
      wr("CMD", chans & 4'h1);        // channel 0 first, the others while it runs
      wr("CMD", chans & 4'hE);
    end else
      wr("CMD", chans);
    rd_field("STATUS", "busy", v);
    sb_check(v == 1, "STATUS.busy while channels are queued");
    rd_field("STATUS", "pending", v);
    sb_check(v != 0 || $countones(chans) == 1, "STATUS.pending empty right after queueing several channels");
    for (int unsigned n = 0; n < 200000; n++) begin
      rd("IRQ_STATUS", st);
      if ((st & want) == want) break;
      clocks(50);
    end
    sb_check((st & want) == want, $sformatf("not every DONE bit set: %b, want %b", st, want));
    clear_irq(st);
    order(seq);
    sb_check(seq.size() == exp_order.size(), $sformatf("%0d channels ran, expected %0d", seq.size(), exp_order.size()));
    foreach (exp_order[i])
      if (i < seq.size()) sb_check(seq[i] == exp_order[i], $sformatf("job %0d ran channel %0d, expected %0d", i, seq[i], exp_order[i]));
    for (int ch = 0; ch < 4; ch++) if (chans[ch]) begin
      bit [31:0] exp[$], sum; bit e;
      if (ch == 2) begin
        exp.delete();
        repeat (len) exp.push_back(32'hC0DE_0000 + ch);
      end else mem().get_words(32'h1000_0000 + (ch << 16), len, exp);
      check_words(32'h4000_0000 + (ch << 16), exp, $sformatf("ch%0d", ch));
    end
  endtask

  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.set_backpressure(80, 2);
    queue_and_check(4'hF, '{0, 1, 2, 3}, 64);
    queue_and_check(4'hA, '{1, 3}, 40);
    queue_and_check(4'h7, '{0, 1, 2}, 48, 1);
    phase.drop_objection(this);
  endtask
endclass

// testlist: dma_err_test 2
class dma_err_test extends dma_job_base_test;
  `uvm_component_utils(dma_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0100, 32'h1000_0140, AXI_SLVERR);   // inside the COPY source
    env.axi_cfg.add_err_region(32'h2000_0200, 32'h2000_0210, AXI_DECERR);   // inside the COPY destination
    env.axi_cfg.add_err_region(32'h3000_0400, 32'h3000_0480, AXI_SLVERR);   // inside the FILL destination
    fill_random(32'h1000_0000, 256, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hDEAD_0000 + i);
    one_job(0, 32'h1000_0000, 32'h2400_0000, 128, 0);              // read errors
    one_job(1, 32'h1000_0400, 32'h2000_0000, 160, 0);              // write errors
    one_job(2, 32'h0, 32'h3000_0300, 96, 1, 32'h5A5A_A5A5);        // FILL with write errors
    one_job(3, 32'h1000_0800, 32'h2800_0000, 50, 0);               // clean again: STATUS.err back to 0
    sb_check(env.axi.cov.c_resp.exists(AXI_SLVERR) && env.axi.cov.c_resp.exists(AXI_DECERR),
          "SLVERR and DECERR responses not both seen");
    phase.drop_objection(this);
  endtask
endclass
