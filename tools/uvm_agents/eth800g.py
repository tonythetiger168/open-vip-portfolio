# 800G Ethernet segment stream (tb/top_tb.sv eth800g_model: always ready,
# 32 bytes per beat, pkt_mty unused bytes on the EOP beat, pkt_cnt / byte_cnt
# accumulated per packet, err_oversize pulse for packets above 9600 bytes).
from _lib import wait_cb

SPEC = dict(
    vip="ETH800G-VIP", p="eth800g", P="800G Ethernet", dir="eth800g",
    fields=[
        ("bit [9:0]", "nbeats", "req"),
        ("bit [4:0]", "mty", "req"),
        ("bit [31:0]", "data_hash", "req", "norand"),   # FNV-1a over every 32-bit word of the packet
        ("bit [15:0]", "pkt_cnt", "rsp"),
        ("bit [31:0]", "byte_cnt", "rsp"),
        ("bit", "oversize", "rsp"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nbeats dist { [1:4] :/ 4, [5:64] :/ 3, [290:302] :/ 1 }; }
""",
    tr_functions="""
function int unsigned bytes_len(); return nbeats * 32 - mty; endfunction

// beat i of the packet (derived from seed)
function bit [255:0] beat(int unsigned i);
  bit [31:0] x = seed ^ (i * 32'h9E37_79B9) | 32'h1;
  for (int k = 0; k < 8; k++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    beat[k*32 +: 32] = x;
  end
endfunction

static function bit [31:0] hash_beat(bit [31:0] h, bit [255:0] b);
  for (int k = 0; k < 8; k++) begin
    h ^= b[k*32 +: 32];
    h *= 32'h0100_0193;
  end
  return h;
endfunction

function void fill();
  data_hash = 32'h811C_9DC5;
  for (int unsigned i = 0; i < nbeats; i++) data_hash = hash_beat(data_hash, beat(i));
endfunction

function void post_randomize(); fill(); endfunction
""",
    drv_rsp=False,
    drv_desc="one packet per item, pkt_sop/pkt_eop framing and pkt_mty on the last beat",
    drv_idle="""
vif.drv_cb.pkt_valid <= 1'b0; vif.drv_cb.pkt_sop <= 1'b0; vif.drv_cb.pkt_eop <= 1'b0;
vif.drv_cb.pkt_data <= '0; vif.drv_cb.pkt_mty <= '0;
""",
    drv_item="""
@(vif.drv_cb);
for (int unsigned i = 0; i < t.nbeats; i++) begin
  vif.drv_cb.pkt_valid <= 1'b1;
  vif.drv_cb.pkt_sop   <= (i == 0);
  vif.drv_cb.pkt_eop   <= (i == t.nbeats - 1);
  vif.drv_cb.pkt_mty   <= (i == t.nbeats - 1) ? t.mty : 5'd0;
  vif.drv_cb.pkt_data  <= t.beat(i);
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.pkt_ready === 1'b1", "800G pkt_ready").splitlines()) + """
end
vif.drv_cb.pkt_valid <= 1'b0;
vif.drv_cb.pkt_sop   <= 1'b0;
vif.drv_cb.pkt_eop   <= 1'b0;
@(vif.drv_cb);
""",
    mon_desc="packets from SOP to EOP; counters sampled the clock after EOP",
    mon_run="""
eth800g_transaction t, done;
forever begin
  @(vif.mon_cb);
  if (done != null) begin
    done.pkt_cnt  = vif.mon_cb.pkt_cnt;
    done.byte_cnt = vif.mon_cb.byte_cnt;
    done.oversize = vif.mon_cb.err_oversize;
    publish(done);
    done = null;
  end
  if (vif.mon_cb.pkt_valid && vif.mon_cb.pkt_ready) begin
    if (vif.mon_cb.pkt_sop) begin
      if (t != null) `uvm_error("MON", "800G SOP inside a packet")
      t = eth800g_transaction::type_id::create("t");
      t.data_hash = 32'h811C_9DC5;
    end
    if (t == null) `uvm_error("MON", "800G beat outside a packet")
    else begin
      t.nbeats++;
      t.data_hash = eth800g_transaction::hash_beat(t.data_hash, vif.mon_cb.pkt_data);
      if (vif.mon_cb.pkt_eop) begin
        t.mty = vif.mon_cb.pkt_mty;
        done = t;
        t = null;
      end
    end
  end
end
""",
    sb_members="bit [15:0] pkts = 0;\nbit [31:0] total = 0;",
    predict="""
pkts++;
total += t.bytes_len();
t.pkt_cnt  = pkts;
t.byte_cnt = total;
t.oversize = (t.bytes_len() > 9600);
""",
    checks="""
if (t.nbeats == 0) fail(t, "empty packet");
""",
    coverage="""
cp_len  : coverpoint tr.bytes_len() { bins tiny = {[1:63]}; bins normal = {[64:1518]}; bins jumbo = {[1519:9600]}; bins over = {[9601:$]}; }
cp_over : coverpoint tr.oversize;
cp_mty  : coverpoint tr.mty { bins full = {0}; bins partial = {[1:30]}; bins one_byte = {31}; }
""",
    directed="""
t = item(); t.nbeats = 2;   t.mty = 0;  t.seed = 1; t.fill(); send(t);   // 64 B
t = item(); t.nbeats = 1;   t.mty = 31; t.seed = 2; t.fill(); send(t);   // 1 B
t = item(); t.nbeats = 48;  t.mty = 2;  t.seed = 3; t.fill(); send(t);   // 1534 B
t = item(); t.nbeats = 300; t.mty = 0;  t.seed = 4; t.fill(); send(t);   // 9600 B: largest legal
t = item(); t.nbeats = 301; t.mty = 31; t.seed = 5; t.fill(); send(t);   // 9601 B: oversize
t = item(); t.nbeats = 302; t.mty = 0;  t.seed = 6; t.fill(); send(t);
""",
)
# SVA: pkt_ready is tied high
SPEC["patches"] = {"eth800g/sva/eth800g_compliance_checker.sv": [(
    "disable iff (1'b0) !rst_n |-> pkt_ready == '0)",
    "disable iff (1'b0) !rst_n |-> pkt_ready == 1'b1)   // always ready")]}
