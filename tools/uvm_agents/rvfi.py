# RISC-V Formal Interface (RVFI, as used by riscv-formal) trace VIP for an
# RV32I core. The agent is the core's memory: it answers instruction
# fetches with the sequence's instructions (in stream order, whatever the
# fetch address) and serves loads and stores from its own memory. The
# monitor takes every retired instruction from the RVFI port and the
# scoreboard is an RV32I instruction-set simulator that checks each field.
#
# Memory ports (request held until acknowledged): i_req, i_addr / i_ack,
# i_rdata; d_req, d_we, d_addr (word aligned), d_wmask, d_wdata / d_ack,
# d_rdata. A word never written reads rvfi_mem_init(address).
#
# RVFI (NRET = 1, XLEN = 32): rvfi_valid, rvfi_order[63:0], rvfi_insn,
# rvfi_trap, rvfi_halt, rvfi_intr, rvfi_mode (3), rvfi_ixl (1),
# rvfi_rs1_addr / rs2_addr / rs1_rdata / rs2_rdata (0 when the instruction
# does not read the register), rvfi_rd_addr / rd_wdata (0 when nothing or x0
# is written), rvfi_pc_rdata / pc_wdata, rvfi_mem_addr (word aligned),
# rvfi_mem_rmask / wmask (byte lanes), rvfi_mem_rdata / wdata (the whole word;
# write-data bytes outside the mask are 0).
#
# tb/top_tb.sv rvfi_model: a multi-cycle RV32I core (fetch, execute, memory)
# starting at PC 0. Illegal instructions (including CSR, FENCE.I, bad
# funct3 / funct7 and shift amounts with bit 5), ECALL, EBREAK, a misaligned
# load / store address and a jump or taken branch to an address that is not
# 4-byte aligned trap: the instruction retires with rvfi_trap, no register or
# memory access reported, and pc_wdata = MTVEC (0x100). The next instruction
# retires with rvfi_intr. FENCE is a no-op.

RVFI_FUNCS = """
localparam bit [31:0] RVFI_MTVEC = 32'h0000_0100;
function automatic bit [31:0] rvfi_mem_init(bit [31:0] a);
  bit [31:0] w = {a[31:2], 2'b00};
  return (w * 32'h9E37_79B1) ^ 32'h5A5A_A5A5;
endfunction
// encoders
function automatic bit [31:0] rv_r(bit [6:0] f7, bit [4:0] rs2, bit [4:0] rs1, bit [2:0] f3, bit [4:0] rd, bit [6:0] op);
  return {f7, rs2, rs1, f3, rd, op};
endfunction
function automatic bit [31:0] rv_i(bit [11:0] imm, bit [4:0] rs1, bit [2:0] f3, bit [4:0] rd, bit [6:0] op);
  return {imm, rs1, f3, rd, op};
endfunction
function automatic bit [31:0] rv_s(bit [11:0] imm, bit [4:0] rs2, bit [4:0] rs1, bit [2:0] f3);
  return {imm[11:5], rs2, rs1, f3, imm[4:0], 7'h23};
endfunction
function automatic bit [31:0] rv_b(bit [12:0] imm, bit [4:0] rs2, bit [4:0] rs1, bit [2:0] f3);
  return {imm[12], imm[10:5], rs2, rs1, f3, imm[4:1], imm[11], 7'h63};
endfunction
function automatic bit [31:0] rv_j(bit [20:0] imm, bit [4:0] rd);
  return {imm[20], imm[10:1], imm[11], imm[19:12], rd, 7'h6F};
endfunction
"""

SPEC = dict(
    vip="RVFI-UVM-VIP", p="rvfi", P="RVFI", dir="rvfi", family="Processor",
    desc="RISC-V Formal Interface (RVFI) VIP for RV32I: instruction / data memory agent, retirement monitor and an "
         "instruction-set simulator scoreboard checking every RVFI field (order, registers, PC, memory masks, traps).",
    about="""
RVFI is the trace port RISC-V cores expose for riscv-formal: one record per
retired instruction with the registers it read and wrote, the PC before and
after and its memory access. This VIP uses it for simulation: the agent is
the core's instruction and data memory (random RV32I instruction streams,
loads served from its own memory), the monitor collects the retirement
records and the scoreboard steps an RV32I instruction-set simulator next to
the core, so a wrong ALU result, sign extension, byte lane, branch decision
or missed trap is reported at the instruction that causes it. The DUT model
is a small multi-cycle RV32I core.""",
    defs=RVFI_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "i_ack"), ("in", "logic [31:0]", "i_rdata"),
        ("in", "logic", "d_ack"), ("in", "logic [31:0]", "d_rdata"),
        ("out", "logic", "i_req"), ("out", "logic [31:0]", "i_addr"),
        ("out", "logic", "d_req"), ("out", "logic", "d_we"), ("out", "logic [31:0]", "d_addr"),
        ("out", "logic [3:0]", "d_wmask"), ("out", "logic [31:0]", "d_wdata"),
        ("out", "logic", "rvfi_valid"), ("out", "logic [63:0]", "rvfi_order"), ("out", "logic [31:0]", "rvfi_insn"),
        ("out", "logic", "rvfi_trap"), ("out", "logic", "rvfi_halt"), ("out", "logic", "rvfi_intr"),
        ("out", "logic [1:0]", "rvfi_mode"), ("out", "logic [1:0]", "rvfi_ixl"),
        ("out", "logic [4:0]", "rvfi_rs1_addr"), ("out", "logic [4:0]", "rvfi_rs2_addr"),
        ("out", "logic [31:0]", "rvfi_rs1_rdata"), ("out", "logic [31:0]", "rvfi_rs2_rdata"),
        ("out", "logic [4:0]", "rvfi_rd_addr"), ("out", "logic [31:0]", "rvfi_rd_wdata"),
        ("out", "logic [31:0]", "rvfi_pc_rdata"), ("out", "logic [31:0]", "rvfi_pc_wdata"),
        ("out", "logic [31:0]", "rvfi_mem_addr"), ("out", "logic [3:0]", "rvfi_mem_rmask"),
        ("out", "logic [3:0]", "rvfi_mem_wmask"), ("out", "logic [31:0]", "rvfi_mem_rdata"),
        ("out", "logic [31:0]", "rvfi_mem_wdata"),
    ],
    fields=[
        ("bit [31:0]", "insn", "req"),
        ("bit [63:0]", "order", "rsp"),
        ("bit", "trap", "rsp"),
        ("bit", "halt", "rsp"),
        ("bit", "intr", "rsp"),
        ("bit [1:0]", "mode", "rsp"),
        ("bit [1:0]", "ixl", "rsp"),
        ("bit [4:0]", "rs1_addr", "rsp"),
        ("bit [4:0]", "rs2_addr", "rsp"),
        ("bit [31:0]", "rs1_rdata", "rsp"),
        ("bit [31:0]", "rs2_rdata", "rsp"),
        ("bit [4:0]", "rd_addr", "rsp"),
        ("bit [31:0]", "rd_wdata", "rsp"),
        ("bit [31:0]", "pc_rdata", "rsp"),
        ("bit [31:0]", "pc_wdata", "rsp"),
        ("bit [31:0]", "mem_addr", "rsp"),
        ("bit [3:0]", "mem_rmask", "rsp"),
        ("bit [3:0]", "mem_wmask", "rsp"),
        ("bit [31:0]", "mem_rdata", "rsp"),
        ("bit [31:0]", "mem_wdata", "rsp"),
        ("bit [4:0]", "cls", "info", "rand"),
        ("bit [2:0]", "r_rd", "info", "rand"),
        ("bit [2:0]", "r_rs1", "info", "rand"),
        ("bit [2:0]", "r_rs2", "info", "rand"),
        ("bit [3:0]", "r_f", "info", "rand"),
        ("bit [31:0]", "r_imm", "info", "rand"),
        ("bit [1:0]", "lat", "info", "rand"),
    ],
    tr_functions="""
// an instruction of class cls; registers mostly x0..x7 so results are reused;
// loads / stores mostly off x0 (address = immediate, so alignment is chosen)
function void post_randomize();
  bit [4:0] rd = {2'b00, r_rd}, rs1 = {2'b00, r_rs1}, rs2 = {2'b00, r_rs2};
  bit [11:0] im = r_imm[11:0];
  bit [2:0] f3 = r_f[2:0];
  bit [2:0] alu [8] = '{3'd0, 3'd2, 3'd3, 3'd4, 3'd6, 3'd7, 3'd1, 3'd5};
  if (r_imm[31]) rd = r_imm[30:26];
  case (cls)
    0, 1, 2, 24, 25: begin                                  // OP-IMM
      f3 = alu[r_f[2:0]];
      if (f3 == 3'd1) im = {7'h00, im[4:0]};
      if (f3 == 3'd5) im = {r_f[3] ? 7'h20 : 7'h00, im[4:0]};
      insn = rv_i(im, rs1, f3, rd, 7'h13);
    end
    3, 4, 5, 26, 27: begin                                  // OP
      f3 = r_f[2:0];
      insn = rv_r((r_f[3] && (f3 == 3'd0 || f3 == 3'd5)) ? 7'h20 : 7'h00, rs2, rs1, f3, rd, 7'h33);
    end
    6: insn = {r_imm[31:12], rd, 7'h37};                     // LUI
    7: insn = {r_imm[31:12], rd, 7'h17};                     // AUIPC
    8: insn = rv_j({r_imm[20:2], r_f[0] & r_f[1], 1'b0}, rd); // JAL (target misaligned 1 in 4)
    9: insn = rv_i({im[11:2], r_f[0] & r_f[1], 1'b0}, r_f[2] ? rs1 : 5'd0, 3'd0, rd, 7'h67);  // JALR
    10, 11, 12: begin                                       // BRANCH
      f3 = (r_f[2:1] == 2'b01) ? {1'b0, 1'b0, r_f[0]} : r_f[2:0];
      insn = rv_b({r_imm[12:2], r_f[3] & r_imm[13], 1'b0}, rs2, rs1, f3);
    end
    13, 14, 15, 28, 29: begin                               // LOAD
      bit [2:0] lf [8] = '{3'd0, 3'd1, 3'd2, 3'd4, 3'd5, 3'd2, 3'd2, 3'd0};
      f3 = lf[r_f[2:0]];
      if (!r_f[3]) im = {4'h0, im[7:2], (f3[1:0] == 2'd2) ? 2'b00 : (f3[1:0] == 2'd1) ? {im[1], 1'b0} : im[1:0]};
      insn = rv_i(im, r_f[3] ? rs1 : 5'd0, f3, rd, 7'h03);
    end
    16, 17, 18, 30, 31: begin                               // STORE
      f3 = (r_f[1:0] == 2'd3) ? 3'd2 : {1'b0, r_f[1:0]};
      if (!r_f[3]) im = {4'h0, im[7:2], (f3 == 3'd2) ? 2'b00 : (f3 == 3'd1) ? {im[1], 1'b0} : im[1:0]};
      insn = rv_s(im, rs2, r_f[2] ? rs1 : 5'd0, f3);
    end
    19: insn = {4'h0, r_imm[27:20], 5'd0, 3'd0, 5'd0, 7'h0F};  // FENCE
    20: insn = 32'h0000_0073;                                // ECALL
    21: insn = 32'h0010_0073;                                // EBREAK
    22: insn = r_imm;                                        // anything
    default: insn = {r_imm[31:20], rs1, 3'd2, rd, 7'h73};    // CSRRS: not implemented
  endcase
endfunction
""",
    drv_rsp=False,
    drv_desc="instruction fetches answered with the item's instruction after lat clocks; a background responder serves loads and stores from the agent's memory",
    drv_members="bit [31:0] mem [bit [29:0]];",
    drv_idle="""
vif.drv_cb.i_ack   <= 1'b0;
vif.drv_cb.i_rdata <= 32'h0;
vif.drv_cb.d_ack   <= 1'b0;
vif.drv_cb.d_rdata <= 32'h0;
""",
    drv_bg="""
int unsigned n = 0;
forever begin
  @(vif.drv_cb);
  if (vif.drv_cb.d_req) begin
    bit [31:0] a = vif.drv_cb.d_addr, w;
    repeat (n % 3) @(vif.drv_cb);
    n++;
    w = mem.exists(a[31:2]) ? mem[a[31:2]] : rvfi_mem_init(a);
    if (vif.drv_cb.d_we) begin
      for (int i = 0; i < 4; i++) if (vif.drv_cb.d_wmask[i]) w[8*i +: 8] = vif.drv_cb.d_wdata[8*i +: 8];
      mem[a[31:2]] = w;
    end
    vif.drv_cb.d_ack <= 1'b1; vif.drv_cb.d_rdata <= w;
    @(vif.drv_cb);
    vif.drv_cb.d_ack <= 1'b0;
  end
end
""",
    drv_item="""
while (!vif.drv_cb.i_req) @(vif.drv_cb);
repeat (t.lat) @(vif.drv_cb);
vif.drv_cb.i_ack <= 1'b1; vif.drv_cb.i_rdata <= t.insn;
@(vif.drv_cb);
vif.drv_cb.i_ack <= 1'b0;
@(vif.drv_cb);
""",
    mon_desc="one item per rvfi_valid: the whole retirement record",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rvfi_valid) begin
    rvfi_transaction t = rvfi_transaction::type_id::create("t");
    t.insn = vif.mon_cb.rvfi_insn; t.order = vif.mon_cb.rvfi_order;
    t.trap = vif.mon_cb.rvfi_trap; t.halt = vif.mon_cb.rvfi_halt; t.intr = vif.mon_cb.rvfi_intr;
    t.mode = vif.mon_cb.rvfi_mode; t.ixl = vif.mon_cb.rvfi_ixl;
    t.rs1_addr = vif.mon_cb.rvfi_rs1_addr; t.rs2_addr = vif.mon_cb.rvfi_rs2_addr;
    t.rs1_rdata = vif.mon_cb.rvfi_rs1_rdata; t.rs2_rdata = vif.mon_cb.rvfi_rs2_rdata;
    t.rd_addr = vif.mon_cb.rvfi_rd_addr; t.rd_wdata = vif.mon_cb.rvfi_rd_wdata;
    t.pc_rdata = vif.mon_cb.rvfi_pc_rdata; t.pc_wdata = vif.mon_cb.rvfi_pc_wdata;
    t.mem_addr = vif.mon_cb.rvfi_mem_addr; t.mem_rmask = vif.mon_cb.rvfi_mem_rmask; t.mem_wmask = vif.mon_cb.rvfi_mem_wmask;
    t.mem_rdata = vif.mon_cb.rvfi_mem_rdata; t.mem_wdata = vif.mon_cb.rvfi_mem_wdata;
    publish(t);
  end
end
""",
    sb_members="""bit [31:0] x [32];
bit [31:0] pc = 0;
bit [63:0] ord = 0;
bit intr_n = 0;
bit [31:0] dmem [bit [29:0]];""",
    predict="""
// RV32I instruction-set simulator: one step per retired instruction
bit [31:0] i = t.insn, a, b, r = 0, npc, ea, w, sh;
bit [31:0] ii = {{20{i[31]}}, i[31:20]}, is = {{20{i[31]}}, i[31:25], i[11:7]};
bit [31:0] ib = {{19{i[31]}}, i[31], i[7], i[30:25], i[11:8], 1'b0};
bit [31:0] ij = {{11{i[31]}}, i[31], i[19:12], i[20], i[30:21], 1'b0};
bit [4:0] rd = i[11:7], rs1 = i[19:15], rs2 = i[24:20];
bit [2:0] f3 = i[14:12];
bit [6:0] f7 = i[31:25];
bit trap = 0, wr = 0, u1 = 0, u2 = 0, ld = 0, st = 0, tk = 0;
bit [3:0] m = 0;
x[0] = 0;
a = x[rs1]; b = x[rs2];
npc = pc + 4;
t.order = ord; t.pc_rdata = pc; t.intr = intr_n; t.halt = 0; t.mode = 2'd3; t.ixl = 2'd1;
t.mem_addr = 0; t.mem_rmask = 0; t.mem_wmask = 0; t.mem_rdata = 0; t.mem_wdata = 0;
case (i[6:0])
  7'h37: begin wr = 1; r = {i[31:12], 12'h0}; end
  7'h17: begin wr = 1; r = pc + {i[31:12], 12'h0}; end
  7'h6F: begin wr = 1; r = pc + 4; npc = pc + ij; trap = npc[1]; end
  7'h67: begin
    u1 = 1; wr = 1; r = pc + 4; npc = (a + ii) & ~32'h1;
    trap = (f3 != 0) || npc[1];
  end
  7'h63: begin
    u1 = 1; u2 = 1;
    case (f3)
      3'd0: tk = (a == b);
      3'd1: tk = (a != b);
      3'd4: tk = ($signed(a) < $signed(b));
      3'd5: tk = ($signed(a) >= $signed(b));
      3'd6: tk = (a < b);
      3'd7: tk = (a >= b);
      default: trap = 1;
    endcase
    if (tk) npc = pc + ib;
    if (tk && npc[1]) trap = 1;
  end
  7'h03: begin
    u1 = 1; wr = 1; ld = 1; ea = a + ii;
    if (f3 == 3 || f3 > 5) trap = 1;
    else if ((f3[1:0] == 1 && ea[0]) || (f3[1:0] == 2 && ea[1:0] != 0)) trap = 1;
    m = ((f3[1:0] == 0) ? 4'h1 : (f3[1:0] == 1) ? 4'h3 : 4'hF) << ea[1:0];
    w = dmem.exists(ea[31:2]) ? dmem[ea[31:2]] : rvfi_mem_init(ea);
    sh = w >> (8 * ea[1:0]);
    case (f3)
      3'd0: r = {{24{sh[7]}}, sh[7:0]};
      3'd1: r = {{16{sh[15]}}, sh[15:0]};
      3'd4: r = {24'h0, sh[7:0]};
      3'd5: r = {16'h0, sh[15:0]};
      default: r = sh;
    endcase
  end
  7'h23: begin
    u1 = 1; u2 = 1; st = 1; ea = a + is;
    if (f3 > 2) trap = 1;
    else if ((f3 == 1 && ea[0]) || (f3 == 2 && ea[1:0] != 0)) trap = 1;
    m = ((f3 == 0) ? 4'h1 : (f3 == 1) ? 4'h3 : 4'hF) << ea[1:0];
  end
  7'h13: begin
    u1 = 1; wr = 1;
    case (f3)
      3'd0: r = a + ii;
      3'd2: r = ($signed(a) < $signed(ii)) ? 1 : 0;
      3'd3: r = (a < ii) ? 1 : 0;
      3'd4: r = a ^ ii;
      3'd6: r = a | ii;
      3'd7: r = a & ii;
      3'd1: begin r = a << i[24:20]; trap = (f7 != 0); end
      3'd5: begin
        if (f7[5]) r = $signed(a) >>> i[24:20]; else r = a >> i[24:20];
        trap = (f7 != 0 && f7 != 7'h20);
      end
    endcase
  end
  7'h33: begin
    u1 = 1; u2 = 1; wr = 1;
    trap = !(f7 == 0 || (f7 == 7'h20 && (f3 == 0 || f3 == 5)));
    case (f3)
      3'd0: r = f7[5] ? a - b : a + b;
      3'd1: r = a << b[4:0];
      3'd2: r = ($signed(a) < $signed(b)) ? 1 : 0;
      3'd3: r = (a < b) ? 1 : 0;
      3'd4: r = a ^ b;
      3'd5: if (f7[5]) r = $signed(a) >>> b[4:0]; else r = a >> b[4:0];
      3'd6: r = a | b;
      3'd7: r = a & b;
    endcase
  end
  7'h0F: trap = (f3 != 0);
  default: trap = 1;                                   // ECALL, EBREAK, CSR, unknown
endcase
if (trap) begin
  npc = RVFI_MTVEC;
  t.rs1_addr = 0; t.rs1_rdata = 0; t.rs2_addr = 0; t.rs2_rdata = 0; t.rd_addr = 0; t.rd_wdata = 0;
end else begin
  t.rs1_addr = u1 ? rs1 : 0; t.rs1_rdata = u1 ? a : 0;
  t.rs2_addr = u2 ? rs2 : 0; t.rs2_rdata = u2 ? b : 0;
  t.rd_addr = (wr && rd != 0) ? rd : 0;
  t.rd_wdata = (wr && rd != 0) ? r : 0;
  if (ld) begin t.mem_addr = {ea[31:2], 2'b00}; t.mem_rmask = m; t.mem_rdata = w; end
  if (st) begin
    t.mem_addr = {ea[31:2], 2'b00}; t.mem_wmask = m;
    w = dmem.exists(ea[31:2]) ? dmem[ea[31:2]] : rvfi_mem_init(ea);
    for (int k = 0; k < 4; k++) if (m[k]) begin
      t.mem_wdata[8*k +: 8] = b[8*(k - ea[1:0]) +: 8];
      w[8*k +: 8] = b[8*(k - ea[1:0]) +: 8];
    end
    dmem[ea[31:2]] = w;
  end
  if (wr && rd != 0) x[rd] = r;
end
t.trap = trap;
t.pc_wdata = npc;
pc = npc; ord++; intr_n = trap;
""",
    checks="""
if (t.trap && (t.rd_addr != 0 || t.mem_rmask != 0 || t.mem_wmask != 0)) fail(t, "trapped instruction reports a register or memory access");
if (t.rd_addr == 0 && t.rd_wdata != 0) fail(t, "rd_wdata nonzero without rd");
""",
    coverage="""
cp_op : coverpoint tr.insn[6:0] { bins lui = {7'h37}; bins auipc = {7'h17}; bins jal = {7'h6F}; bins jalr = {7'h67};
                                  bins branch = {7'h63}; bins load = {7'h03}; bins store = {7'h23}; bins op_imm = {7'h13};
                                  bins op = {7'h33}; bins fence = {7'h0F}; bins system = {7'h73}; }
cp_trap : coverpoint tr.trap;
cp_intr : coverpoint tr.intr;
cp_taken : coverpoint (tr.pc_wdata != tr.pc_rdata + 4) iff (tr.insn[6:0] == 7'h63 && !tr.trap);
cp_lsize : coverpoint tr.mem_rmask iff (tr.mem_rmask != 0) { bins b[] = {4'h1, 4'h2, 4'h4, 4'h8}; bins h[] = {4'h3, 4'hC}; bins w = {4'hF}; }
cp_ssize : coverpoint tr.mem_wmask iff (tr.mem_wmask != 0) { bins b[] = {4'h1, 4'h2, 4'h4, 4'h8}; bins h[] = {4'h3, 4'hC}; bins w = {4'hF}; }
cp_alu : coverpoint tr.insn[14:12] iff ((tr.insn[6:0] == 7'h33 || tr.insn[6:0] == 7'h13) && !tr.trap);
x_op_trap : cross cp_op, cp_trap { ignore_bins ok_sys = binsof(cp_op.system) && binsof(cp_trap) intersect {0};
                                   ignore_bins lui_trap = binsof(cp_op) intersect {7'h37, 7'h17} && binsof(cp_trap) intersect {1}; }
""",
    directed="""
// a short program with known results, then traps of every kind
bit [31:0] p [$] = '{
  32'h1234_50B7,                         // lui   x1, 0x12345
  rv_i(12'h678, 5'd1, 3'd0, 5'd1, 7'h13), // addi  x1, x1, 0x678
  rv_i(12'hFFF, 5'd0, 3'd0, 5'd2, 7'h13), // addi  x2, x0, -1
  rv_s(12'h040, 5'd1, 5'd0, 3'd2),        // sw    x1, 0x40(x0)
  rv_i(12'h040, 5'd0, 3'd2, 5'd3, 7'h03), // lw    x3, 0x40(x0)
  rv_i(12'h041, 5'd0, 3'd0, 5'd4, 7'h03), // lb    x4, 0x41(x0)
  rv_i(12'h043, 5'd0, 3'd4, 5'd5, 7'h03), // lbu   x5, 0x43(x0)
  rv_i(12'h042, 5'd0, 3'd1, 5'd6, 7'h03), // lh    x6, 0x42(x0)
  rv_s(12'h045, 5'd2, 5'd0, 3'd0),        // sb    x2, 0x45(x0)
  rv_i(12'h044, 5'd0, 3'd5, 5'd7, 7'h03), // lhu   x7, 0x44(x0)
  rv_s(12'h046, 5'd1, 5'd0, 3'd1),        // sh    x1, 0x46(x0)
  rv_i(12'h044, 5'd0, 3'd2, 5'd7, 7'h03), // lw    x7, 0x44(x0)
  rv_r(7'h20, 5'd1, 5'd3, 3'd0, 5'd4, 7'h33), // sub x4, x3, x1
  rv_b(13'h008, 5'd0, 5'd4, 3'd0),        // beq   x4, x0, +8 (taken)
  rv_b(13'h008, 5'd0, 5'd4, 3'd1),        // bne   x4, x0, +8 (not taken)
  rv_i(12'h404, 5'd2, 3'd5, 5'd5, 7'h13), // srai  x5, x2, 4
  rv_j(21'h00C, 5'd6),                    // jal   x6, +12
  rv_i(12'h080, 5'd0, 3'd0, 5'd7, 7'h67), // jalr  x7, 0x80(x0)
  rv_i(12'h042, 5'd0, 3'd2, 5'd3, 7'h03), // lw    x3, 0x42(x0): misaligned
  rv_s(12'h041, 5'd1, 5'd0, 3'd1),        // sh    x1, 0x41(x0): misaligned
  rv_j(21'h006, 5'd1),                    // jal   x1, +6: misaligned target
  rv_i(12'h082, 5'd0, 3'd0, 5'd1, 7'h67), // jalr  x1, 0x82(x0): misaligned target
  32'h0000_0073, 32'h0010_0073,           // ecall, ebreak
  rv_i(12'h024, 5'd1, 3'd1, 5'd1, 7'h13), // slli with shamt bit 5: illegal
  rv_r(7'h01, 5'd1, 5'd1, 3'd0, 5'd1, 7'h33), // mul: not RV32I
  32'h3000_2073,                          // csrr mstatus: not implemented
  32'h0000_100F,                          // fence.i: not implemented
  32'h0FF0_000F,                          // fence
  rv_i(12'h000, 5'd0, 3'd0, 5'd0, 7'h13)  // nop
};
foreach (p[k]) begin t = item(); t.insn = p[k]; send(t); end
""",
    drain_ns=2000,
    model="""
module rvfi_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        i_ack,
  input  logic [31:0] i_rdata,
  input  logic        d_ack,
  input  logic [31:0] d_rdata,
  output logic        i_req,
  output logic [31:0] i_addr,
  output logic        d_req,
  output logic        d_we,
  output logic [31:0] d_addr,
  output logic [3:0]  d_wmask,
  output logic [31:0] d_wdata,
  output logic        rvfi_valid,
  output logic [63:0] rvfi_order,
  output logic [31:0] rvfi_insn,
  output logic        rvfi_trap,
  output logic        rvfi_halt,
  output logic        rvfi_intr,
  output logic [1:0]  rvfi_mode,
  output logic [1:0]  rvfi_ixl,
  output logic [4:0]  rvfi_rs1_addr,
  output logic [4:0]  rvfi_rs2_addr,
  output logic [31:0] rvfi_rs1_rdata,
  output logic [31:0] rvfi_rs2_rdata,
  output logic [4:0]  rvfi_rd_addr,
  output logic [31:0] rvfi_rd_wdata,
  output logic [31:0] rvfi_pc_rdata,
  output logic [31:0] rvfi_pc_wdata,
  output logic [31:0] rvfi_mem_addr,
  output logic [3:0]  rvfi_mem_rmask,
  output logic [3:0]  rvfi_mem_wmask,
  output logic [31:0] rvfi_mem_rdata,
  output logic [31:0] rvfi_mem_wdata
);
  localparam logic [31:0] MTVEC = 32'h0000_0100;
  localparam logic [1:0]  S_FETCH = 2'd0, S_EXEC = 2'd1, S_MEM = 2'd2;

  logic [31:0] x [0:31];
  logic [31:0] pc, ir;
  logic [1:0]  state;
  logic [63:0] ord;
  logic        intr_n;
  logic [4:0]  l_rd;          // pending load: destination, funct3, byte offset
  logic [2:0]  l_f3;
  logic [1:0]  l_off;
  logic        l_ld;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int k = 0; k < 32; k++) x[k] <= 32'h0;
      pc <= 32'h0; ir <= 32'h0; state <= S_FETCH; ord <= 64'h0; intr_n <= 1'b0;
      l_rd <= '0; l_f3 <= '0; l_off <= '0; l_ld <= 1'b0;
      i_req <= 1'b0; i_addr <= 32'h0; d_req <= 1'b0; d_we <= 1'b0; d_addr <= 32'h0; d_wmask <= 4'h0; d_wdata <= 32'h0;
      rvfi_valid <= 1'b0; rvfi_order <= '0; rvfi_insn <= '0; rvfi_trap <= 1'b0; rvfi_halt <= 1'b0; rvfi_intr <= 1'b0;
      rvfi_mode <= 2'd3; rvfi_ixl <= 2'd1; rvfi_rs1_addr <= '0; rvfi_rs2_addr <= '0; rvfi_rs1_rdata <= '0;
      rvfi_rs2_rdata <= '0; rvfi_rd_addr <= '0; rvfi_rd_wdata <= '0; rvfi_pc_rdata <= '0; rvfi_pc_wdata <= '0;
      rvfi_mem_addr <= '0; rvfi_mem_rmask <= '0; rvfi_mem_wmask <= '0; rvfi_mem_rdata <= '0; rvfi_mem_wdata <= '0;
    end else begin
      rvfi_valid <= 1'b0;
      case (state)
        S_FETCH: begin
          i_req <= 1'b1; i_addr <= pc;
          if (i_req && i_ack) begin ir <= i_rdata; i_req <= 1'b0; state <= S_EXEC; end
        end
        S_EXEC: begin : exec
          logic [31:0] i, a, b, r, npc, ea, ii, is, ib, ij, wd;
          logic [4:0]  rd, rs1, rs2;
          logic [2:0]  f3;
          logic [6:0]  f7;
          logic        trap, wr, u1, u2, ld, st, tk;
          logic [3:0]  m;
          i = ir;
          rd = i[11:7]; rs1 = i[19:15]; rs2 = i[24:20]; f3 = i[14:12]; f7 = i[31:25];
          ii = {{20{i[31]}}, i[31:20]};
          is = {{20{i[31]}}, i[31:25], i[11:7]};
          ib = {{19{i[31]}}, i[31], i[7], i[30:25], i[11:8], 1'b0};
          ij = {{11{i[31]}}, i[31], i[19:12], i[20], i[30:21], 1'b0};
          a = (rs1 == 5'd0) ? 32'h0 : x[rs1];
          b = (rs2 == 5'd0) ? 32'h0 : x[rs2];
          trap = 1'b0; wr = 1'b0; u1 = 1'b0; u2 = 1'b0; ld = 1'b0; st = 1'b0; tk = 1'b0;
          r = 32'h0; ea = 32'h0; m = 4'h0; wd = 32'h0;
          npc = pc + 32'd4;
          case (i[6:0])
            7'h37: begin wr = 1'b1; r = {i[31:12], 12'h0}; end
            7'h17: begin wr = 1'b1; r = pc + {i[31:12], 12'h0}; end
            7'h6F: begin wr = 1'b1; r = pc + 32'd4; npc = pc + ij; trap = npc[1]; end
            7'h67: begin
              u1 = 1'b1; wr = 1'b1; r = pc + 32'd4; npc = (a + ii) & ~32'h1;
              trap = (f3 != 3'd0) || npc[1];
            end
            7'h63: begin
              u1 = 1'b1; u2 = 1'b1;
              case (f3)
                3'd0: tk = (a == b);
                3'd1: tk = (a != b);
                3'd4: tk = ($signed(a) < $signed(b));
                3'd5: tk = ($signed(a) >= $signed(b));
                3'd6: tk = (a < b);
                3'd7: tk = (a >= b);
                default: trap = 1'b1;
              endcase
              if (tk) npc = pc + ib;
              if (tk && npc[1]) trap = 1'b1;
            end
            7'h03: begin
              u1 = 1'b1; wr = 1'b1; ld = 1'b1; ea = a + ii;
              if (f3 == 3'd3 || f3 > 3'd5) trap = 1'b1;
              else if ((f3[1:0] == 2'd1 && ea[0]) || (f3[1:0] == 2'd2 && ea[1:0] != 2'd0)) trap = 1'b1;
              m = ((f3[1:0] == 2'd0) ? 4'h1 : (f3[1:0] == 2'd1) ? 4'h3 : 4'hF) << ea[1:0];
            end
            7'h23: begin
              u1 = 1'b1; u2 = 1'b1; st = 1'b1; ea = a + is;
              if (f3 > 3'd2) trap = 1'b1;
              else if ((f3 == 3'd1 && ea[0]) || (f3 == 3'd2 && ea[1:0] != 2'd0)) trap = 1'b1;
              m = ((f3 == 3'd0) ? 4'h1 : (f3 == 3'd1) ? 4'h3 : 4'hF) << ea[1:0];
              wd = b << (8 * ea[1:0]);
              for (int k = 0; k < 4; k++) if (!m[k]) wd[8*k +: 8] = 8'h00;
            end
            7'h13: begin
              u1 = 1'b1; wr = 1'b1;
              case (f3)
                3'd0: r = a + ii;
                3'd2: r = ($signed(a) < $signed(ii)) ? 32'd1 : 32'd0;
                3'd3: r = (a < ii) ? 32'd1 : 32'd0;
                3'd4: r = a ^ ii;
                3'd6: r = a | ii;
                3'd7: r = a & ii;
                3'd1: begin r = a << i[24:20]; trap = (f7 != 7'h00); end
                default: begin
                  if (f7[5]) r = $signed(a) >>> i[24:20]; else r = a >> i[24:20];
                  trap = (f7 != 7'h00 && f7 != 7'h20);
                end
              endcase
            end
            7'h33: begin
              u1 = 1'b1; u2 = 1'b1; wr = 1'b1;
              trap = !(f7 == 7'h00 || (f7 == 7'h20 && (f3 == 3'd0 || f3 == 3'd5)));
              case (f3)
                3'd0: r = f7[5] ? a - b : a + b;
                3'd1: r = a << b[4:0];
                3'd2: r = ($signed(a) < $signed(b)) ? 32'd1 : 32'd0;
                3'd3: r = (a < b) ? 32'd1 : 32'd0;
                3'd4: r = a ^ b;
                3'd5: if (f7[5]) r = $signed(a) >>> b[4:0]; else r = a >> b[4:0];
                3'd6: r = a | b;
                default: r = a & b;
              endcase
            end
            7'h0F: trap = (f3 != 3'd0);
            default: trap = 1'b1;
          endcase
          rvfi_order <= ord; rvfi_insn <= i; rvfi_pc_rdata <= pc; rvfi_intr <= intr_n; rvfi_trap <= trap;
          rvfi_mem_addr <= 32'h0; rvfi_mem_rmask <= 4'h0; rvfi_mem_wmask <= 4'h0; rvfi_mem_rdata <= 32'h0; rvfi_mem_wdata <= 32'h0;
          if (trap) begin
            npc = MTVEC;
            rvfi_rs1_addr <= 5'd0; rvfi_rs1_rdata <= 32'h0; rvfi_rs2_addr <= 5'd0; rvfi_rs2_rdata <= 32'h0;
            rvfi_rd_addr <= 5'd0; rvfi_rd_wdata <= 32'h0;
          end else begin
            rvfi_rs1_addr <= u1 ? rs1 : 5'd0; rvfi_rs1_rdata <= u1 ? a : 32'h0;
            rvfi_rs2_addr <= u2 ? rs2 : 5'd0; rvfi_rs2_rdata <= u2 ? b : 32'h0;
            rvfi_rd_addr <= (wr && rd != 5'd0) ? rd : 5'd0;
            rvfi_rd_wdata <= (wr && rd != 5'd0) ? r : 32'h0;
          end
          rvfi_pc_wdata <= npc;
          if (!trap && (ld || st)) begin
            d_req <= 1'b1; d_we <= st; d_addr <= {ea[31:2], 2'b00}; d_wmask <= st ? m : 4'h0; d_wdata <= wd;
            rvfi_mem_addr <= {ea[31:2], 2'b00};
            if (ld) rvfi_mem_rmask <= m;
            else begin rvfi_mem_wmask <= m; rvfi_mem_wdata <= wd; end
            l_rd <= rd; l_f3 <= f3; l_off <= ea[1:0]; l_ld <= ld;
            state <= S_MEM;
          end else begin
            if (!trap && wr && rd != 5'd0) x[rd] <= r;
            rvfi_valid <= 1'b1;
            pc <= npc; ord <= ord + 64'd1; intr_n <= trap;
            state <= S_FETCH;
          end
        end
        default: begin                                      // S_MEM
          if (d_req && d_ack) begin : mem_done
            logic [31:0] sh, r;
            d_req <= 1'b0; d_we <= 1'b0;
            sh = d_rdata >> (8 * l_off);
            case (l_f3)
              3'd0: r = {{24{sh[7]}}, sh[7:0]};
              3'd1: r = {{16{sh[15]}}, sh[15:0]};
              3'd4: r = {24'h0, sh[7:0]};
              3'd5: r = {16'h0, sh[15:0]};
              default: r = sh;
            endcase
            if (l_ld) begin
              rvfi_mem_rdata <= d_rdata;
              if (l_rd != 5'd0) begin x[l_rd] <= r; rvfi_rd_wdata <= r; end
            end
            rvfi_valid <= 1'b1;
            pc <= pc + 32'd4; ord <= ord + 64'd1; intr_n <= 1'b0;
            state <= S_FETCH;
          end
        end
      endcase
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({i_req, d_req, rvfi_valid}))
  else $error("RVFI: X on a request or rvfi_valid");
assert property (@(posedge clk) disable iff (!rst_n) rvfi_valid |-> !$isunknown({rvfi_insn, rvfi_pc_rdata, rvfi_pc_wdata, rvfi_rd_wdata}))
  else $error("RVFI: X in a retirement record");
// one memory request at a time, held until acknowledged
assert property (@(posedge clk) disable iff (!rst_n) !(i_req && d_req))
  else $error("RVFI: fetch and data request together");
assert property (@(posedge clk) disable iff (!rst_n) d_req && !d_ack |=> d_req && $stable(d_addr))
  else $error("RVFI: data request dropped or changed before its acknowledge");
cover property (@(posedge clk) disable iff (!rst_n) rvfi_valid && rvfi_trap);
cover property (@(posedge clk) disable iff (!rst_n) rvfi_valid && rvfi_intr);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic i_ack = 1'b0, d_ack = 1'b0;
logic [31:0] i_rdata = 32'h0, d_rdata = 32'h0;
wire i_req, d_req, d_we;
wire [31:0] i_addr, d_addr, d_wdata;
wire [3:0] d_wmask;
wire rvfi_valid, rvfi_trap, rvfi_halt, rvfi_intr;
wire [63:0] rvfi_order;
wire [31:0] rvfi_insn, rvfi_rs1_rdata, rvfi_rs2_rdata, rvfi_rd_wdata, rvfi_pc_rdata, rvfi_pc_wdata;
wire [31:0] rvfi_mem_addr, rvfi_mem_rdata, rvfi_mem_wdata;
wire [1:0] rvfi_mode, rvfi_ixl;
wire [4:0] rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rd_addr;
wire [3:0] rvfi_mem_rmask, rvfi_mem_wmask;

always #5 clk = ~clk;

rvfi_model u_dut (.clk(clk), .rst_n(rst_n), .i_ack(i_ack), .i_rdata(i_rdata), .d_ack(d_ack), .d_rdata(d_rdata),
  .i_req(i_req), .i_addr(i_addr), .d_req(d_req), .d_we(d_we), .d_addr(d_addr), .d_wmask(d_wmask), .d_wdata(d_wdata),
  .rvfi_valid(rvfi_valid), .rvfi_order(rvfi_order), .rvfi_insn(rvfi_insn), .rvfi_trap(rvfi_trap), .rvfi_halt(rvfi_halt),
  .rvfi_intr(rvfi_intr), .rvfi_mode(rvfi_mode), .rvfi_ixl(rvfi_ixl), .rvfi_rs1_addr(rvfi_rs1_addr),
  .rvfi_rs2_addr(rvfi_rs2_addr), .rvfi_rs1_rdata(rvfi_rs1_rdata), .rvfi_rs2_rdata(rvfi_rs2_rdata),
  .rvfi_rd_addr(rvfi_rd_addr), .rvfi_rd_wdata(rvfi_rd_wdata), .rvfi_pc_rdata(rvfi_pc_rdata),
  .rvfi_pc_wdata(rvfi_pc_wdata), .rvfi_mem_addr(rvfi_mem_addr), .rvfi_mem_rmask(rvfi_mem_rmask),
  .rvfi_mem_wmask(rvfi_mem_wmask), .rvfi_mem_rdata(rvfi_mem_rdata), .rvfi_mem_wdata(rvfi_mem_wdata));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// encoders
function automatic logic [31:0] I(input integer imm, input integer rs1, input integer f3, input integer rd, input logic [6:0] op);
  I = {imm[11:0], rs1[4:0], f3[2:0], rd[4:0], op};
endfunction
function automatic logic [31:0] R(input logic [6:0] f7, input integer rs2, input integer rs1, input integer f3, input integer rd);
  R = {f7, rs2[4:0], rs1[4:0], f3[2:0], rd[4:0], 7'h33};
endfunction
function automatic logic [31:0] S(input integer imm, input integer rs2, input integer rs1, input integer f3);
  S = {imm[11:5], rs2[4:0], rs1[4:0], f3[2:0], imm[4:0], 7'h23};
endfunction
function automatic logic [31:0] B(input integer imm, input integer rs2, input integer rs1, input integer f3);
  B = {imm[12], imm[10:5], rs2[4:0], rs1[4:0], f3[2:0], imm[4:1], imm[11], 7'h63};
endfunction
function automatic logic [31:0] J(input integer imm, input integer rd);
  J = {imm[20], imm[10:1], imm[11], imm[19:12], rd[4:0], 7'h6F};
endfunction

// memories: program (by word address) and data (zero at reset)
logic [31:0] im [0:255];
logic [31:0] dm [0:63];
integer lat = 0;
always @(posedge clk) begin
  i_ack <= 1'b0; d_ack <= 1'b0;
  if (i_req && !i_ack) begin
    if (lat == 0) begin i_ack <= 1'b1; i_rdata <= im[i_addr[9:2]]; lat <= 2; end
    else lat <= lat - 1;
  end
  if (d_req && !d_ack) begin
    d_ack <= 1'b1;
    d_rdata <= dm[d_addr[7:2]];
    if (d_we) for (int k = 0; k < 4; k++) if (d_wmask[k]) dm[d_addr[7:2]][8*k +: 8] <= d_wdata[8*k +: 8];
  end
end

// retirement records
logic [31:0] r_pc [0:127], r_pcw [0:127], r_wd [0:127], r_ma [0:127], r_mr [0:127], r_mw [0:127], r_r1 [0:127], r_r2 [0:127];
logic [4:0]  r_rd [0:127], r_a1 [0:127], r_a2 [0:127];
logic [3:0]  r_rm [0:127], r_wm [0:127];
logic        r_tr [0:127], r_in [0:127], r_ok [0:127];
logic [63:0] r_or [0:127];
integer nr = 0, both = 0;
always @(posedge clk) if (rst_n && i_req && d_req) both = both + 1;
always @(posedge clk) if (rvfi_valid && nr < 128) begin
  r_pc[nr] = rvfi_pc_rdata; r_pcw[nr] = rvfi_pc_wdata; r_wd[nr] = rvfi_rd_wdata; r_rd[nr] = rvfi_rd_addr;
  r_ma[nr] = rvfi_mem_addr; r_mr[nr] = rvfi_mem_rdata; r_mw[nr] = rvfi_mem_wdata; r_rm[nr] = rvfi_mem_rmask;
  r_wm[nr] = rvfi_mem_wmask; r_tr[nr] = rvfi_trap; r_in[nr] = rvfi_intr; r_or[nr] = rvfi_order;
  r_ok[nr] = (rvfi_halt === 1'b0 && rvfi_mode === 2'd3 && rvfi_ixl === 2'd1);
  r_a1[nr] = rvfi_rs1_addr; r_a2[nr] = rvfi_rs2_addr; r_r1[nr] = rvfi_rs1_rdata; r_r2[nr] = rvfi_rs2_rdata;
  nr = nr + 1;
end

// record k: PC, next PC, rd and its value, trap
function automatic logic rec(input integer k, input logic [31:0] pc, input logic [31:0] pcw, input integer rd,
                             input logic [31:0] wd, input logic tr);
  rec = k < nr && r_pc[k] == pc && r_pcw[k] == pcw && r_rd[k] == rd && r_wd[k] == wd && r_tr[k] == tr &&
        r_or[k] == k && (tr || r_in[k] == (k > 0 && r_tr[k - 1]));
endfunction
function automatic logic mem(input integer k, input logic [31:0] a, input logic [3:0] rm, input logic [3:0] wm,
                             input logic [31:0] rd, input logic [31:0] wd);
  mem = r_ma[k] == a && r_rm[k] == rm && r_wm[k] == wm && r_mr[k] == rd && r_mw[k] == wd;
endfunction
function automatic logic nomem(input integer k);
  nomem = r_ma[k] == 0 && r_rm[k] == 0 && r_wm[k] == 0 && r_mr[k] == 0 && r_mw[k] == 0;
endfunction
function automatic logic rs(input integer k, input integer a1, input logic [31:0] d1, input integer a2, input logic [31:0] d2);
  rs = r_a1[k] == a1 && r_r1[k] == d1 && r_a2[k] == a2 && r_r2[k] == d2;
endfunction

initial begin
  integer k;
  for (int j = 0; j < 256; j++) im[j] = 32'h0000_0013;
  for (int j = 0; j < 64; j++) dm[j] = 32'h0;
  im[0]  = 32'h1234_50B7;                 // 00 lui   x1, 0x12345
  im[1]  = I(12'h678, 1, 0, 1, 7'h13);    // 04 addi  x1, x1, 0x678
  im[2]  = I(-1, 0, 0, 2, 7'h13);         // 08 addi  x2, x0, -1
  im[3]  = S(12'h040, 1, 0, 2);           // 0C sw    x1, 0x40(x0)
  im[4]  = I(12'h040, 0, 2, 3, 7'h03);    // 10 lw    x3, 0x40(x0)
  im[5]  = I(12'h041, 0, 0, 4, 7'h03);    // 14 lb    x4, 0x41(x0)
  im[6]  = I(12'h043, 0, 4, 5, 7'h03);    // 18 lbu   x5, 0x43(x0)
  im[7]  = I(12'h042, 0, 1, 6, 7'h03);    // 1C lh    x6, 0x42(x0)
  im[8]  = S(12'h045, 2, 0, 0);           // 20 sb    x2, 0x45(x0)
  im[9]  = I(12'h045, 0, 0, 7, 7'h03);    // 24 lb    x7, 0x45(x0)
  im[10] = I(12'h045, 0, 4, 7, 7'h03);    // 28 lbu   x7, 0x45(x0)
  im[11] = I(12'h044, 0, 1, 8, 7'h03);    // 2C lh    x8, 0x44(x0)
  im[12] = S(12'h046, 1, 0, 1);           // 30 sh    x1, 0x46(x0)
  im[13] = I(12'h044, 0, 2, 9, 7'h03);    // 34 lw    x9, 0x44(x0)
  im[14] = R(7'h20, 1, 3, 0, 10);         // 38 sub   x10, x3, x1
  im[15] = B(8, 0, 10, 0);                // 3C beq   x10, x0, +8
  im[16] = I(1, 0, 0, 11, 7'h13);         // 40 addi  x11, x0, 1 (skipped)
  im[17] = B(8, 0, 10, 1);                // 44 bne   x10, x0, +8 (not taken)
  im[18] = R(7'h00, 0, 2, 2, 12);         // 48 slt   x12, x2, x0
  im[19] = R(7'h00, 0, 2, 3, 13);         // 4C sltu  x13, x2, x0
  im[20] = I(12'h404, 2, 5, 14, 7'h13);   // 50 srai  x14, x2, 4
  im[21] = I(12'h004, 1, 5, 15, 7'h13);   // 54 srli  x15, x1, 4
  im[22] = I(12'h004, 1, 1, 16, 7'h13);   // 58 slli  x16, x1, 4
  im[23] = I(-1, 1, 4, 17, 7'h13);        // 5C xori  x17, x1, -1
  im[24] = 32'h0000_1917;                 // 60 auipc x18, 1
  im[25] = J(12, 19);                     // 64 jal   x19, +12
  im[28] = I(12'h080, 0, 0, 20, 7'h67);   // 70 jalr  x20, 0x80(x0)
  im[32] = B(8, 0, 2, 4);                 // 80 blt   x2, x0, +8
  im[34] = B(8, 1, 2, 7);                 // 88 bgeu  x2, x1, +8
  im[36] = R(7'h00, 1, 1, 0, 0);          // 90 add   x0, x1, x1
  im[37] = R(7'h00, 17, 1, 6, 22);        // 94 or    x22, x1, x17
  im[38] = I(12'h0B0, 0, 0, 26, 7'h13);   // 98 addi  x26, x0, 0xB0
  im[39] = I(12'h042, 0, 2, 24, 7'h03);   // 9C lw    x24, 0x42(x0): misaligned
  im[64] = I(1, 25, 0, 25, 7'h13);        // 100 addi x25, x25, 1 (trap handler)
  im[65] = I(0, 26, 0, 0, 7'h67);         // 104 jalr x0, 0(x26)
  im[44] = I(12'h0C0, 0, 0, 26, 7'h13);   // B0 addi  x26, x0, 0xC0
  im[45] = 32'h0000_0073;                 // B4 ecall
  im[48] = I(12'h0D0, 0, 0, 26, 7'h13);   // C0 addi  x26, x0, 0xD0
  im[49] = 32'hFFFF_FFFF;                 // C4 illegal
  im[52] = I(12'h0E0, 0, 0, 26, 7'h13);   // D0 addi  x26, x0, 0xE0
  im[53] = J(6, 1);                       // D4 jal   x1, +6: misaligned target
  im[56] = I(12'h0F0, 0, 0, 26, 7'h13);   // E0 addi  x26, x0, 0xF0
  im[57] = S(12'h041, 1, 0, 2);           // E4 sw    x1, 0x41(x0): misaligned
  im[60] = I(12'h180, 0, 0, 26, 7'h13);   // F0 addi  x26, x0, 0x180
  im[61] = 32'h0010_0073;                 // F4 ebreak
  im[96] = I(12'h040, 0, 2, 27, 7'h03);   // 180 lw   x27, 0x40(x0)
  im[97] = R(7'h00, 0, 1, 0, 28);         // 184 add  x28, x1, x0
  im[98] = I(12'h194, 0, 0, 26, 7'h13);   // 188 addi x26, x0, 0x194
  im[99] = I(12'h024, 1, 1, 29, 7'h13);   // 18C slli with shamt bit 5: illegal
  im[101] = 32'h0FF0_000F;                // 194 fence
  im[102] = B(8, 2, 0, 5);                // 198 bge  x0, x2, +8
  im[104] = R(7'h20, 1, 2, 5, 30);        // 1A0 sra  x30, x2, x1 (shamt 24)
  im[105] = I(12'h1B0, 0, 0, 26, 7'h13);  // 1A4 addi x26, x0, 0x1B0
  im[106] = B(6, 0, 0, 0);                // 1A8 beq  x0, x0, +6: misaligned target
  im[108] = R(7'h00, 22, 1, 7, 31);       // 1B0 and  x31, x1, x22
  im[109] = I(12'h1C0, 0, 0, 26, 7'h13);  // 1B4 addi x26, x0, 0x1C0
  im[110] = I(12'h082, 0, 0, 1, 7'h67);   // 1B8 jalr x1, 0x82(x0): misaligned target
  im[112] = I(12'h1D0, 0, 0, 26, 7'h13);  // 1C0 addi x26, x0, 0x1D0
  im[113] = I(12'h080, 0, 1, 1, 7'h67);   // 1C4 jalr with funct3 1: illegal
  im[116] = I(12'h1E0, 0, 0, 26, 7'h13);  // 1D0 addi x26, x0, 0x1E0
  im[117] = B(8, 0, 0, 2);                // 1D4 branch funct3 2: illegal
  im[120] = I(12'h1F0, 0, 0, 26, 7'h13);  // 1E0 addi x26, x0, 0x1F0
  im[121] = I(12'h040, 0, 3, 1, 7'h03);   // 1E4 load funct3 3: illegal
  im[124] = I(12'h040, 0, 0, 5, 7'h13);   // 1F0 addi x5, x0, 0x40
  im[125] = I(12'h004, 5, 2, 6, 7'h03);   // 1F4 lw   x6, 4(x5)
  im[126] = I(12'h201, 0, 0, 7, 7'h67);   // 1F8 jalr x7, 0x201(x0): bit 0 cleared
  im[128] = J(0, 0);                      // 200 jal  x0, 0 (stay)
  repeat (3) @(posedge clk);
  chk(i_req === 1'b0 && rvfi_valid === 1'b0 && d_req === 1'b0 && d_we === 1'b0, "no fetch, data request or retirement in reset");
  rst_n = 1;
  k = 0;
  while (k < 4000 && nr < 60) begin @(posedge clk); k = k + 1; end
  chk(nr >= 56, $sformatf("program retired (%0d records)", nr));
  chk(rec(0, 32'h00, 32'h04, 1, 32'h1234_5000, 0) && nomem(0) && rs(0, 0, 0, 0, 0) && !r_in[0], "lui");
  chk(rec(1, 32'h04, 32'h08, 1, 32'h1234_5678, 0) && rs(1, 1, 32'h1234_5000, 0, 0), "addi reads x1");
  chk(rec(2, 32'h08, 32'h0C, 2, 32'hFFFF_FFFF, 0), "addi -1");
  chk(rec(3, 32'h0C, 32'h10, 0, 0, 0) && mem(3, 32'h40, 4'h0, 4'hF, 0, 32'h1234_5678) && rs(3, 0, 0, 1, 32'h1234_5678), "sw");
  chk(rec(4, 32'h10, 32'h14, 3, 32'h1234_5678, 0) && mem(4, 32'h40, 4'hF, 4'h0, 32'h1234_5678, 0), "lw");
  chk(rec(5, 32'h14, 32'h18, 4, 32'h56, 0) && mem(5, 32'h40, 4'h2, 4'h0, 32'h1234_5678, 0), "lb lane 1");
  chk(rec(6, 32'h18, 32'h1C, 5, 32'h12, 0) && mem(6, 32'h40, 4'h8, 4'h0, 32'h1234_5678, 0), "lbu lane 3");
  chk(rec(7, 32'h1C, 32'h20, 6, 32'h1234, 0) && mem(7, 32'h40, 4'hC, 4'h0, 32'h1234_5678, 0), "lh upper half");
  chk(rec(8, 32'h20, 32'h24, 0, 0, 0) && mem(8, 32'h44, 4'h0, 4'h2, 0, 32'h0000_FF00), "sb lane 1");
  chk(rec(9, 32'h24, 32'h28, 7, 32'hFFFF_FFFF, 0), "lb sign-extends");
  chk(rec(10, 32'h28, 32'h2C, 7, 32'h0000_00FF, 0), "lbu zero-extends");
  chk(rec(11, 32'h2C, 32'h30, 8, 32'hFFFF_FF00, 0), "lh sign-extends");
  chk(rec(12, 32'h30, 32'h34, 0, 0, 0) && mem(12, 32'h44, 4'h0, 4'hC, 0, 32'h5678_0000), "sh upper half");
  chk(rec(13, 32'h34, 32'h38, 9, 32'h5678_FF00, 0), "lw after sb / sh");
  chk(rec(14, 32'h38, 32'h3C, 10, 32'h0, 0) && rs(14, 3, 32'h1234_5678, 1, 32'h1234_5678), "sub");
  chk(rec(15, 32'h3C, 32'h44, 0, 0, 0) && rs(15, 10, 0, 0, 0), "beq taken");
  chk(rec(16, 32'h44, 32'h48, 0, 0, 0), "bne not taken");
  chk(rec(17, 32'h48, 32'h4C, 12, 32'h1, 0), "slt -1 < 0");
  chk(rec(18, 32'h4C, 32'h50, 13, 32'h0, 0), "sltu 0xFFFFFFFF < 0 false");
  chk(rec(19, 32'h50, 32'h54, 14, 32'hFFFF_FFFF, 0), "srai");
  chk(rec(20, 32'h54, 32'h58, 15, 32'h0123_4567, 0), "srli");
  chk(rec(21, 32'h58, 32'h5C, 16, 32'h2345_6780, 0), "slli");
  chk(rec(22, 32'h5C, 32'h60, 17, 32'hEDCB_A987, 0), "xori -1");
  chk(rec(23, 32'h60, 32'h64, 18, 32'h0000_1060, 0), "auipc");
  chk(rec(24, 32'h64, 32'h70, 19, 32'h68, 0), "jal");
  chk(rec(25, 32'h70, 32'h80, 20, 32'h74, 0) && rs(25, 0, 0, 0, 0), "jalr");
  chk(rec(26, 32'h80, 32'h88, 0, 0, 0), "blt taken");
  chk(rec(27, 32'h88, 32'h90, 0, 0, 0), "bgeu taken");
  chk(rec(28, 32'h90, 32'h94, 0, 0, 0) && rs(28, 1, 32'h1234_5678, 1, 32'h1234_5678), "add to x0: no rd");
  chk(rec(29, 32'h94, 32'h98, 22, 32'hFFFF_FFFF, 0), "or");
  chk(rec(31, 32'h9C, 32'h100, 0, 0, 1) && nomem(31) && rs(31, 0, 0, 0, 0), "misaligned lw traps");
  chk(rec(32, 32'h100, 32'h104, 25, 32'h1, 0) && r_in[32], "handler: intr on its first instruction");
  chk(rec(33, 32'h104, 32'hB0, 0, 0, 0) && !r_in[33], "handler returns");
  chk(rec(35, 32'hB4, 32'h100, 0, 0, 1), "ecall traps");
  chk(rec(39, 32'hC4, 32'h100, 0, 0, 1), "illegal instruction traps");
  chk(rec(43, 32'hD4, 32'h100, 0, 0, 1), "jal to a misaligned target traps, no link");
  chk(rec(47, 32'hE4, 32'h100, 0, 0, 1) && nomem(47), "misaligned sw traps, no write");
  chk(rec(51, 32'hF4, 32'h100, 0, 0, 1), "ebreak traps");
  chk(rec(52, 32'h100, 32'h104, 25, 32'h6, 0), "handler counted six traps");
  chk(rec(54, 32'h180, 32'h184, 27, 32'h1234_5678, 0), "memory unchanged by the trapped store");
  chk(rec(55, 32'h184, 32'h188, 28, 32'h1234_5678, 0), "x1 unchanged by the trapped jal");
  chk(rec(57, 32'h18C, 32'h100, 0, 0, 1), "slli with shamt bit 5 traps");
  k = 0;
  while (k < 6000 && nr < 89) begin @(posedge clk); k = k + 1; end
  chk(rec(60, 32'h194, 32'h198, 0, 0, 0) && nomem(60) && rs(60, 0, 0, 0, 0), "fence: no-op");
  chk(rec(61, 32'h198, 32'h1A0, 0, 0, 0), "bge 0 >= -1 taken");
  chk(rec(62, 32'h1A0, 32'h1A4, 30, 32'hFFFF_FFFF, 0) && rs(62, 2, 32'hFFFF_FFFF, 1, 32'h1234_5678), "sra by x1[4:0]");
  chk(rec(64, 32'h1A8, 32'h100, 0, 0, 1), "taken branch to a misaligned target traps");
  chk(rec(67, 32'h1B0, 32'h1B4, 31, 32'h1234_5678, 0), "and");
  chk(rec(69, 32'h1B8, 32'h100, 0, 0, 1), "jalr to a misaligned target traps, no link");
  chk(rec(73, 32'h1C4, 32'h100, 0, 0, 1), "jalr with funct3 1 traps");
  chk(rec(77, 32'h1D4, 32'h100, 0, 0, 1), "branch with funct3 2 traps");
  chk(rec(81, 32'h1E4, 32'h100, 0, 0, 1), "load with funct3 3 traps");
  chk(rec(85, 32'h1F4, 32'h1F8, 6, 32'h5678_FF00, 0) && rs(85, 5, 32'h40, 0, 0) && mem(85, 32'h44, 4'hF, 4'h0, 32'h5678_FF00, 0),
      "lw off a base register reports rs1");
  chk(rec(86, 32'h1F8, 32'h200, 7, 32'h1FC, 0), "jalr clears bit 0 of the target");
  chk(rec(87, 32'h200, 32'h200, 0, 0, 0) && rec(88, 32'h200, 32'h200, 0, 0, 0), "jal x0, 0 loops");
  k = 1;
  for (int j = 0; j < 89; j++) if (!r_ok[j]) k = 0;
  chk(k == 1, "halt 0, mode M, ixl 32 on every record");
  chk(both == 0, "never a fetch and a data request together");
  chk(dm[16] == 32'h1234_5678 && dm[17] == 32'h5678_FF00, "data memory after the stores");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
