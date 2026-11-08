// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// cpu_cluster_tests.svh -- CPU_Cluster-UVM-VIP functional tests (included by
// cpu_cluster_pkg.sv).
// Reference model (open-ip-portfolio specs/CPU_Cluster.json features):
//   pattern(i) = SEED ^ {~i[15:0], i[15:0]}, i = 0 .. LEN-1;
//   MODE 0 WRITE: DST word i = pattern(i), no reads;
//   MODE 1 CHECK: read SRC word i, compare with pattern(i); RESULT.mismatches
//     counts differences (saturating), RESULT.first_fail = index of the first;
//     MISMATCH interrupt when a difference was found; no writes;
//   MODE 2 / 3 COPY: DST word i = SRC word i.
/* TEST PLAN
- `cpu_cluster_write_check_test`: 24 rounds of WRITE a pattern, CHECK it back
  (0 mismatches, no MISMATCH interrupt), corrupt 1..5 random words by back
  door and CHECK again (mismatches and first_fail exact, MISMATCH set);
  lengths 1, 16, 17 and random up to 800 words; random seeds; addresses near
  4 KB boundaries; four back-pressure settings.
- `cpu_cluster_copy_test`: 24 COPY jobs (MODE 2 and 3): DST = SRC word for
  word, read / write counts, windows.
- `cpu_cluster_err_test`: WRITE into a DECERR region (words untouched), CHECK
  from a SLVERR region (those words read as 0 and mismatch), COPY with both:
  DONE + ERR, STATUS.err; a clean job clears it.
*/

class cpu_cluster_job_base_test extends cpu_cluster_base_test;
  `uvm_component_utils(cpu_cluster_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  static function bit [31:0] pattern(bit [31:0] seed, int unsigned i);
    bit [15:0] l = i[15:0];
    return seed ^ {~l, l};
  endfunction

  task write_job(string tag, bit [31:0] dst, int unsigned len, bit [31:0] seed);
    bit [31:0] exp[$];
    for (int unsigned i = 0; i < len; i++) exp.push_back(pattern(seed, i));
    wr("CTRL", 0); wr("SEED", seed);
    run_job(tag, 0, dst, len, exp, 0, 0);
  endtask

  task check_job(string tag, bit [31:0] src, int unsigned len, bit [31:0] seed);
    bit [31:0] in[$], exp[$], v, st; bit rerr; int unsigned mm = 0; int ff = -1;
    job_input(src, len, in, rerr);
    foreach (in[i]) if (in[i] != pattern(seed, i)) begin mm++; if (ff < 0) ff = i; end
    wr("CTRL", 1); wr("SEED", seed);
    wr("IRQ_ENABLE", 0);
    rd("IRQ_STATUS", st); clear_irq(st);
    run_job(tag, src, 0, len, exp, rerr, len);
    rd_field("RESULT", "mismatches", v);
    check_eq(v, (mm > 16'hFFFF) ? 16'hFFFF : mm, {tag, " RESULT.mismatches"});
    if (mm != 0) begin
      rd_field("RESULT", "first_fail", v);
      check_eq(v, ff, {tag, " RESULT.first_fail"});
    end
    st = job_irq_status;
    sb_check(st[irq_bit("MISMATCH")] == (mm != 0), $sformatf("%s: MISMATCH=%0d with %0d mismatches", tag,
                                                          st[irq_bit("MISMATCH")], mm));
  endtask

  task copy_job(string tag, bit [31:0] src, bit [31:0] dst, int unsigned len, bit [1:0] mode = 2);
    bit [31:0] in[$]; bit rerr;
    job_input(src, len, in, rerr);
    wr("CTRL", mode);
    run_job(tag, src, dst, len, in, rerr);
  endtask
endclass

// testlist: cpu_cluster_write_check_test 3
class cpu_cluster_write_check_test extends cpu_cluster_job_base_test;
  `uvm_component_utils(cpu_cluster_write_check_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lens[$] = '{1, 16, 17};
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 24; i++) begin
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 800);
      bit [31:0] seed = $urandom();
      bit [31:0] a = rand_addr(32'h2000_0000, 32'h0001_0000, len);
      backpressure(i);
      write_job($sformatf("write %0d len=%0d", i, len), a, len, seed);
      check_job($sformatf("check %0d clean", i), a, len, seed);
      repeat ($urandom_range(1, 5)) begin
        int unsigned k = $urandom_range(len - 1);
        mem().wr32(a + 4 * k, mem().rd32(a + 4 * k) ^ (32'h1 << $urandom_range(31)));
      end
      check_job($sformatf("check %0d corrupted", i), a, len, seed);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: cpu_cluster_copy_test 2
class cpu_cluster_copy_test extends cpu_cluster_job_base_test;
  `uvm_component_utils(cpu_cluster_copy_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 24; i++) begin
      int unsigned len = (i == 0) ? 1 : $urandom_range(1, 700);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0001_0000, len);
      bit [31:0] dst = rand_addr(32'h3000_0000, 32'h0001_0000, len);
      backpressure(i);
      fill_random(src, len, w);
      copy_job($sformatf("copy %0d len=%0d", i, len), src, dst, len, 2 + i % 2);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: cpu_cluster_err_test 2
class cpu_cluster_err_test extends cpu_cluster_job_base_test;
  `uvm_component_utils(cpu_cluster_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0140, AXI_DECERR);
    env.axi_cfg.add_err_region(32'h1000_0040, 32'h1000_0060, AXI_SLVERR);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hCAFE_0000 + i);
    write_job("write into DECERR", 32'h2000_0000, 128, 32'h0BAD_F00D);
    for (int i = 0; i < 64; i++) mem().wr32(32'h1000_0000 + 4 * i, pattern(32'h77, i));
    check_job("check from SLVERR", 32'h1000_0000, 64, 32'h77);
    fill_random(32'h1000_0000, 64, w);
    copy_job("copy both", 32'h1000_0000, 32'h2000_00C0, 64);
    copy_job("clean", 32'h1000_0400, 32'h2800_0000, 33);
    phase.drop_objection(this);
  endtask
endclass
