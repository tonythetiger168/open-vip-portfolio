# SD/SDIO host command agent (tb/top_tb.sv sdio_model, negedge-clocked card:
# a 48-bit command on cmd_i is answered on cmd_o/cmd_oe with a fixed R1-style
# response, and dat_oe/dat_o busy for the first 8 clocks of it).
#
# Response: 48 bits, start 0, transmission 0, the command index, card status
# 0x00000100, CRC7, end 1. (Until 2026-10-27 the model sent {transmission
# bit, index[5:1]} as the index, a zero CRC7 and no end bit; fixed in the
# model and here together.)
SPEC = dict(
    vip="SDIO-UVM-VIP", p="sdio", P="SDIO", dir="sdio",
    cfg="int unsigned resp_timeout = 64;   // NCR: clocks to wait for the response start",
    fields=[
        ("bit [5:0]", "cmd", "req"),
        ("bit [31:0]", "arg", "req"),
        ("bit [6:0]", "crc", "req", "norand"),   # CRC7 of the command (computed by build())
        ("bit [47:0]", "resp", "rsp"),           # bits driven while cmd_oe, MSB first
        ("bit [5:0]", "resp_len", "rsp"),
        ("bit [3:0]", "busy_clks", "rsp"),       # clocks dat_oe was high during the response
    ],
    tr_functions="""
// CRC7 (x^7 + x^3 + 1) over the first 40 bits of the command
static function bit [6:0] crc7(bit [39:0] d);
  bit [6:0] c = 0;
  for (int i = 39; i >= 0; i--) begin
    bit fb = c[6] ^ d[i];
    c = {c[5:0], 1'b0};
    if (fb) c ^= 7'h09;
  end
  return c;
endfunction

// start 0, transmission 1, index, argument, CRC7, end 1
function bit [47:0] frame();
  return {1'b0, 1'b1, cmd, arg, crc, 1'b1};
endfunction

function void build(); crc = crc7({1'b0, 1'b1, cmd, arg}); endfunction
function void post_randomize(); build(); endfunction
""",
    drv_desc="48-bit command on cmd_i (one bit per clock), then collects the response",
    drv_idle="vif.drv_cb.cmd_i <= 1'b1; vif.drv_cb.dat_i <= 4'hF;",
    drv_item="""
bit [47:0] f = t.frame();
@(vif.drv_cb);
for (int i = 47; i >= 0; i--) begin
  vif.drv_cb.cmd_i <= f[i];
  @(vif.drv_cb);
end
vif.drv_cb.cmd_i <= 1'b1;
""" + """begin
  int unsigned to = 0;
  while (vif.drv_cb.cmd_oe !== 1'b1 && to < cfg.resp_timeout) begin @(vif.drv_cb); to++; end
  if (vif.drv_cb.cmd_oe !== 1'b1) `uvm_error("TIMEOUT", "SDIO: no response")
end
t.resp = 0; t.resp_len = 0; t.busy_clks = 0;
while (vif.drv_cb.cmd_oe === 1'b1) begin
  t.resp = {t.resp[46:0], vif.drv_cb.cmd_o};
  t.resp_len++;
  if (vif.drv_cb.dat_oe === 1'b1) t.busy_clks++;
  @(vif.drv_cb);
end
repeat (2) @(vif.drv_cb);
""",
    mon_desc="commands on cmd_i (start bit to end bit) and the card's response on cmd_o",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.cmd_i === 1'b0) begin           // start bit
    sdio_transaction t = sdio_transaction::type_id::create("t");
    bit [47:0] f = 0;
    int unsigned to = 0;
    for (int i = 0; i < 48; i++) begin
      if (i != 0) @(vif.mon_cb);
      f = {f[46:0], vif.mon_cb.cmd_i};
    end
    t.cmd = f[45:40]; t.arg = f[39:8]; t.crc = f[7:1];
    if (f[46] != 1'b1 || f[0] != 1'b1) `uvm_error("MON", "SDIO command without transmission / end bit")
    do begin @(vif.mon_cb); to++; end while (vif.mon_cb.cmd_oe !== 1'b1 && to < cfg.resp_timeout);
    while (vif.mon_cb.cmd_oe === 1'b1) begin
      t.resp = {t.resp[46:0], vif.mon_cb.cmd_o};
      t.resp_len++;
      if (vif.mon_cb.dat_oe === 1'b1) begin
        t.busy_clks++;
        if (vif.mon_cb.dat_o !== 4'h5) `uvm_error("MON", "SDIO unexpected DAT pattern during busy")
      end
      @(vif.mon_cb);
    end
    publish(t);
  end
end
""",
    predict="""
// R1-style response: start 0, transmission 0, index, status 0x00000100,
// CRC7, end 1 (48 bits), busy on DAT for 8 clocks
t.resp = {2'b00, t.cmd, 32'h0000_0100,
          sdio_transaction::crc7({2'b00, t.cmd, 32'h0000_0100}), 1'b1};
t.resp_len = 48;
t.busy_clks = 8;
""",
    checks="""
if (t.crc != sdio_transaction::crc7({1'b0, 1'b1, t.cmd, t.arg})) fail(t, "command CRC7 mismatch");
if (t.resp[47:46] != 2'b00) fail(t, "response start/transmission bits not 0");
if (t.resp[0] != 1'b1) fail(t, "response end bit not 1");
if (t.resp[7:1] != sdio_transaction::crc7(t.resp[47:8])) fail(t, "response CRC7 mismatch");
""",
    coverage="""
cp_cmd : coverpoint tr.cmd { bins go_idle = {0}; bins send_if_cond = {8}; bins io_rw_direct = {52};
                             bins io_rw_extended = {53}; bins app = {55}; bins other = default; }
""",
    directed="""
bit [5:0] cmds [6] = '{6'd0, 6'd8, 6'd5, 6'd3, 6'd52, 6'd53};   // CMD0/8/5/3/52/53
bit [31:0] args [6] = '{32'h0, 32'h0000_01AA, 32'h0030_0000, 32'h0, 32'h8000_0C00, 32'h1000_0004};
foreach (cmds[i]) begin t = item(); t.cmd = cmds[i]; t.arg = args[i]; t.build(); send(t); end
""",
)
